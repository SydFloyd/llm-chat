"""
Claude AI Client Module

This module provides interfaces for interacting with the Anthropic Claude API,
with support for tools, thinking functionality, and conversation management.
"""

import anthropic
import logging
import os
import time
from typing import Dict, List, Optional, Tuple, Union, Any

from config import cfg

# Set up logging
logger = logging.getLogger(__name__)

# Import utility functions for file and tool operations
from utils import view_file, view_directory, str_replace, create_file, insert_text, undo_edit


class ToolHandler:
    """Handles the execution of tool operations requested by Claude."""
    
    @staticmethod
    def handle_tool(tool_call: Any) -> Tuple[str, bool]:
        """
        Process a tool call from Claude and execute the appropriate action.
        
        Args:
            tool_call: The tool call object from Claude's response
            
        Returns:
            Tuple of (result_content, is_error)
        """
        input_params = tool_call.input
        command = input_params.get('command', '')
        file_path = input_params.get('path', '')
        
        command_handlers = {
            'view': ToolHandler._handle_view,
            'str_replace': ToolHandler._handle_str_replace,
            'create': ToolHandler._handle_create,
            'insert': ToolHandler._handle_insert,
            'undo_edit': ToolHandler._handle_undo_edit
        }
        
        if command in command_handlers:
            return command_handlers[command](input_params, file_path)
        else:
            return f"Error: Unknown command '{command}'", True
    
    @staticmethod
    def _handle_view(params: Dict, file_path: str) -> Tuple[str, bool]:
        """Handle view command for files or directories."""
        if os.path.isdir(file_path):
            show_details = params.get('details', False)
            return view_directory(file_path, show_details)
        elif os.path.isfile(file_path):
            file_content, error_occurred = view_file(file_path, params.get('view_range'))
            return file_content, error_occurred
        else:
            return f"Error: '{file_path}' does not exist or is not accessible", True
    
    @staticmethod
    def _handle_str_replace(params: Dict, file_path: str) -> Tuple[str, bool]:
        """Handle string replacement in files."""
        old_str = params.get('old_str', '')
        new_str = params.get('new_str', None)
        if not new_str:
            return "Error: 'new_str' is required", True
        return str_replace(file_path, old_str, new_str)
    
    @staticmethod
    def _handle_create(params: Dict, file_path: str) -> Tuple[str, bool]:
        """Handle file creation."""
        file_text = params.get('file_text', '')
        overwrite = params.get('overwrite', False)
        return create_file(file_path, file_text, overwrite)
    
    @staticmethod
    def _handle_insert(params: Dict, file_path: str) -> Tuple[str, bool]:
        """Handle text insertion into files."""
        insert_line = params.get('insert_line', 0)
        new_str = params.get('new_str', '')
        preserve_newline = params.get('preserve_newline', True)
        return insert_text(file_path, new_str, insert_line, preserve_newline)
    
    @staticmethod
    def _handle_undo_edit(params: Dict, file_path: str) -> Tuple[str, bool]:
        """Handle undoing the last edit to a file."""
        return undo_edit(file_path)


