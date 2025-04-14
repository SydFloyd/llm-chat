import anthropic
from pathlib import Path
import os

from config import cfg
from utils.view_file import view_file
from utils.view_directory import view_directory
from utils.str_replace import str_replace
from utils.create_file import create_file
from utils.insert_text import insert_text
from utils.undo_edit import undo_edit

def to_relative(absolute_path):
    # Convert string path to Path object and make it relative to current directory
    return Path(absolute_path).relative_to('/')

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

        self._validate_config()

    def _init_client(self):
        self.client = anthropic.Anthropic(
            api_key=cfg.anthropic_api_key,
        )
        if self.client is None:
            raise ValueError("Anthropic client initialization failed.")
        
    def _validate_config(self):
        if self.thinking_budget > 0 and not self.model.startswith("claude-3-7-sonnet"):
            raise ValueError("Thinking budget is only available for Claude 3.7 Sonnet.")
        if self.thinking_budget < 0:
            raise ValueError("Thinking budget cannot be negative.")
        if self.thinking_budget < 1024 and self.thinking_budget > 0:
            raise ValueError("Thinking budget must be at least 1024 tokens.")
        if self.thinking_budget > self.max_tokens:
            raise ValueError("Thinking budget must be less than max tokens.")
        
        if self.text_editor and not self.model.startswith("claude-3-7-sonnet"):
            raise ValueError("Text editor is only available for Claude 3.5 Sonnet and Claude 3.7 Sonnet.")

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
        # file_path = to_relative(file_path)
        print(f"File path: {file_path}")
        if not os.path.exists(file_path):
            return "Error: File not found.", True
        
        print(f"\n\n    Tool Call: Command: {command}, File: {file_path}, Input: {input_params}")
        
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
            new_str = input_params.get('new_str', '')

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
        from pprint import pprint
        pprint(self._compile_messages(prompt))
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
        response = self.client.messages.create(**kwargs)

        # print(response) # debug

        # Handle the response
        saved_response = []
        tool_called = False
        tool_results = []
        for content in response.content:
            if content.type == "thinking":
                # Handle thinking block
                print(f"\n\n    Thinking: {content.thinking}")
                answer = content.thinking

            elif content.type == "text":
                # Handle text block
                print(f"\n\n    Claude: {content.text}")
                saved_response.append({"type": "text", "text": content.text})

            if content.type == "tool_use":
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
    # print(list_anthropic_models())

    system_message = (
        "You are a helpful coding assistant. "
        "You are on a Windows machine. "
        "Make your tool calls with relative paths. "
    )

    m = Claude(system_message=system_message, text_editor=True)
    # m = Claude(thinking_budget=1024)
    print(m.prompt("What does main.py do?"))

    while True:
        prompt = input("Prompt: ")
        if prompt == "exit":
            break
        m.prompt(prompt)
