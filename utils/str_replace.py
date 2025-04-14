import os

from utils.undo_edit import with_backup

@with_backup
def str_replace(file_path, old_str, new_str):
    """
    Safely replace text in a file with Claude-friendly error handling.
    
    Args:
        file_path (str): Path to the file to modify
        old_str (str): The text to replace (must match exactly, including whitespace and indentation)
        new_str (str): The new text to insert in place of the old text
                                      
    Returns:
        tuple: (content or message, error_occurred)
    """
    try:
        # Validate file path
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist", True
            
        if not os.path.isfile(file_path):
            return f"Error: '{file_path}' is not a file", True
            
        # Validate input parameters
        if old_str == '':
            return "Error: 'old_str' cannot be empty", True
            
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                
            # Find all occurrences of the text
            matches = content.count(old_str)
            
            # Handle no matches
            if matches == 0:
                return "Error: No match found for replacement. Please check your text and try again.", True
                
            # Handle multiple matches
            if matches > 1:
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
            new_content = content.replace(old_str, new_str)
            
            # Write the modified content back to the file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
            except PermissionError:
                return f"Error: Permission denied writing to file '{file_path}'", True
            except Exception as e:
                return f"Error writing to file '{file_path}': {str(e)}", True
                
            # Return the new content
            return new_content, False
            
        except UnicodeDecodeError:
            return f"Error: File '{file_path}' contains binary or non-text content", True
        except PermissionError:
            return f"Error: Permission denied reading file '{file_path}'", True
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}", True
            
    except Exception as e:
        return f"Unexpected error in str_replace: {str(e)}", True