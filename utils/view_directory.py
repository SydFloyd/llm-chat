import os
import datetime
import logging

# Get module-level logger
logger = logging.getLogger(__name__)

def view_directory(dir_path, show_details=False):
    """
    Get formatted directory listing with optional file details.
    
    Args:
        dir_path (str): Path to the directory to list
        show_details (bool): Whether to show additional file details
        
    Returns:
        tuple: (content, error_occurred)
    """
    logger.debug(f"view_directory called with path={dir_path}, show_details={show_details}")
    try:
        # Check if path exists and is a directory
        if not os.path.exists(dir_path):
            logger.warning(f"Directory not found: {dir_path}")
            return f"Error: Path '{dir_path}' does not exist", True
            
        if not os.path.isdir(dir_path):
            logger.warning(f"Path is not a directory: {dir_path}")
            return f"Error: '{dir_path}' is not a directory", True
            
        try:
            # Get sorted directory listing
            entries = sorted(os.listdir(dir_path))
            
            # Handle empty directory
            if not entries:
                return f"{dir_path} (empty directory)", False
                
            if show_details:
                # Show detailed view with file sizes, types, and modification times
                formatted_entries = []
                for entry in entries:
                    full_path = os.path.join(dir_path, entry)
                    try:
                        # Get file stats
                        stats = os.stat(full_path)
                        size = stats.st_size
                        mod_time = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Determine type
                        if os.path.isdir(full_path):
                            entry_type = "directory"
                            size_str = f"{len(os.listdir(full_path))} items"
                        elif os.path.islink(full_path):
                            entry_type = "symlink"
                            size_str = f"{size} bytes"
                        else:
                            entry_type = "file"
                            # Format size appropriately
                            if size < 1024:
                                size_str = f"{size} bytes"
                            elif size < 1024 * 1024:
                                size_str = f"{size/1024:.1f} KB"
                            elif size < 1024 * 1024 * 1024:
                                size_str = f"{size/(1024*1024):.1f} MB"
                            else:
                                size_str = f"{size/(1024*1024*1024):.1f} GB"
                        
                        formatted_entries.append(f"- {entry} ({entry_type}, {size_str}, modified: {mod_time})")
                    except (FileNotFoundError, PermissionError):
                        # Handle case where file might be deleted between listdir and stat
                        formatted_entries.append(f"- {entry} (inaccessible)")
                files_formatted = "\n".join(formatted_entries)
            else:
                # Simple view, just names with type indicators
                formatted_entries = []
                for entry in entries:
                    full_path = os.path.join(dir_path, entry)
                    try:
                        if os.path.isdir(full_path):
                            formatted_entries.append(f"- {entry}/ (dir)")
                        elif os.path.islink(full_path):
                            formatted_entries.append(f"- {entry} (link)")
                        else:
                            formatted_entries.append(f"- {entry}")
                    except (FileNotFoundError, PermissionError):
                        formatted_entries.append(f"- {entry} (inaccessible)")
                files_formatted = "\n".join(formatted_entries)
            
            # Get and show directory info
            total_entries = len(entries)
            try:
                dir_size = sum(os.path.getsize(os.path.join(dir_path, f)) for f in entries if os.path.isfile(os.path.join(dir_path, f)))
                if dir_size < 1024:
                    dir_size_str = f"{dir_size} bytes"
                elif dir_size < 1024 * 1024:
                    dir_size_str = f"{dir_size/1024:.1f} KB"
                elif dir_size < 1024 * 1024 * 1024:
                    dir_size_str = f"{dir_size/(1024*1024):.1f} MB"
                else:
                    dir_size_str = f"{dir_size/(1024*1024*1024):.1f} GB"
                header = f"{dir_path} ({total_entries} items, {dir_size_str} total):"
            except:
                # Fallback if size calculation fails
                header = f"{dir_path} ({total_entries} items):"
            
            logger.debug(f"Successfully listed directory {dir_path} ({total_entries} items)")
            return f"{header}\n{files_formatted}", False
            
        except PermissionError:
            logger.error(f"Permission denied accessing directory: {dir_path}")
            return f"Error: Permission denied accessing directory '{dir_path}'", True
        except Exception as e:
            logger.error(f"Error listing directory {dir_path}: {str(e)}")
            return f"Error listing directory '{dir_path}': {str(e)}", True
            
    except Exception as e:
        logger.error(f"Unexpected error processing directory {dir_path}: {str(e)}")
        return f"Unexpected error processing directory '{dir_path}': {str(e)}", True