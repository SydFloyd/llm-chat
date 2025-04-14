import anthropic
import logging
import os
import time

from config import cfg

# Set up logging
logger = logging.getLogger(__name__)
from utils.view_file import view_file
from utils.view_directory import view_directory
from utils.str_replace import str_replace
from utils.create_file import create_file
from utils.insert_text import insert_text
from utils.undo_edit import undo_edit

class Claude:
    def __init__(self, 
                 model='claude-3-7-sonnet-20250219', 
                 max_tokens=2048, 
                 temperature=1, 
                 system_message=None, 
                 thinking_budget=0,
                 injected_messages=None,
                 text_editor=False,
                 repo_path=".",):
        logger.info(f"Initializing Claude with model={model}, max_tokens={max_tokens}, temperature={temperature}")
        logger.debug(f"Additional params: thinking_budget={thinking_budget}, text_editor={text_editor}, repo_path={repo_path}")
        
        self._init_client()

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_message = system_message
        self.injected_messages = injected_messages
        self.text_editor = text_editor
        self.repo_path = repo_path

        self.message_history = []

        self.thinking_budget = thinking_budget

        self.last_api_call = 0
        self.cooldown = 15  # seconds

        self._validate_config()
        logger.info("Claude initialization completed successfully")

    def _init_client(self):
        logger.debug("Initializing Anthropic client")
        try:
            self.client = anthropic.Anthropic(
                api_key=cfg.anthropic_api_key,
            )
            if self.client is None:
                logger.error("Anthropic client initialization failed")
                raise ValueError("Anthropic client initialization failed.")
            logger.debug("Anthropic client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            raise
        
    def _validate_config(self):
        logger.debug("Validating configuration")
        if self.thinking_budget > 0 and not self.model.startswith("claude-3-7-sonnet"):
            logger.error(f"Invalid config: thinking budget {self.thinking_budget} not compatible with model {self.model}")
            raise ValueError("Thinking budget is only available for Claude 3.7 Sonnet.")
        if self.thinking_budget < 0:
            logger.error(f"Invalid config: negative thinking budget {self.thinking_budget}")
            raise ValueError("Thinking budget cannot be negative.")
        if self.thinking_budget < 1024 and self.thinking_budget > 0:
            logger.error(f"Invalid config: thinking budget {self.thinking_budget} too small")
            raise ValueError("Thinking budget must be at least 1024 tokens.")
        if self.thinking_budget > self.max_tokens:
            logger.error(f"Invalid config: thinking budget {self.thinking_budget} exceeds max tokens {self.max_tokens}")
            raise ValueError("Thinking budget must be less than max tokens.")
        
        if self.text_editor and not self.model.startswith("claude-3-7-sonnet"):
            logger.error(f"Invalid config: text editor not compatible with model {self.model}")
            raise ValueError("Text editor is only available for Claude 3.5 Sonnet and Claude 3.7 Sonnet.")
            
        logger.debug("Configuration validated successfully")

    def _compile_messages(self, prompt):
        messages = []
        if self.injected_messages:
            messages.extend(self.injected_messages)
        messages.extend(self.message_history)
        messages.append({"role": "user", "content": prompt})
        return messages
    
    def handle_editor_tool(self, tool_call):
        """Handle the text editor tool call. Runs commands in repo_path."""
        input_params = tool_call.input
        command = input_params.get('command', '')
        file_path = input_params.get('path', '')
        
        if command == 'view':
            # View file content or directory
            if os.path.isdir(file_path):
                # Optional parameter to show detailed directory listing
                show_details = input_params.get('details', False)
                return view_directory(file_path, show_details)
            elif os.path.isfile(file_path):
                # For file viewing, use the previously defined view_file function
                file_content, error_occurred = view_file(file_path, input_params.get('view_range'))
                return file_content, error_occurred
            else:
                return f"Error: '{file_path}' does not exist or is not accessible", True

        elif command == 'str_replace':
            # Replace text in file
            old_str = input_params.get('old_str', '')
            new_str = input_params.get('new_str', None)
            if not new_str:
                return "Error: 'new_str' is required", True

            return str_replace(file_path, old_str, new_str)
        
        elif command == 'create':
            # file_text: The content to write to the new file
            file_text = input_params.get('file_text', '')
            overwrite = input_params.get('overwrite', False)
    
            return create_file(file_path, file_text, overwrite)
        
        elif command == 'insert':
            # Insert text at location
            # insert_line: The line number after which to insert the text (0 for beginning of file)
            # new_str: The text to insert
            # preserve_newline (optional): Whether to add a newline character if not present
            insert_line = input_params.get('insert_line', 0)
            new_str = input_params.get('new_str', '')
            preserve_newline = input_params.get('preserve_newline', True)
            
            return insert_text(file_path, new_str, insert_line, preserve_newline)

        elif command == 'undo_edit':
            # Restore from backup
            # path: The path to the file whose last edit should be undone
            return undo_edit(file_path)
    
    def prompt(self, prompt):
        kwargs = {
            "model": self.model,
            "messages": self._compile_messages(prompt),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        if self.system_message:
            kwargs["system"] = self.system_message + f"\nCWD:\n{os.listdir(self.repo_path)} "
        if self.thinking_budget:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget
            }
        if self.text_editor:
            kwargs["tools"] = [
                {
                    "type": "text_editor_20250124",
                    "name": "str_replace_editor"
                }
            ]
        if time.time() - self.last_api_call < self.cooldown:
            time.sleep(self.cooldown - (time.time() - self.last_api_call))
        # Call the API
        response = self.client.messages.create(**kwargs)
        self.last_api_call = time.time()

        # Handle the response
        saved_response = []
        tool_called = False
        tool_results = []
        for content in response.content:
            if content.type == "thinking":
                # Handle thinking block
                print(f"\n\n    Thinking: {content.thinking}")

            elif content.type == "text":
                # Handle text block
                print(f"\n\n    Claude: {content.text}")
                saved_response.append({"type": "text", "text": content.text})

            if content.type == "tool_use":
                print(f"\n\n    Tool: {content.input.get("command", "ERROR")} called with {content.input.get("path", "ERROR")}")
                tool_called = True
                # Execute the tool based on command
                saved_response.append({"type": "tool_use", 
                                       "id": content.id,
                                       "name": content.name,
                                       "input": content.input})
                result, is_error = self.handle_editor_tool(content)
                
                # Return result to Claude
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": content.id,
                    "content": result
                }
                if is_error:
                    tool_result["is_error"] = is_error
                    logger.warning(f"Tool Error: {result}")
                tool_results.append(tool_result)

        self.message_history.append({"role": "user", "content": prompt})
        self.message_history.append({"role": "assistant", "content": saved_response})
        
        if tool_called:
            self.prompt(tool_results)

