"""
Claude AI Client Module

This module provides interfaces for interacting with the Anthropic Claude API,
with support for tools, thinking functionality, and conversation management.
"""

import anthropic
import logging
import os
import time
import collections
from typing import Dict, List, Optional, Tuple, Union, Any, Deque

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
    DEFAULT_MAX_TOKENS = 2048 * 8
    DEFAULT_TEMPERATURE = 1
    DEFAULT_COOLDOWN = 3  # minimum seconds between API calls
    
    # Rate limit configurations
    RATE_LIMIT_TOKENS = 20000  # Anthropic's rate limit: 20k tokens per minute
    RATE_LIMIT_WINDOW = 60  # Window size in seconds (1 minute)
    
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
                 cooldown: int = DEFAULT_COOLDOWN,
                 rate_limit_tokens: int = RATE_LIMIT_TOKENS,
                 rate_limit_window: int = RATE_LIMIT_WINDOW):
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
            rate_limit_tokens: Maximum tokens allowed per minute (Anthropic limit)
            rate_limit_window: Time window for rate limiting in seconds
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
        self.rate_limit_tokens = rate_limit_tokens
        self.rate_limit_window = rate_limit_window
        
        # Conversation state
        self.message_history = []
        self.thinking_budget = thinking_budget
        self.last_api_call = 0
        
        # Rate limiting state
        self.token_usage_history: Deque[Tuple[float, int]] = collections.deque()
        
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

        # Track token usage
        self._track_token_usage(response)
        
        # Process and handle the response
        return self._process_response(prompt, response)
        
    def _track_token_usage(self, response):
        """
        Track token usage for rate limiting purposes.
        
        Args:
            response: The API response containing usage information
        """
        # Extract usage statistics
        if hasattr(response, 'usage') and response.usage:
            input_tokens = getattr(response.usage, 'input_tokens', 0)
            output_tokens = getattr(response.usage, 'output_tokens', 0)
            total_tokens = input_tokens + output_tokens
            
            # Record usage with timestamp
            self.token_usage_history.append((time.time(), total_tokens))
            
            logger.debug(f"API call token usage - Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
        else:
            logger.warning("Token usage information not available in response")
            # If usage information is not available, use a conservative estimate
            estimated_tokens = self.max_tokens + 1000  # Conservative estimate
            self.token_usage_history.append((time.time(), estimated_tokens))
            logger.debug(f"No token usage information available, using estimate: {estimated_tokens} tokens")
    
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
        """
        Apply dynamic rate limiting based on token usage history.
        
        This method:
        1. Removes usage records older than the rate limit window
        2. Calculates current token usage within the window
        3. Determines wait time needed to stay under the token rate limit
        4. Enforces a minimum cooldown period between requests
        """
        current_time = time.time()
        
        # Apply minimum cooldown between requests
        elapsed = current_time - self.last_api_call
        if elapsed < self.cooldown:
            min_wait_time = self.cooldown - elapsed
            logger.debug(f"Minimum cooldown: waiting {min_wait_time:.2f} seconds")
            time.sleep(min_wait_time)
            current_time = time.time()  # Update current time after waiting
        
        # Remove token usage records older than the rate limit window
        window_start = current_time - self.rate_limit_window
        while self.token_usage_history and self.token_usage_history[0][0] < window_start:
            self.token_usage_history.popleft()
        
        # Calculate current token usage within the window
        current_usage = sum(usage[1] for usage in self.token_usage_history)
        
        # Estimate tokens for next request (include max_tokens for response)
        # This is a conservative estimate to avoid rate limit errors
        estimated_next_request = self.max_tokens + 1000  # Add buffer for prompt tokens
        
        # Calculate available token capacity
        available_capacity = self.rate_limit_tokens - current_usage
        
        if available_capacity < estimated_next_request:
            # Need to wait for some tokens to free up from the window
            if self.token_usage_history:
                # Calculate time when oldest record will expire from window
                oldest_record_time = self.token_usage_history[0][0]
                # Calculate how much of the window needs to pass to free up enough tokens
                oldest_record_tokens = self.token_usage_history[0][1]
                
                # Calculate what portion of the window we need to wait for
                wait_fraction = (estimated_next_request - available_capacity) / oldest_record_tokens
                wait_time = max(0, (oldest_record_time + self.rate_limit_window) - current_time) * wait_fraction
                
                logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds to free up tokens. " 
                             f"Current usage: {current_usage}/{self.rate_limit_tokens} tokens")
                time.sleep(wait_time)
            else:
                # Should not happen, but just in case
                logger.warning("Rate limit calculation issue - no history but insufficient capacity")
                time.sleep(1)  # Small wait as a fallback
    
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
        
    def get_token_usage_stats(self) -> Dict:
        """
        Get statistics about the current token usage within the rate limit window.
        
        Returns:
            Dict containing token usage statistics
        """
        current_time = time.time()
        window_start = current_time - self.rate_limit_window
        
        # Clean up expired records
        while self.token_usage_history and self.token_usage_history[0][0] < window_start:
            self.token_usage_history.popleft()
            
        # Calculate current usage
        current_usage = sum(usage[1] for usage in self.token_usage_history)
        usage_percent = (current_usage / self.rate_limit_tokens) * 100 if self.rate_limit_tokens > 0 else 0
        
        # Calculate time until full capacity
        time_until_full_capacity = 0
        if self.token_usage_history and current_usage > 0:
            oldest_record_time = self.token_usage_history[0][0]
            time_until_full_capacity = max(0, (oldest_record_time + self.rate_limit_window) - current_time)
            
        return {
            "window_size_seconds": self.rate_limit_window,
            "token_limit": self.rate_limit_tokens,
            "current_usage": current_usage,
            "available_tokens": self.rate_limit_tokens - current_usage,
            "usage_percent": usage_percent,
            "request_count": len(self.token_usage_history),
            "time_until_full_capacity_seconds": time_until_full_capacity
        }



