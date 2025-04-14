import os
import logging
from utils.verify_changes import verify_changes

# Get module-level logger
logger = logging.getLogger(__name__)

def create_file(file_path, file_text='', overwrite=False):
    """
    Safely create a new file with proper error handling.
    
    Args:
        file_path (str): Path to the file to create
        file_text (str): Content to write to the new file
        overwrite (bool): Whether to overwrite an existing file
        
    Returns:
        tuple: (result message, error_occurred)
    """
    logger.debug(f"create_file called with path={file_path}, overwrite={overwrite}")
    try:
        # Check if the file already exists
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                logger.warning(f"Cannot create file '{file_path}' - directory with that name exists")
                return f"Error: Cannot create file '{file_path}' because a directory with that name already exists", True
                
            if not overwrite:
                logger.info(f"File '{file_path}' already exists and overwrite=False")
                return f"Error: File '{file_path}' already exists. Set overwrite=True to replace it.", True
            else:
                logger.info(f"File '{file_path}' exists but will be overwritten")
        
        # Make sure the parent directory exists
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            logger.debug(f"Parent directory '{parent_dir}' doesn't exist, creating it")
            try:
                # Create parent directories recursively
                os.makedirs(parent_dir)
                logger.info(f"Created parent directory '{parent_dir}'")
            except PermissionError:
                logger.error(f"Permission denied creating directory '{parent_dir}'")
                return f"Error: Permission denied creating directory '{parent_dir}'", True
            except Exception as e:
                logger.error(f"Error creating directory '{parent_dir}': {str(e)}")
                return f"Error creating directory '{parent_dir}': {str(e)}", True
                
        # Write the content to the file
        try:
            logger.debug(f"Writing content to file '{file_path}'")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_text)
        except PermissionError:
            logger.error(f"Permission denied writing to file '{file_path}'")
            return f"Error: Permission denied writing to file '{file_path}'", True
        except IsADirectoryError:
            logger.error(f"'{file_path}' is a directory, not a file")
            return f"Error: '{file_path}' is a directory, not a file", True
        except Exception as e:
            logger.error(f"Error writing to file '{file_path}': {str(e)}")
            return f"Error writing to file '{file_path}': {str(e)}", True
            
        # Verify the file after creation
        verification_msg, verification_error = verify_changes(file_path)
        
        # Return success message with verification results
        action = "updated" if os.path.exists(file_path) and overwrite else "created"
        logger.info(f"File '{file_path}' {action} successfully")
        result_msg = f"File '{file_path}' {action} successfully.\n{verification_msg}"
        return result_msg, verification_error
        
    except Exception as e:
        logger.error(f"Unexpected error creating file '{file_path}': {str(e)}")
        return f"Unexpected error creating file '{file_path}': {str(e)}", True