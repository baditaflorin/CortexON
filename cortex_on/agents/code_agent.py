from dataclasses import dataclass
import json
from dotenv import load_dotenv
import os
from pydantic import Field, BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel
from fastapi import WebSocket
from typing import List, Optional
from utils.ant_client import get_client
import subprocess
import shlex
import logfire
from dataclasses import asdict
from utils.stream_response_format import StreamResponse

load_dotenv()

@dataclass
class coder_agent_deps:
    websocket: Optional[WebSocket] = None
    stream_output: Optional[StreamResponse] = None

coder_system_message = """You are a helpful AI assistant with coding capabilities. Solve tasks using your coding and language skills.

<critical>
    - You have access to a single shell tool that executes terminal commands and handles file operations.
    - All commands will be executed in a restricted directory for security.
    - Do NOT write code that attempts to access directories outside your working directory.
    - Do NOT provide test run snippets that print unnecessary output.
    - Never use interactive input functions like 'input()' in Python or 'read' in Bash.
    - All code must be non-interactive and should execute completely without user interaction.
    - Use command line arguments, environment variables, or file I/O instead of interactive input.
</critical>

(restricted to your working directory which means you are already in the ./code_files directory)
When solving tasks, use your provided shell tool for all operations:

- execute_shell(command: str) - Execute terminal commands including:
  - File operations: Use 'cat' to read files, 'echo' with redirection (>) to write files
  - Directory operations: 'ls', 'mkdir', etc.
  - Code execution: 'python' for running Python scripts
  - Package management: 'pip install' for dependencies
  
For Python code, don't use python3, just use python for execution.

Follow this workflow:
1. First, explain your plan and approach to solving the task.
2. Use shell commands to gather information when needed (e.g., 'cat file.py', 'ls').
3. Write code to files using echo with redirection (e.g., 'echo "print('hello')" > script.py').
   - For multi-line files, use the here-document syntax with 'cat' (e.g., 'cat > file.py << 'EOF'\\ncode\\nEOF').
4. Execute the code using 'python script.py'.
5. After each execution, verify the results and fix any errors.
6. Continue this process until the task is complete.

Code guidelines:
- Always specify the script type in code blocks (e.g., ```python, ```sh)
- For files that need to be saved, include "# filename: <filename>" as the first line
- Provide complete, executable code that doesn't require user modification
- Include only one code block per response
- Use print statements appropriately for output, not for debugging

Self-verification:
- After executing code, analyze the output to verify correctness
- If errors occur, fix them and try again with improved code
- If your approach isn't working after multiple attempts, reconsider your strategy

Reply "TERMINATE" when the task is successfully completed."""
            

class CoderResult(BaseModel):
    dependencies: List = Field(
        description="All the packages name that has to be installed before the code execution"
    )
    content: str = Field(description="Response content in the form of code")
    code_description: str = Field(description="Description of the code")


model = AnthropicModel(
                model_name=os.environ.get("ANTHROPIC_MODEL_NAME"),
                anthropic_client=get_client()
)

coder_agent = Agent(
    model=model,
    name="Coder Agent",
    result_type=CoderResult,
    deps_type=coder_agent_deps,
    system_prompt=coder_system_message
)

