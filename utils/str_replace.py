import os
import logging

# Get module-level logger
logger = logging.getLogger(__name__)

from utils.undo_edit import with_backup
from utils.verify_changes import verify_changes

@with_backup
def str_replace(file_path, old_str, new_str):
    """
    Safely replace text in a file with Claude-friendly error handling.
    
    Args:
        file_path (str): Path to the file to modify
        old_str (str): The string to be replaced (must match exactly, including whitespace and indentation)
        new_str (str): The new string to insert in place of the old text
                                      
    Returns:
        tuple: (content or message, error_occurred) - Returns the modified content or error message
    """
    logger.debug(f"str_replace called with path={file_path}, old_str_len={len(old_str)}, new_str_len={len(new_str)}")
    try:
        # Validate file path
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return f"Error: File '{file_path}' does not exist", True
            
        if not os.path.isfile(file_path):
            logger.warning(f"Path is not a file: {file_path}")
            return f"Error: '{file_path}' is not a file", True
            
        # Validate input parameters
        if old_str == '':
            logger.warning("Empty 'old_str' parameter")
            return "Error: 'old_str' cannot be empty", True
            
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            # Find all occurrences of the text
            matches = content.count(old_str)
            logger.debug(f"Found {matches} occurrences of the text to replace in {file_path}")
            
            # Handle no matches
            if matches == 0:
                logger.warning(f"No match found for replacement in {file_path}")
                return "Error: No match found for replacement. Please check your text and try again.", True
                
            # Handle multiple matches
            if matches > 1:
                logger.info(f"Multiple matches ({matches}) found in {file_path}, providing context")
                # For multiple matches, provide context for each match to help Claude
                match_info = []
                remaining_content = content
                position = 0
                
                # Find each match with its surrounding context (2 lines)
                for i in range(matches):
                    match_pos = remaining_content.find(old_str)
                    if match_pos == -1:
                        break
                        
                    abs_pos = position + match_pos
                    
                    # Find line number
                    line_number = content[:abs_pos].count('\n') + 1
                    
                    # Extract lines for context (2 lines before, 2 after)
                    # Find start of context
                    context_start = content.rfind('\n', 0, abs_pos)
                    for _ in range(2):
                        prev_newline = content.rfind('\n', 0, context_start)
                        if prev_newline == -1:
                            break
                        context_start = prev_newline
                    if context_start == -1:
                        context_start = 0
                    else:
                        context_start += 1  # Skip the newline
                        
                    # Find end of context
                    context_end = content.find('\n', abs_pos + len(old_str))
                    for _ in range(2):
                        next_newline = content.find('\n', context_end + 1)
                        if next_newline == -1:
                            break
                        context_end = next_newline
                    if context_end == -1:
                        context_end = len(content)
                        
                    # Get the context
                    context_text = content[context_start:context_end]
                    match_info.append(f"Match #{i+1} (line {line_number}):\n{context_text}")
                    
                    # Move position for next search
                    position = abs_pos + len(old_str)
                    remaining_content = content[position:]
                
                # Create detailed error message
                context_msg = "\n\n".join(match_info)
                return f"Error: Found {matches} matches for replacement text. Please provide more context to make a unique match.\n\n{context_msg}", True
            
            # Replace the text (only one match found)
            logger.info(f"Found single match in {file_path}, performing replacement")
            new_content = content.replace(old_str, new_str)
            
            # Write the modified content back to the file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logger.info(f"Successfully replaced text in {file_path}")
            except PermissionError:
                logger.error(f"Permission denied writing to file: {file_path}")
                return f"Error: Permission denied writing to file '{file_path}'", True
            except Exception as e:
                logger.error(f"Error writing to file {file_path}: {str(e)}")
                return f"Error writing to file '{file_path}': {str(e)}", True
                
            # Verify the file after replacement
            verification_msg, verification_error = verify_changes(file_path)
            
            # Append verification message to the content
            file_size = os.path.getsize(file_path)
            result_msg = f"Text replacement successful in '{file_path}' (size: {file_size} bytes).\n{verification_msg}\n\n{new_content}"
            return result_msg, verification_error
            
        except UnicodeDecodeError:
            return f"Error: File '{file_path}' contains binary or non-text content", True
        except PermissionError:
            return f"Error: Permission denied reading file '{file_path}'", True
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}", True
            
    except Exception as e:
        return f"Unexpected error in str_replace: {str(e)}", True