anthropic_client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key=cfg.anthropic_api_key,
)

def list_anthropic_models(limit=20):
    models = anthropic_client.models.list(limit=limit)
    model_mappping = {x.display_name: x.id for x in models.data}
    return model_mappping

if __name__ == "__main__":
    # Initialize logging
    logger = cfg.setup_logging()
    logger.info("Application starting")
    
    # print(list_anthropic_models())

    system_message = (
        "You are a helpful coding assistant. "
        "You are on a Windows machine. "
        "Make your tool calls with relative paths. "
    )

    with open("llm.txt", "r") as f:
        paths_to_include = f.readlines()
    paths_to_include = [x.strip() for x in paths_to_include]
    for path in paths_to_include:
        if os.path.isfile(path):
            with open(path, "r") as f:
                system_message += f"\n{path}:\n{f.read()}\n"
        elif os.path.isdir(path):
            system_message += f"\n{path}:\n{os.listdir(path)}\n"
        else:
            system_message += f"\n Extra information: {path}\n"

    m = Claude(system_message=system_message, text_editor=True)
    # m = Claude(thinking_budget=1024)
    logger.info("Claude instance initialized")
    prompt = (
        "Please finish adding logging to utils/view_file.py. "
    )
    print(m.prompt(prompt))

    while True:
        prompt = input("Prompt: ")
        if prompt == "exit":
            logger.info("User requested exit")
            break
        m.prompt(prompt)
    
    logger.info("Application shutting down")
