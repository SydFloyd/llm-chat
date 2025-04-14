import os

def view_file(file_path, view_range=None):
    """
    Safely read a file or list directory contents.
    
    Args:
        file_path (str): Path to file or directory to view
        view_range (list, optional): Two integers [start, end] specifying line range to view (1-indexed)
                                    where -1 for end means read to the end of file
    
    Returns:
        tuple: (content, error_occurred)
    """
    try:
        # Validate file path exists
        if not os.path.exists(file_path):
            return f"Error: Path '{file_path}' does not exist", True
            
        # Handle directory listing
        if os.path.isdir(file_path):
            try:
                files = os.listdir(file_path)
                files_formatted = "\n".join([f"- {file}" for file in files])
                return f"{file_path}:\n{files_formatted}", False
            except PermissionError:
                return f"Error: Permission denied accessing directory '{file_path}'", True
            except Exception as e:
                return f"Error listing directory '{file_path}': {str(e)}", True
                
        # Handle file reading
        elif os.path.isfile(file_path):
            # Set default view range if not provided
            if view_range is None:
                view_range = [1, -1]  # Default to entire file
                
            # Validate view_range parameter
            if not isinstance(view_range, list) or len(view_range) != 2:
                return f"Error: view_range must be a list of two integers", True
                
            try:
                start, end = map(int, view_range)
            except (ValueError, TypeError):
                return f"Error: view_range values must be integers", True
                
            # Convert from 1-indexed to 0-indexed
            start = max(0, start - 1)  # Ensure start is at least 0
            
            try:
                # Use context manager for proper file handling
                with open(file_path, 'r', errors='replace') as f:
                    # Read line by line to handle large files more efficiently
                    if end == -1:
                        # Reading to the end of the file
                        lines = f.readlines()
                    else:
                        # Reading specific range
                        lines = []
                        for i, line in enumerate(f):
                            if i < start:
                                continue
                            if end != -1 and i >= end:
                                break
                            lines.append(line)
                
                # Join lines and return
                return "".join(lines), False
                
            except PermissionError:
                return f"Error: Permission denied reading file '{file_path}'", True
            except UnicodeDecodeError:
                return f"Error: File '{file_path}' contains non-text content or uses unsupported encoding", True
            except Exception as e:
                return f"Error reading file '{file_path}': {str(e)}", True
        else:
            return f"Error: '{file_path}' is neither a file nor a directory", True
            
    except Exception as e:
        return f"Unexpected error processing '{file_path}': {str(e)}", True
