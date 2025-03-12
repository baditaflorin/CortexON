import json
import os
import time
import logfire
import asyncio
import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from functools import wraps
from utils.ant_client import get_client
from utils.markdown_browser import RequestsMarkdownBrowser
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import (
    SystemPromptPart,
    UserPromptPart,
    ModelRequest,
    ModelResponse,
    ModelMessage,
)
from pydantic_ai.models.anthropic import AnthropicModel
from fastapi import WebSocket
from dataclasses import asdict
from utils.stream_response_format import StreamResponse

from dotenv import load_dotenv

load_dotenv()

# Custom exceptions
class FileSurferError(Exception):
    """Base exception class for FileSurfer"""
    pass

class BrowserNotInitializedError(FileSurferError):
    """Raised when browser is not initialized"""
    pass

class FileNotFoundError(FileSurferError):
    """Raised when file is not found"""
    pass

class NavigationError(FileSurferError):
    """Raised when navigation fails"""
    pass

class PathValidationError(FileSurferError):
    """Raised when path validation fails"""
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def error_handler(func):
    """Decorator for handling errors in async functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except FileSurferError as e:
            logger.error(f"FileSurfer error in {func.__name__}: {str(e)}")
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True
            )
            raise FileSurferError(f"An unexpected error occurred: {str(e)}")
    return wrapper

@dataclass
class FileToolDependencies:
    browser: RequestsMarkdownBrowser
    websocket: Optional[WebSocket]
    stream_output: Optional[StreamResponse]
    sandbox_directory: str

class FileSurfer:
    """An agent that uses tools to read and navigate local files with robust error handling."""

    def __init__(
        self,
        agent: Agent,
        name: str = "File Surfer Agent",
        browser: Optional[RequestsMarkdownBrowser] = None,
        system_prompt: str = "You are a helpful AI Assistant that can navigate and read files in the code_files directory. You should help the user understand code, find specific files, and analyze code structure. You cannot access files outside the code_files directory for security reasons.",
        viewport_size: int = 1024 * 5,
        sandbox_directory: str = "code_files",
    ) -> None:
        """
        Initialize FileSurfer with error handling.

        Args:
            agent: The AI agent to use
            browser: Optional browser instance
            system_prompt: System prompt for the agent
            viewport_size: Size of the viewport
            sandbox_directory: Restricted directory for file operations

        Raises:
            FileSurferError: If initialization fails
        """
        try:
            self._agent: Agent = agent
            self._name: str = name
            self.description = "An agent that uses tools to read and navigate local files with robust error handling."
            self._browser: RequestsMarkdownBrowser = browser or RequestsMarkdownBrowser(
                viewport_size=viewport_size, downloads_folder=sandbox_directory
            )
            self._chat_history: List[ModelMessage] = []
            self._system_prompt = system_prompt
            self._viewport_size = viewport_size
            self._sandbox_directory = os.path.abspath(sandbox_directory)
            self.websocket: Optional[WebSocket] = None
            self.stream_output: Optional[StreamResponse] = None
            
            # Ensure sandbox directory exists
            os.makedirs(self._sandbox_directory, exist_ok=True)
            
            self._register_tools()
            logger.info(f"FileSurfer initialized successfully with sandbox: {self._sandbox_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize FileSurfer: {str(e)}", exc_info=True)
            raise FileSurferError(f"Failed to initialize FileSurfer: {str(e)}")

    def _validate_path(self, path: str) -> str:
        """
        Validate that path is within the sandbox directory.
        
        Args:
            path: Path to validate
            
        Returns:
            Absolute path if valid
            
        Raises:
            PathValidationError: If path is outside sandbox
        """
        # Normalize the path
        abs_path = os.path.abspath(path)
        
        # Check if the path is within the sandbox
        if not abs_path.startswith(self._sandbox_directory):
            error_msg = f"Access denied: {path} is outside the sandbox directory"
            logger.error(error_msg)
            raise PathValidationError(error_msg)
        
        return abs_path

    @property
    def name(self) -> str:
        """Get the agent's name"""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        """Set the agent's name"""
        self._name = value

    def _register_tools(self) -> None:
        """Register tools with error handling"""
        try:
            self._register_file_tools()
            self._register_navigation_tools()
            self._register_search_tools()
            self._register_directory_tools()
            logger.info("Tools registered successfully")
        except Exception as e:
            logger.error(f"Failed to register tools: {str(e)}", exc_info=True)
            raise FileSurferError(f"Failed to register tools: {str(e)}")

    def _register_file_tools(self) -> None:
        """Register file-related tools"""
        @self._agent.tool
        @error_handler
        async def open_file(
            ctx: RunContext[FileToolDependencies], path: str
        ) -> str:
            """Open a file within the sandbox directory"""
            try:
                # Prepend sandbox directory if not already included
                if not path.startswith(ctx.deps.sandbox_directory):
                    full_path = os.path.join(ctx.deps.sandbox_directory, path)
                else:
                    full_path = path
                
                # Validate path is within sandbox
                full_path = self._validate_path(full_path)
                
                ctx.deps.browser.open_local_file(full_path)
                header, content = self._get_browser_state()
                
                if ctx.deps.stream_output and ctx.deps.websocket:
                    ctx.deps.stream_output.steps.append(
                        f"Opening file: {path} ..."
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                    ctx.deps.stream_output.steps.append(
                        f"{header.strip()}"
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                return f"{header.strip()}\n=======================\n{content}"
            except PathValidationError as e:
                raise e
            except Exception as e:
                logger.error(f"Failed to open file {path}: {str(e)}", exc_info=True)
                raise FileNotFoundError(f"Failed to open file {path}: {str(e)}")

    def _register_directory_tools(self) -> None:
        """Register directory-related tools"""
        @self._agent.tool
        @error_handler
        async def list_directory(
            ctx: RunContext[FileToolDependencies], subdir: str = ""
        ) -> str:
            """
            List contents of a directory within the sandbox
            
            Args:
                subdir: Subdirectory within sandbox to list (empty for root)
            """
            try:
                # Build path and validate
                dir_path = os.path.join(ctx.deps.sandbox_directory, subdir) if subdir else ctx.deps.sandbox_directory
                dir_path = self._validate_path(dir_path)
                
                if not os.path.isdir(dir_path):
                    return f"Error: {subdir} is not a directory"
                
                # Get directory contents
                entries = os.listdir(dir_path)
                
                # Format as markdown
                result = f"# Directory listing for: /{subdir if subdir else ''}\n\n"
                
                if entries:
                    result += "| Name | Type | Size |\n"
                    result += "|------|------|------|\n"
                    
                    for entry in sorted(entries):
                        entry_path = os.path.join(dir_path, entry)
                        if os.path.isdir(entry_path):
                            entry_type = "Directory"
                            size = "-"
                        else:
                            entry_type = "File"
                            size = f"{os.path.getsize(entry_path):,} bytes"
                        
                        result += f"| {entry} | {entry_type} | {size} |\n"
                else:
                    result += "Directory is empty."
                
                if ctx.deps.stream_output and ctx.deps.websocket:
                    ctx.deps.stream_output.steps.append(
                        f"Listing directory: {subdir or 'sandbox root'} ..."
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                
                return result
                
            except PathValidationError as e:
                return f"Error: {str(e)}"
            except Exception as e:
                logger.error(f"Error listing directory {subdir}: {str(e)}", exc_info=True)
                return f"Error listing directory: {str(e)}"

        @self._agent.tool
        @error_handler
        async def get_file_content(
            ctx: RunContext[FileToolDependencies], path: str
        ) -> str:
            """
            Get the raw content of a file within the sandbox
            
            Args:
                path: Path to the file relative to sandbox
            """
            try:
                # Prepend sandbox directory if not already included
                if not path.startswith(ctx.deps.sandbox_directory):
                    full_path = os.path.join(ctx.deps.sandbox_directory, path)
                else:
                    full_path = path
                
                # Validate path is within sandbox
                full_path = self._validate_path(full_path)
                
                if not os.path.isfile(full_path):
                    return f"Error: {path} is not a file or doesn't exist"
                
                # Read and return file content
                with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Get file extension
                _, ext = os.path.splitext(full_path)
                ext = ext.lstrip('.').lower()
                
                if ctx.deps.stream_output and ctx.deps.websocket:
                    ctx.deps.stream_output.steps.append(
                        f"Reading file content: {path} ..."
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                
                return f"```{ext}\n{content}\n```"
                
            except PathValidationError as e:
                return f"Error: {str(e)}"
            except Exception as e:
                logger.error(f"Error reading file {path}: {str(e)}", exc_info=True)
                return f"Error reading file: {str(e)}"

    def _register_navigation_tools(self) -> None:
        """Register navigation tools"""
        @self._agent.tool
        @error_handler
        async def page_up(ctx: RunContext[FileToolDependencies]) -> str:
            """Scroll viewport up with error handling"""
            try:
                ctx.deps.browser.page_up()
                header, content = self._get_browser_state()
                if ctx.deps.stream_output and ctx.deps.websocket:
                    ctx.deps.stream_output.steps.append(
                        f"Scrolling up..."
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                    ctx.deps.stream_output.steps.append(
                        f"{header.strip()}"
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                return f"{header.strip()}\n=======================\n{content}"
            except Exception as e:
                logger.error(
                    f"Navigation error during page_up: {str(e)}", exc_info=True
                )
                raise NavigationError(f"Failed to scroll up: {str(e)}")

        @self._agent.tool
        @error_handler
        async def page_down(ctx: RunContext[FileToolDependencies]) -> str:
            """Scroll viewport down with error handling"""
            try:
                ctx.deps.browser.page_down()
                header, content = self._get_browser_state()
                if ctx.deps.stream_output and ctx.deps.websocket:
                    ctx.deps.stream_output.steps.append(
                        f"Scrolling down..."
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                    ctx.deps.stream_output.steps.append(
                        f"{header.strip()}"
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                return f"{header.strip()}\n=======================\n{content}"
            except Exception as e:
                logger.error(
                    f"Navigation error during page_down: {str(e)}", exc_info=True
                )
                raise NavigationError(f"Failed to scroll down: {str(e)}")

    def _register_search_tools(self) -> None:
        """Register search-related tools"""
        @self._agent.tool
        @error_handler
        async def find_on_page_ctrl_f(
            ctx: RunContext[FileToolDependencies], search_string: str
        ) -> str:
            """Search on page with error handling"""
            try:
                ctx.deps.browser.find_on_page(search_string)
                header, content = self._get_browser_state()
                if ctx.deps.stream_output and ctx.deps.websocket:
                    ctx.deps.stream_output.steps.append(
                        f"Searching for '{search_string}'..."
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                    ctx.deps.stream_output.steps.append(
                        f"{header.strip()}"
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                return f"{header.strip()}\n=======================\n{content}"
            except Exception as e:
                logger.error(
                    f"Search error for string '{search_string}': {str(e)}",
                    exc_info=True,
                )
                raise NavigationError(
                    f"Failed to search for '{search_string}': {str(e)}"
                )

        @self._agent.tool
        @error_handler
        async def find_next(ctx: RunContext[FileToolDependencies]) -> str:
            """Find next occurrence with error handling"""
            try:
                ctx.deps.browser.find_next()
                header, content = self._get_browser_state()
                if ctx.deps.stream_output and ctx.deps.websocket:
                    ctx.deps.stream_output.steps.append(
                        f"Finding next occurence..."
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                    ctx.deps.stream_output.steps.append(
                        f"{header.strip()}"
                    )
                    await ctx.deps.websocket.send_text(
                        json.dumps(asdict(self.stream_output))
                    )
                return f"{header.strip()}\n=======================\n{content}"
            except Exception as e:
                logger.error(f"Error finding next occurrence: {str(e)}", exc_info=True)
                raise NavigationError(f"Failed to find next occurrence: {str(e)}")

    def _get_browser_state(self) -> Tuple[str, str]:
        """
        Get browser state with error handling

        Returns:
            Tuple[str, str]: Header and content

        Raises:
            BrowserNotInitializedError: If browser is not initialized
        """
        try:
            if self._browser is None:
                self._browser = RequestsMarkdownBrowser(
                    viewport_size=self._viewport_size,
                    downloads_folder=self._sandbox_directory,
                )

            header = self._generate_header()
            return (header, self._browser.viewport)
        except Exception as e:
            logger.error(f"Failed to get browser state: {str(e)}", exc_info=True)
            raise BrowserNotInitializedError(f"Failed to get browser state: {str(e)}")

    def _generate_header(self) -> str:
        """Generate browser header with error handling"""
        try:
            header = [f"Address: {self._browser.address}"]

            if self._browser.page_title:
                header.append(f"Title: {self._browser.page_title}")

            current_page = self._browser.viewport_current_page
            total_pages = len(self._browser.viewport_pages)
            header.append(
                f"Viewport position: Showing page {current_page+1} of {total_pages}."
            )

            # Add history information
            address = self._browser.address
            for i in range(len(self._browser.history) - 2, -1, -1):
                if self._browser.history[i][0] == address:
                    header.append(
                        f"You previously visited this page {round(time.time() - self._browser.history[i][1])} seconds ago."
                    )
                    break

            return "\n".join(header)
        except Exception as e:
            logger.error(f"Failed to generate header: {str(e)}", exc_info=True)
            raise BrowserNotInitializedError(f"Failed to generate header: {str(e)}")

    @error_handler
    async def generate_reply(
        self, user_message: str, websocket: WebSocket, stream_output: StreamResponse
    ) -> Tuple[bool, str, List[ModelMessage]]:
        """
        Generate reply to user message with error handling

        Args:
            user_message: User's input message
            websocket: WebSocket connection for streaming
            stream_output: Response format for streaming

        Returns:
            Tuple[bool, str, List[ModelMessage]]: Success status, response text, and all messages

        Raises:
            FileSurferError: If reply generation fails
        """
        try:
            self.websocket = websocket
            self.stream_output = stream_output
        
            if self._browser is None:
                self._browser = RequestsMarkdownBrowser(
                    viewport_size=self._viewport_size,
                    downloads_folder=self._sandbox_directory,
                )

            context_message = UserPromptPart(
                content=f"Your browser is currently open to the page '{self._browser.page_title}' at the address '{self._browser.address}'. You are restricted to browsing files only within the {self._sandbox_directory} directory for security reasons.",
            )

            message_history = self._build_message_history(context_message)
            deps = FileToolDependencies(
                browser=self._browser, 
                websocket=self.websocket, 
                stream_output=self.stream_output,
                sandbox_directory=self._sandbox_directory
            )

            response = await self._agent.run(
                user_prompt=user_message, message_history=message_history, deps=deps
            )

            self._chat_history = response.all_messages()
            logger.info("Successfully generated reply")

            return (
                True,
                str(response.data),
                response.all_messages(),
            )

        except Exception as e:
            logger.error(f"Failed to generate reply: {str(e)}", exc_info=True)
            return False, str(e), []

    def _build_message_history(
        self, context_message: UserPromptPart
    ) -> List[ModelMessage]:
        """Build message history with error handling"""
        try:
            if not self._chat_history:
                system_message = SystemPromptPart(content=self._system_prompt)
                return [
                    ModelRequest(
                        parts=[system_message, context_message], kind="request"
                    )
                ]

            message_history = []
            for message in self._chat_history:
                if message.kind == "request":
                    message_history.append(
                        ModelRequest(parts=message.parts, kind=message.kind)
                    )
                else:
                    message_history.append(
                        ModelResponse(parts=message.parts, kind=message.kind)
                    )

            message_history.append(
                ModelRequest(parts=[context_message], kind="request")
            )
            return message_history

        except Exception as e:
            logger.error(f"Failed to build message history: {str(e)}", exc_info=True)
            raise FileSurferError(f"Failed to build message history: {str(e)}")

# Example usage
if __name__ == "__main__":
    try:
        # Configure logfire
        logfire.configure(
            send_to_logfire="if-token-present", token=os.getenv("LOGFIRE_TOKEN")
        )

        # Initialize OpenAI model
        model = AnthropicModel(
                model_name=os.environ.get("ANTHROPIC_MODEL_NAME"),
                anthropic_client=get_client()
        )

        # Initialize agent and file surfer
        agent = Agent(model, deps_type=FileToolDependencies)
        file_surfer = FileSurfer(
            agent=agent,
            browser=RequestsMarkdownBrowser(
                viewport_size=1024 * 5, downloads_folder="code_files"
            ),
            sandbox_directory="code_files"
        )

        # Main interaction loop
        while True:
            try:
                user_message = input("\nEnter your question (type 'exit' to quit): ")
                if user_message.lower() == "exit":
                    break

                result = asyncio.run(
                    file_surfer.generate_reply(user_message=user_message)
                )
                print("Response:", result)

            except KeyboardInterrupt:
                logger.info("Program terminated by user")
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                print(f"An error occurred: {str(e)}")

    except Exception as e:
        logger.critical(f"Critical error in main: {str(e)}", exc_info=True)
        raise