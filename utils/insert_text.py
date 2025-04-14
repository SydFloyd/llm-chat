import os

from utils.undo_edit import with_backup

@with_backup
def insert_text(file_path, new_str, insert_line=0, preserve_newline=True):
    """
    Safely insert text at a specific line in a file.
    
    Args:
        file_path (str): Path to the file
        new_str (str): The text to insert
        insert_line (int): The line number after which to insert the text (0 for beginning of file)
        preserve_newline (bool): Whether to add a newline character if not present
        
    Returns:
        tuple: (result message, error_occurred)
    """
    try:
        # Validate file path
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist", True
            
        if not os.path.isfile(file_path):
            return f"Error: '{file_path}' is not a file", True
            
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                
            # Validate line number
            if insert_line < 0:
                return f"Error: Insert line number ({insert_line}) cannot be negative", True
                
            # Handle insert beyond file length
            if insert_line > len(lines):
                # Add empty lines if needed
                lines.extend([''] * (insert_line - len(lines)))
                
            # Add newline to the inserted text if it doesn't end with one and preserve_newline is True
            if preserve_newline and new_str and not new_str.endswith('\n'):
                new_str += '\n'
                
            # Handle special case: insert at beginning of file
            if insert_line == 0:
                lines.insert(0, new_str)
            else:
                # Insert after the specified line
                lines.insert(insert_line, new_str)
                
            # Write the modified content back to the file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            except PermissionError:
                return f"Error: Permission denied writing to file '{file_path}'", True
            except Exception as e:
                return f"Error writing to file '{file_path}': {str(e)}", True
                
            # Return success message with file line info
            total_lines = len(lines)
            if insert_line == 0:
                position = "beginning of file"
            else:
                position = f"after line {insert_line}"
                
            return f"Text inserted at {position} in '{file_path}' (now {total_lines} lines total).", False
            
        except UnicodeDecodeError:
            return f"Error: File '{file_path}' contains binary or non-text content", True
        except PermissionError:
            return f"Error: Permission denied reading file '{file_path}'", True
        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}", True
            
    except Exception as e:
        return f"Unexpected error in insert_text: {str(e)}", True