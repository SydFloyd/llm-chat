import os

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
    try:
        # Check if the file already exists
        if os.path.exists(file_path):
            if os.path.isdir(file_path):
                return f"Error: Cannot create file '{file_path}' because a directory with that name already exists", True
                
            if not overwrite:
                return f"Error: File '{file_path}' already exists. Set overwrite=True to replace it.", True
        
        # Make sure the parent directory exists
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            try:
                # Create parent directories recursively
                os.makedirs(parent_dir)
            except PermissionError:
                return f"Error: Permission denied creating directory '{parent_dir}'", True
            except Exception as e:
                return f"Error creating directory '{parent_dir}': {str(e)}", True
                
        # Write the content to the file
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_text)
        except PermissionError:
            return f"Error: Permission denied writing to file '{file_path}'", True
        except IsADirectoryError:
            return f"Error: '{file_path}' is a directory, not a file", True
        except Exception as e:
            return f"Error writing to file '{file_path}': {str(e)}", True
            
        # Return success message
        action = "updated" if os.path.exists(file_path) and overwrite else "created"
        return f"File '{file_path}' {action} successfully.", False
        
    except Exception as e:
        return f"Unexpected error creating file '{file_path}': {str(e)}", True