class ClaudeClient:
    """
    Client for interacting with Anthropic's Claude AI models.
    
    This class provides methods to initialize, configure, and communicate with 
    Claude models, supporting features like thinking, tool use, and conversation history.
    """
    
    # Default model configurations
    DEFAULT_MODEL = 'claude-3-7-sonnet-20250219'
    DEFAULT_MAX_TOKENS = 2048 * 4
    DEFAULT_TEMPERATURE = 1
    DEFAULT_COOLDOWN = 15  # seconds between API calls
    
    # Models that support thinking
    THINKING_MODELS = ['claude-3-7-sonnet']
    
    # Models that support the text editor tool
    TEXT_EDITOR_MODELS = ['claude-3-5-sonnet', 'claude-3-7-sonnet']
    
    def __init__(self, 
                 model: str = DEFAULT_MODEL, 
                 max_tokens: int = DEFAULT_MAX_TOKENS, 
                 temperature: float = DEFAULT_TEMPERATURE, 
                 system_message: Optional[str] = None, 
                 thinking_budget: int = 0,
                 injected_messages: Optional[List[Dict]] = None,
                 text_editor: bool = False,
                 repo_path: str = ".",
                 cooldown: int = DEFAULT_COOLDOWN):
        """
        Initialize a Claude client instance.
        
        Args:
            model: The Claude model to use
            max_tokens: Maximum tokens in the response
            temperature: Temperature for response generation
            system_message: System prompt/context
            thinking_budget: Budget for Claude's thinking (only for supported models)
            injected_messages: Pre-loaded conversation context
            text_editor: Whether to enable the text editor tool
            repo_path: Base path for file operations
            cooldown: Minimum time between API calls in seconds
        """
        logger.info(f"Initializing Claude with model={model}, max_tokens={max_tokens}, temperature={temperature}")
        logger.debug(f"Additional params: thinking_budget={thinking_budget}, text_editor={text_editor}, repo_path={repo_path}")
        
        # Initialize API client
        self._init_client()
        
        # Store configuration
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.system_message = system_message
        self.injected_messages = injected_messages or []
        self.text_editor = text_editor
        self.repo_path = repo_path
        self.cooldown = cooldown
        
        # Conversation state
        self.message_history = []
        self.thinking_budget = thinking_budget
        self.last_api_call = 0
        
        # Validate configuration
        self._validate_config()
        logger.info("Claude initialization completed successfully")

    def _init_client(self):
        """Initialize the Anthropic API client."""
        logger.debug("Initializing Anthropic client")
        try:
            self.client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
            if self.client is None:
                logger.error("Anthropic client initialization failed")
                raise ValueError("Anthropic client initialization failed.")
            logger.debug("Anthropic client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            raise
        
    def _validate_config(self):
        """Validate the client configuration."""
        logger.debug("Validating configuration")
        
        # Validate thinking budget compatibility
        has_thinking_support = any(model_prefix in self.model for model_prefix in self.THINKING_MODELS)
        if self.thinking_budget > 0 and not has_thinking_support:
            logger.error(f"Invalid config: thinking budget {self.thinking_budget} not compatible with model {self.model}")
            raise ValueError(f"Thinking budget is only available for these models: {', '.join(self.THINKING_MODELS)}")
        
        # Validate thinking budget values
        if self.thinking_budget < 0:
            logger.error(f"Invalid config: negative thinking budget {self.thinking_budget}")
            raise ValueError("Thinking budget cannot be negative.")
        if 0 < self.thinking_budget < 1024:
            logger.error(f"Invalid config: thinking budget {self.thinking_budget} too small")
            raise ValueError("Thinking budget must be at least 1024 tokens.")
        if self.thinking_budget > self.max_tokens:
            logger.error(f"Invalid config: thinking budget {self.thinking_budget} exceeds max tokens {self.max_tokens}")
            raise ValueError("Thinking budget must be less than max tokens.")
        
        # Validate text editor compatibility
        has_text_editor_support = any(model_prefix in self.model for model_prefix in self.TEXT_EDITOR_MODELS)
        if self.text_editor and not has_text_editor_support:
            logger.error(f"Invalid config: text editor not compatible with model {self.model}")
            raise ValueError(f"Text editor is only available for these models: {', '.join(self.TEXT_EDITOR_MODELS)}")
            
        logger.debug("Configuration validated successfully")

    def _compile_messages(self, prompt: Union[str, List[Dict]]) -> List[Dict]:
        """
        Compile the message history and new prompt into a message array.
        
        Args:
            prompt: Either a string prompt or a list of tool results
            
        Returns:
            List of messages for the API call
        """
        messages = []
        
        # Add any injected messages (pre-conversation context)
        if self.injected_messages:
            messages.extend(self.injected_messages)
            
        # Add conversation history
        messages.extend(self.message_history)
        
        # Add the new prompt
        messages.append({"role": "user", "content": prompt})
            
        return messages
    
    def prompt(self, prompt: Union[str, List[Dict]]) -> str:
        """
        Send a prompt to Claude and process the response.
        
        Args:
            prompt: The prompt to send to Claude or tool results
            
        Returns:
            The complete response from Claude
        """
        # Prepare API call parameters
        kwargs = self._prepare_api_params(prompt)
        
        # Apply rate limiting if needed
        self._apply_rate_limit()
        
        # Call the API
        response = self.client.messages.create(**kwargs)
        self.last_api_call = time.time()

        # Process and handle the response
        return self._process_response(prompt, response)
    
    def _prepare_api_params(self, prompt: Union[str, List[Dict]]) -> Dict:
        """Prepare parameters for the API call."""
        kwargs = {
            "model": self.model,
            "messages": self._compile_messages(prompt),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        
        # Add system message if provided
        if self.system_message:
            # Include current working directory information
            kwargs["system"] = self.system_message + f"\nCWD:\n{os.listdir(self.repo_path)} "
        
        # Add thinking capability if budget is specified
        if self.thinking_budget:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self.thinking_budget
            }
        
        # Add text editor tool if enabled
        if self.text_editor:
            kwargs["tools"] = [
                {
                    "type": "text_editor_20250124",
                    "name": "str_replace_editor"
                }
            ]
        
        return kwargs
    
    def _apply_rate_limit(self):
        """Apply rate limiting between API calls."""
        elapsed = time.time() - self.last_api_call
        if elapsed < self.cooldown:
            wait_time = self.cooldown - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
    
    def _process_response(self, prompt: Union[str, List[Dict]], response: Any) -> str:
        """
        Process the response from Claude.
        
        Args:
            prompt: The original prompt
            response: The response from the API
            
        Returns:
            The final response text
        """
        # Initialize tracking variables
        saved_response = []
        tool_called = False
        tool_results = []
        
        # Process each content block in the response
        for content in response.content:
            if content.type == "thinking":
                saved_response.append(self._handle_thinking_content(content))
            elif content.type == "text":
                saved_response.append(self._handle_text_content(content))
            elif content.type == "tool_use":
                tool_result = self._handle_tool_content(content)
                saved_response.append(tool_result["saved_response"])
                tool_called = True
                tool_results.extend(tool_result["tool_results"])

        # Update conversation history
        self.message_history.append({"role": "user", "content": prompt})
        self.message_history.append({"role": "assistant", "content": saved_response})
        
        # If a tool was called, continue the conversation with the tool results
        if tool_called:
            return self.prompt(tool_results)
            
        # Return the response text for the final response
        return self._extract_response_text(saved_response)
        
    def _handle_thinking_content(self, content: Any) -> Dict:
        """Handle thinking content from Claude's response."""
        thinking_text = cfg.colors.thinking(f"\n\n\n    Thinking:\n\n{content.thinking}")
        print(thinking_text)
        return {
            "type": "thinking", 
            "thinking": content.thinking, 
            "signature": content.signature
        }
        
    def _handle_text_content(self, content: Any) -> Dict:
        """Handle text content from Claude's response."""
        claude_text = cfg.colors.claude_output(f"\n\n\n    Claude:\n\n{content.text}")
        print(claude_text)
        return {"type": "text", "text": content.text}
        
    def _handle_tool_content(self, content: Any) -> Dict:
        """
        Handle tool use content from Claude's response.
        
        Returns:
            Dict containing saved_response and tool_results
        """
        command = content.input.get("command", "ERROR")
        path = content.input.get("path", "ERROR")
        tool_text = cfg.colors.tool_call(f"\n\n\n    Tool: {command} called on {path}")
        print(tool_text)
        
        saved_response = {
            "type": "tool_use", 
            "id": content.id,
            "name": content.name,
            "input": content.input
        }
        
        # Execute the tool operation
        result, is_error = ToolHandler.handle_tool(content)
        
        # Format the tool result for Claude
        tool_result = {
            "type": "tool_result",
            "tool_use_id": content.id,
            "content": result
        }
        if is_error:
            tool_result["is_error"] = is_error
            logger.warning(f"Tool Error: {result}")
            
        return {
            "saved_response": saved_response,
            "tool_results": [tool_result]
        }
    
    def _extract_response_text(self, saved_response: List[Dict]) -> str:
        """Extract the text content from the response."""
        text_parts = []
        for item in saved_response:
            if item["type"] == "text":
                text_parts.append(item["text"])
        return "\n".join(text_parts)
    
    def get_conversation_history(self) -> List[Dict]:
        """
        Get the current conversation history.
        
        Returns:
            The message history as a list of role/content pairs
        """
        return self.message_history
    
    def clear_conversation(self):
        """Clear the conversation history."""
        self.message_history = []
        logger.info("Conversation history cleared")


def list_anthropic_models(limit=20):
    """
    List all available Anthropic models.
    
    Args:
        limit: Maximum number of models to retrieve
        
    Returns:
        Dictionary mapping display names to model IDs
    """
    client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
    models = client.models.list(limit=limit)
    model_mapping = {x.display_name: x.id for x in models.data}
    return model_mapping

def load_context_from_file(context_file="llm.txt") -> str:
    """
    Load additional context from a file listing paths to include.
    
    Args:
        context_file: Path to file containing paths to include
        
    Returns:
        Compiled system message with included file contents
    """
    base_message = (
        "You are a helpful coding assistant. "
        "You are on a Windows machine. "
        "Make your tool calls with relative paths. "
    )
    
    try:
        with open(context_file, "r") as f:
            paths_to_include = f.readlines()
            
        paths_to_include = [x.strip() for x in paths_to_include if x.strip()]
        
        for path in paths_to_include:
            if os.path.isfile(path):
                with open(path, "r") as f:
                    base_message += f"\n{path} file:\n{f.read()}\n\n"
            elif os.path.isdir(path):
                base_message += f"\n{path} dir:\n{os.listdir(path)}\n\n"
            else:
                base_message += f"\n{path}\n"
    except Exception as e:
        logger.error(f"Error loading context from {context_file}: {str(e)}")
        
    return base_message


if __name__ == "__main__":
    # Initialize logging
    logger = cfg.setup_logging()
    logger.info("Application starting")
    
    # Load system message with additional context
    system_message = load_context_from_file("llm.txt")
    
    # Initialize the Claude client
    client = ClaudeClient(
        system_message=system_message, 
        thinking_budget=2048, 
        text_editor=True
    )
    logger.info("Claude client initialized")
    
    # Example initial prompt
    initial_prompt = (
        "Tell me what improvements can be made to claude.py.  Do not make any changes yet. "
    )
    print("Initial prompt sent.")
    client.prompt(initial_prompt)
    
    # Main interaction loop
    while True:
        try:
            prompt_text = cfg.colors.user_prompt("\nPrompt: ")
            user_prompt = input(prompt_text)
            if user_prompt.lower() in ("exit", "quit"):
                logger.info("User requested exit")
                break
                
            client.prompt(user_prompt)
            
        except KeyboardInterrupt:
            logger.info("User interrupted the application")
            break
        except Exception as e:
            logger.error(f"Error during prompt: {str(e)}")
            print(f"An error occurred: {str(e)}")
    
    logger.info("Application shutting down")