ALLOWED_COMMANDS = {
    "ls", "dir", "cat", "echo", "python", "pip", 
    "mkdir", "touch", "rm", "cp", "mv"
}
@coder_agent.tool
async def execute_shell(ctx : RunContext[coder_agent_deps], command: str) -> str:
    """
    Executes a shell command within a restricted directory and returns the output.
    This consolidated tool handles terminal commands and file operations.
    """
    try:
        # Update stream output if available at high level of abstraction
        if ctx.deps.stream_output and ctx.deps.websocket:
            # Determine high-level operation type based on command
            if base_command := command.split()[0]:
                operation_message = get_high_level_operation_message(command, base_command)
                ctx.deps.stream_output.steps.append(operation_message)
                await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
        
        logfire.info(f"Executing shell command: {command}")
        
        # Define the restricted directory
        base_dir = os.path.abspath(os.path.dirname(__file__))
        restricted_dir = os.path.join(base_dir, "code_files")
        os.makedirs(restricted_dir, exist_ok=True)
        
        # Extract the base command
        base_command = command.split()[0]
        
        # Security checks
        if base_command not in ALLOWED_COMMANDS:
            error_msg = f"Operation not permitted"
            if ctx.deps.stream_output and ctx.deps.websocket:
                ctx.deps.stream_output.steps.append(error_msg)
                await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
            return f"Error: Command '{base_command}' is not allowed for security reasons."
        
        # Change to the restricted directory
        original_dir = os.getcwd()
        os.chdir(restricted_dir)
        
        try:
            # Special handling for echo with redirection (file writing)
            if ">" in command and base_command == "echo":
                # Update stream with high-level message
                if ctx.deps.stream_output and ctx.deps.websocket:
                    # Get the file name
                    file_path = command.split(">", 1)[1].strip()
                    ctx.deps.stream_output.steps.append(f"Writing content to {file_path}")
                    await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                    logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                
                # Simple parsing for echo "content" > file.txt
                parts = command.split(">", 1)
                echo_cmd = parts[0].strip()
                file_path = parts[1].strip()
                
                # Extract content between echo and > (removing quotes if present)
                content = echo_cmd[5:].strip()
                if (content.startswith('"') and content.endswith('"')) or \
                   (content.startswith("'") and content.endswith("'")):
                    content = content[1:-1]
                
                # Write to file
                try:
                    with open(file_path, "w") as file:
                        file.write(content)
                    
                    success_msg = f"Successfully wrote to {file_path}"
                    if ctx.deps.stream_output and ctx.deps.websocket:
                        ctx.deps.stream_output.steps.append(f"File {file_path} created successfully")
                        await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                        logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                        
                    return success_msg
                except Exception as e:
                    error_msg = f"Error writing to file: {str(e)}"
                    if ctx.deps.stream_output and ctx.deps.websocket:
                        ctx.deps.stream_output.steps.append(f"Failed to create file {file_path}")
                        await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                        logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                        
                    logfire.error(error_msg, exc_info=True)
                    return error_msg
            
            # Handle cat with here-document for multiline file writing
            elif "<<" in command and base_command == "cat":
                # Parse to get file name for high-level message
                cmd_parts = command.split("<<", 1)
                cat_part = cmd_parts[0].strip()
                
                if ">" in cat_part:
                    file_path = cat_part.split(">", 1)[1].strip()
                    # Update stream with more abstract message
                    if ctx.deps.stream_output and ctx.deps.websocket:
                        ctx.deps.stream_output.steps.append(f"Creating file {file_path}")
                        await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                        logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                
                try:
                    # Parse the command: cat > file.py << 'EOF'\ncode\nEOF
                    cmd_parts = command.split("<<", 1)
                    cat_part = cmd_parts[0].strip()
                    doc_part = cmd_parts[1].strip()
                    
                    # Extract filename
                    if ">" in cat_part:
                        file_path = cat_part.split(">", 1)[1].strip()
                    else:
                        error_msg = "Invalid file operation"
                        if ctx.deps.stream_output and ctx.deps.websocket:
                            ctx.deps.stream_output.steps.append(error_msg)
                            await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                            logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                        return "Error: Invalid cat command format. Must include redirection."
                    
                    # Parse the heredoc content
                    if "\n" in doc_part:
                        delimiter_and_content = doc_part.split("\n", 1)
                        delimiter = delimiter_and_content[0].strip("'").strip('"')
                        content = delimiter_and_content[1]
                        
                        # Find the end delimiter and extract content
                        if f"\n{delimiter}" in content:
                            content = content.split(f"\n{delimiter}")[0]
                            
                            # Write to file
                            with open(file_path, "w") as file:
                                file.write(content)
                                
                            success_msg = f"Successfully wrote multiline content to {file_path}"
                            if ctx.deps.stream_output and ctx.deps.websocket:
                                ctx.deps.stream_output.steps.append(f"File {file_path} created successfully")
                                await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                                logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                                
                            return success_msg
                        else:
                            error_msg = "File content format error"
                            if ctx.deps.stream_output and ctx.deps.websocket:
                                ctx.deps.stream_output.steps.append(error_msg)
                                await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                                logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                            return "Error: End delimiter not found in heredoc"
                    else:
                        error_msg = "File content format error"
                        if ctx.deps.stream_output and ctx.deps.websocket:
                            ctx.deps.stream_output.steps.append(error_msg)
                            await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                            logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                        return "Error: Invalid heredoc format"
                except Exception as e:
                    error_msg = f"Error processing cat with heredoc: {str(e)}"
                    if ctx.deps.stream_output and ctx.deps.websocket:
                        ctx.deps.stream_output.steps.append(f"Failed to create file {file_path}")
                        await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                        logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                        
                    logfire.error(error_msg, exc_info=True)
                    return error_msg
            
            # Update stream output for regular command execution with high-level description
            if ctx.deps.stream_output and ctx.deps.websocket:
                operation_msg = get_high_level_execution_message(command, base_command)
                ctx.deps.stream_output.steps.append(operation_msg)
                await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
            
            # Use shlex to properly parse the command for all other commands
            args = shlex.split(command)
            
            result = subprocess.run(
                args,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            logfire.info(f"Command executed: {result.args}")
            
            if result.returncode == 0:
                success_msg = result.stdout
                if ctx.deps.stream_output and ctx.deps.websocket:
                    operation_success_msg = get_success_message(command, base_command)
                    ctx.deps.stream_output.steps.append(operation_success_msg)
                    await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                    logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                    
                logfire.info(f"Command executed successfully: {result.stdout}")
                return success_msg
            else:
                files = os.listdir('.')
                error_msg = f"Command failed with error code {result.returncode}:\n{result.stderr}\n\nFiles in directory: {files}"
                
                if ctx.deps.stream_output and ctx.deps.websocket:
                    operation_failed_msg = get_failure_message(command, base_command)
                    ctx.deps.stream_output.steps.append(operation_failed_msg)
                    await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
                    logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
                return error_msg
        finally:
            os.chdir(original_dir)
            
    except subprocess.TimeoutExpired:
        error_msg = "Command execution timed out after 60 seconds"
        if ctx.deps.stream_output and ctx.deps.websocket:
            ctx.deps.stream_output.steps.append("Operation timed out")
            await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))
            logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
        return error_msg
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        if ctx.deps.stream_output and ctx.deps.websocket:
            ctx.deps.stream_output.steps.append("Operation failed")
            await ctx.deps.websocket.send_text(json.dumps(asdict(ctx.deps.stream_output)))

            logfire.debug(f"WebSocket message sent: {json.dumps(asdict(ctx.deps.stream_output))}")
            
        logfire.error(error_msg, exc_info=True)
        return error_msg

