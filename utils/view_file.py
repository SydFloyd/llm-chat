import os
import logging

# Get module-level logger
logger = logging.getLogger(__name__)

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
    logger.debug(f"view_file called with path={file_path}, view_range={view_range}")
    try:
        # Validate file path exists
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            return f"Error: Path '{file_path}' does not exist", True
            
        # Handle directory listing
        if os.path.isdir(file_path):
            logger.debug(f"Listing directory: {file_path}")
            try:
                files = os.listdir(file_path)
                files_formatted = "\n".join([f"- {file}" for file in files])
                logger.debug(f"Successfully listed directory with {len(files)} files")
                return f"{file_path}:\n{files_formatted}", False
            except PermissionError:
                logger.error(f"Permission denied accessing directory: {file_path}")
                return f"Error: Permission denied accessing directory '{file_path}'", True
            except Exception as e:
                logger.error(f"Error listing directory {file_path}: {str(e)}")
                return f"Error listing directory '{file_path}': {str(e)}", True
                
        # Handle file reading
        elif os.path.isfile(file_path):
            logger.debug(f"Reading file: {file_path}")
            # Set default view range if not provided
            if view_range is None:
                view_range = [1, -1]  # Default to entire file
                logger.debug("Using default view range [1, -1] (entire file)")
                
            # Validate view_range parameter
            if not isinstance(view_range, list) or len(view_range) != 2:
                logger.warning(f"Invalid view_range parameter: {view_range}")
                return f"Error: view_range must be a list of two integers", True
                
            try:
                start, end = map(int, view_range)
                logger.debug(f"Parsed view range: start={start}, end={end}")
            except (ValueError, TypeError):
                logger.warning(f"Invalid view_range values (not integers): {view_range}")
                return f"Error: view_range values must be integers", True
                
            # Convert from 1-indexed to 0-indexed
            start = max(0, start - 1)  # Ensure start is at least 0
            logger.debug(f"Adjusted 0-indexed start line: {start}")
            
            try:
                # Use context manager for proper file handling
                logger.debug(f"Opening file: {file_path}")
                with open(file_path, 'r', errors='replace') as f:
                    # Read line by line to handle large files more efficiently
                    if end == -1:
                        # Reading to the end of the file
                        logger.debug(f"Reading entire file from line {start+1}")
                        lines = f.readlines()
                    else:
                        # Reading specific range
                        logger.debug(f"Reading lines {start+1} to {end}")
                        lines = []
                        for i, line in enumerate(f):
                            if i < start:
                                continue
                            if end != -1 and i >= end:
                                break
                            lines.append(line)
                
                # Join lines and return
                content_length = len("".join(lines))
                logger.debug(f"Successfully read {len(lines)} lines ({content_length} bytes) from {file_path}")
                return "".join(lines), False
                
            except PermissionError:
                logger.error(f"Permission denied reading file: {file_path}")
                return f"Error: Permission denied reading file '{file_path}'", True
            except UnicodeDecodeError:
                logger.error(f"File contains non-text content or uses unsupported encoding: {file_path}")
                return f"Error: File '{file_path}' contains non-text content or uses unsupported encoding", True
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
                return f"Error reading file '{file_path}': {str(e)}", True
        else:
            logger.warning(f"Path is neither a file nor a directory: {file_path}")
            return f"Error: '{file_path}' is neither a file nor a directory", True
            
    except Exception as e:
        logger.error(f"Unexpected error processing '{file_path}': {str(e)}")
        return f"Unexpected error processing '{file_path}': {str(e)}", True