def load_context_from_file(context_file="llm.txt") -> str:
    """
    Load additional context from a file listing paths to include.
    
    Args:
        context_file: Path to file containing paths to include
        
    Returns:
        Compiled system message with included file contents
    """
    base_message = (
        "Below is relevant context for the task at hand. "
        "Please use this information to assist in the task. "
    )
    
    try:
        with open(context_file, "r", encoding="utf-8") as f:
            lines_to_include = f.readlines()
            
        lines_to_include = [x.strip() for x in lines_to_include]
        
        for line in lines_to_include:
            if os.path.isfile(line):
                try:
                    # Try UTF-8 first, which is most common
                    with open(line, "r", encoding="utf-8") as f:
                        base_message += f"\n{line} file:\n{f.read()}\n\n"
                except UnicodeDecodeError:
                    # Fall back to latin-1, which can decode any byte value
                    with open(line, "r", encoding="latin-1") as f:
                        base_message += f"\n{line} file:\n{f.read()}\n\n"
            elif os.path.isdir(line):
                base_message += f"\n{line} dir:\n{os.listdir(line)}\n\n"
            else:
                base_message += f"\n{line}\n"
    except Exception as e:
        logger.error(f"Error loading context from {context_file}: {str(e)}")
        
    return base_message


if __name__ == "__main__":
    # Initialize logging
    logger = cfg.setup_logging()
    logger.info("Application starting")
    
    # Load system message with additional context
    system_message = (
        "You are a helpful coding assistant. "
        "You are on a Windows machine. "
        "Make your tool calls with relative paths. "
    )
    
    # Initialize the Claude client with dynamic rate limiting
    client = ClaudeClient(
        system_message=system_message, 
        thinking_budget=2048, 
        text_editor=True,
        cooldown=3,  # Minimum delay between requests (seconds)
        rate_limit_tokens=20000,  # Anthropic's rate limit: 20k tokens per minute
        rate_limit_window=60  # Window size in seconds (1 minute)
    )
    logger.info("Claude client initialized with dynamic rate limiting")

    context = load_context_from_file("llm.txt")
    
    # Example initial prompt
    initial_prompt = (
        context +
        "Tell me what the most obvious high-impact optimizations can be made to claude_w_tools.py. "
        "Don't make any changes yet, just tell me what you would do. "
    )
    print("Initial prompt sent.")
    client.prompt(initial_prompt)
    
    # Main interaction loop
    while True:
        try:
            # Display token usage statistics
            usage_stats = client.get_token_usage_stats()
            usage_info = (
                f"\nToken usage: {usage_stats['current_usage']}/{usage_stats['token_limit']} "
                f"({usage_stats['usage_percent']:.1f}%)"
            )
            if usage_stats['time_until_full_capacity_seconds'] > 1:
                usage_info += f" - Full capacity in {usage_stats['time_until_full_capacity_seconds']:.1f}s"
            print(cfg.colors.info(usage_info))
            
            prompt_text = cfg.colors.user_prompt("\nPrompt: ")
            user_prompt = input(prompt_text)
            
            if user_prompt.lower() in ("exit", "quit"):
                logger.info("User requested exit")
                break
            elif user_prompt.lower() == "stats":
                # Detailed usage statistics
                stats = client.get_token_usage_stats()
                print(cfg.colors.info("\nDetailed Rate Limit Statistics:"))
                for key, value in stats.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:.2f}")
                    else:
                        print(f"  {key}: {value}")
                continue
            elif user_prompt.lower() == "clear":
                # Clear conversation history
                client.clear_conversation()
                print(cfg.colors.info("Conversation history cleared"))
                continue
                
            client.prompt(user_prompt)
            
        except KeyboardInterrupt:
            logger.info("User interrupted the application")
            break
        except anthropic.RateLimitError as e:
            logger.error(f"Rate limit error: {str(e)}")
            print(cfg.colors.error(f"Rate limit exceeded: {str(e)}"))
            print(cfg.colors.info("Waiting 10 seconds before continuing..."))
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error during prompt: {str(e)}")
            print(cfg.colors.error(f"An error occurred: {str(e)}"))
    
    logger.info("Application shutting down")