def get_high_level_operation_message(command: str, base_command: str) -> str:
    """Returns a high-level description of the operation being performed"""
    if base_command == "ls" or base_command == "dir":
        return "Listing files in directory"
    elif base_command == "cat" and not "<<" in command:
        # For simple cat command without heredoc
        file_name = command.split(" ", 1)[1] if len(command.split(" ", 1)) > 1 else "file"
        return f"Reading file {file_name}"
    elif base_command == "echo" and ">" in command:
        file_name = command.split(">", 1)[1].strip()
        return f"Creating file {file_name}"
    elif base_command == "cat" and "<<" in command:
        parts = command.split(">", 1)
        if len(parts) > 1:
            file_name = parts[1].strip().split(" ", 1)[0]
            return f"Creating file {file_name}"
        return "Creating file"
    elif base_command == "python":
        script_name = command.split(" ", 1)[1] if len(command.split(" ", 1)) > 1 else "script"
        return f"Running Python script {script_name}"
    elif base_command == "pip":
        if "install" in command:
            packages = command.split("install ", 1)[1] if "install " in command else "packages"
            return f"Installing package(s): {packages}"
        return "Managing Python packages"
    elif base_command == "mkdir":
        dir_name = command.split(" ", 1)[1] if len(command.split(" ", 1)) > 1 else "directory"
        return f"Creating directory {dir_name}"
    elif base_command == "touch":
        file_name = command.split(" ", 1)[1] if len(command.split(" ", 1)) > 1 else "file"
        return f"Creating empty file {file_name}"
    elif base_command == "rm":
        file_name = command.split(" ", 1)[1] if len(command.split(" ", 1)) > 1 else "file"
        return f"Removing {file_name}"
    elif base_command == "cp":
        parts = command.split(" ")
        if len(parts) >= 3:
            return f"Copying {parts[1]} to {parts[2]}"
        return "Copying file"
    elif base_command == "mv":
        parts = command.split(" ")
        if len(parts) >= 3:
            return f"Moving {parts[1]} to {parts[2]}"
        return "Moving file"
    else:
        return f"Executing operation: {base_command}"

def get_high_level_execution_message(command: str, base_command: str) -> str:
    """Returns a high-level execution message for the command"""
    if base_command == "python":
        script_name = command.split(" ", 1)[1] if len(command.split(" ", 1)) > 1 else "script"
        return f"Executing Python script {script_name}"
    return f"Executing operation"

def get_success_message(command: str, base_command: str) -> str:
    """Returns a success message based on the command type"""
    if base_command == "ls" or base_command == "dir":
        return "Files listed successfully"
    elif base_command == "cat" and not "<<" in command:
        return "File read successfully"
    elif base_command == "python":
        return "Python script executed successfully"
    elif base_command == "pip" and "install" in command:
        return "Package installation completed"
    elif base_command == "mkdir":
        return "Directory created successfully"
    elif base_command == "touch":
        return "File created successfully"
    elif base_command == "rm":
        return "File removed successfully"
    elif base_command == "cp":
        return "File copied successfully"
    elif base_command == "mv":
        return "File moved successfully"
    else:
        return "Operation completed successfully"

def get_failure_message(command: str, base_command: str) -> str:
    """Returns a failure message based on the command type"""
    if base_command == "ls" or base_command == "dir":
        return "Failed to list files"
    elif base_command == "cat" and not "<<" in command:
        return "Failed to read file"
    elif base_command == "python":
        return "Python script execution failed"
    elif base_command == "pip" and "install" in command:
        return "Package installation failed"
    elif base_command == "mkdir":
        return "Failed to create directory"
    elif base_command == "touch":
        return "Failed to create file"
    elif base_command == "rm":
        return "Failed to remove file"
    elif base_command == "cp":
        return "Failed to copy file"
    elif base_command == "mv":
        return "Failed to move file"
    else:
        return "Operation failed"