# Standard library imports
import os

# Third-party imports
from dotenv import load_dotenv
from fastapi import WebSocket
import logfire
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel

# Local application imports
# from utils.ant_client import get_client #We use the new model_factory
from utils.model_client import get_model

model = get_model()


load_dotenv()

agents = ["coder_agent", "web_surfer_agent"]


agent_descriptions = "\n".join(f"Name: {agent}\n" for agent in agents)

planner_prompt = f"""You are a helpful AI assistant that creates plans to solve tasks. You have access to a terminal tool for reading and writing plans to files.

<rules>
    <input_processing> 
        - You are provided with a team description that contains information about the team members and their expertise.
        - You need to create a plan that leverages these team members effectively to solve the given task.
        - You have access to a terminal tool for reading and writing plans to files in the planner directory.
    </input_processing> 

    <output_processing>
        - You need to generate a plan in a clear, bullet-point format.
        - After creating the plan, use the execute_terminal tool to save it to todo.md in the planner directory.
        - The plan should specify which team members handle which parts of the task.
        - You can use the execute_terminal tool to check existing plans before creating new ones.
        - You can use the execute_terminal tool with the 'ls' command to see what plans are already available.
    </output_processing>

    <terminal_usage>
        - Use "cat filename" to read a file (e.g., "cat todo.md")
        - Use "echo 'content' > filename" for simple file writing (e.g., "echo 'This is a plan' > todo.md")
        - Use "cat > filename << 'EOF'\\nMultiline content\\nMore lines\\nEOF" for multiline file writing
        - Use "ls" to list all files in the planner directory
        - Only read and write operations are permitted within the planner directory
    </terminal_usage>

    <critical>
        - Always save your plan to todo.md using the execute_terminal tool.
        - You always need to generate a plan that satisfies the request strictly using the agents that we have.
        - Never try to answer the question yourself no matter how simple it is.
        - If there are any weblinks/file paths, include them in the plan exactly as provided by the user, without any modification.
        - If there are any instructions in the original question, include them in the plan as is.
        - Don't add agents unnecessarily to the plan. Use only the agents that are absolutely necessary to solve the task.
        - After creating a plan, always verify it was saved correctly by reading the file.
        - coder agent can code and execute commands, web_surfer_agent can browse the web and extract information.
    </critical>
</rules>

Available agents: 

{agent_descriptions}
"""

class PlannerResult(BaseModel):
    plan: str = Field(description="The generated plan in a string format")

model = get_model()

planner_agent = Agent(
    model=model,
    name="Planner Agent",
    result_type=PlannerResult,
    system_prompt=planner_prompt 
)
@planner_agent.tool_plain
async def execute_terminal(command: str) -> str:
    """
    Executes a terminal command within the planner directory for file operations.
    This consolidated tool handles reading and writing plan files.
    Restricted to only read and write operations for security.
    """
    try:
        logfire.info(f"Executing terminal command: {command}")
        
        # Define the restricted directory
        base_dir = os.path.abspath(os.path.dirname(__file__))
        planner_dir = os.path.join(base_dir, "planner")
        os.makedirs(planner_dir, exist_ok=True)
        
        # Extract the base command
        base_command = command.split()[0]
        
        # Allow only read and write operations
        ALLOWED_COMMANDS = {"cat", "echo", "ls"}
        
        # Security checks
        if base_command not in ALLOWED_COMMANDS:
            return f"Error: Command '{base_command}' is not allowed. Only read and write operations are permitted."
        
        if ".." in command or "~" in command or "/" in command:
            return "Error: Path traversal attempts are not allowed."
        
        # Change to the restricted directory
        original_dir = os.getcwd()
        os.chdir(planner_dir)
        
        try:
            # Special handling for echo with redirection (file writing)
            if ">" in command and base_command == "echo":
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
                    return f"Successfully wrote to {file_path}"
                except Exception as e:
                    logfire.error(f"Error writing to file: {str(e)}", exc_info=True)
                    return f"Error writing to file: {str(e)}"
            
            # Handle cat with here-document for multiline file writing
            elif "<<" in command and base_command == "cat":
                try:
                    # Parse the command: cat > file.md << 'EOF'\nplan content\nEOF
                    cmd_parts = command.split("<<", 1)
                    cat_part = cmd_parts[0].strip()
                    doc_part = cmd_parts[1].strip()
                    
                    # Extract filename
                    if ">" in cat_part:
                        file_path = cat_part.split(">", 1)[1].strip()
                    else:
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
                            return f"Successfully wrote multiline content to {file_path}"
                        else:
                            return "Error: End delimiter not found in heredoc"
                    else:
                        return "Error: Invalid heredoc format"
                except Exception as e:
                    logfire.error(f"Error processing cat with heredoc: {str(e)}", exc_info=True)
                    return f"Error processing cat with heredoc: {str(e)}"
            
            # Handle cat for reading files
            elif base_command == "cat" and ">" not in command and "<<" not in command:
                try:
                    file_path = command.split()[1]
                    with open(file_path, "r") as file:
                        content = file.read()
                    return content
                except Exception as e:
                    logfire.error(f"Error reading file: {str(e)}", exc_info=True)
                    return f"Error reading file: {str(e)}"
            
            # Handle ls for listing files
            elif base_command == "ls":
                try:
                    files = os.listdir('.')
                    return "Files in planner directory:\n" + "\n".join(files)
                except Exception as e:
                    logfire.error(f"Error listing files: {str(e)}", exc_info=True)
                    return f"Error listing files: {str(e)}"
            else:
                return f"Error: Command '{command}' is not supported. Only read and write operations are permitted."
            
        finally:
            os.chdir(original_dir)
            
    except Exception as e:
        logfire.error(f"Error executing command: {str(e)}", exc_info=True)
        return f"Error executing command: {str(e)}"