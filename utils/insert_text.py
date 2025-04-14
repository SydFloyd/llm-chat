import os
import logging

from utils.undo_edit import with_backup

# Get module-level logger
logger = logging.getLogger(__name__)

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
    logger.debug(f"insert_text called with path={file_path}, insert_line={insert_line}, preserve_newline={preserve_newline}")
    try:
        # Validate file path
        if not os.path.exists(file_path):
            logger.warning(f"File '{file_path}' does not exist")
            return f"Error: File '{file_path}' does not exist", True
            
        if not os.path.isfile(file_path):
            logger.warning(f"Path '{file_path}' is not a file")
            return f"Error: '{file_path}' is not a file", True
            
        try:
            # Read the file content
            logger.debug(f"Reading file content from '{file_path}'")
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            logger.debug(f"File '{file_path}' read successfully, contains {len(lines)} lines")
                
            # Validate line number
            if insert_line < 0:
                logger.warning(f"Invalid insert_line={insert_line}, cannot be negative")
                return f"Error: Insert line number ({insert_line}) cannot be negative", True
                
            # Handle insert beyond file length
            if insert_line > len(lines):
                logger.info(f"Insert position {insert_line} is beyond file length {len(lines)}, adding empty lines")
                # Add empty lines if needed
                lines.extend([''] * (insert_line - len(lines)))
                
            # Add newline to the inserted text if it doesn't end with one and preserve_newline is True
            if preserve_newline and new_str and not new_str.endswith('\n'):
                logger.debug(f"Adding newline character to inserted text")
                new_str += '\n'
                
            # Handle special case: insert at beginning of file
            if insert_line == 0:
                logger.debug(f"Inserting text at beginning of file")
                lines.insert(0, new_str)
            else:
                # Insert after the specified line
                logger.debug(f"Inserting text after line {insert_line}")
                lines.insert(insert_line, new_str)
                
            # Write the modified content back to the file
            try:
                logger.debug(f"Writing modified content back to '{file_path}'")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
            except PermissionError:
                logger.error(f"Permission denied writing to file '{file_path}'")
                return f"Error: Permission denied writing to file '{file_path}'", True
            except Exception as e:
                logger.error(f"Error writing to file '{file_path}': {str(e)}")
                return f"Error writing to file '{file_path}': {str(e)}", True
                
            # Return success message with file line info
            total_lines = len(lines)
            if insert_line == 0:
                position = "beginning of file"
            else:
                position = f"after line {insert_line}"
                
            logger.info(f"Text inserted at {position} in '{file_path}' (now {total_lines} lines total)")
            return f"Text inserted at {position} in '{file_path}' (now {total_lines} lines total).", False
            
        except UnicodeDecodeError:
            logger.error(f"File '{file_path}' contains binary or non-text content")
            return f"Error: File '{file_path}' contains binary or non-text content", True
        except PermissionError:
            logger.error(f"Permission denied reading file '{file_path}'")
            return f"Error: Permission denied reading file '{file_path}'", True
        except Exception as e:
            logger.error(f"Error reading file '{file_path}': {str(e)}")
            return f"Error reading file '{file_path}': {str(e)}", True
            
    except Exception as e:
        logger.error(f"Unexpected error in insert_text: {str(e)}")
        return f"Unexpected error in insert_text: {str(e)}", True