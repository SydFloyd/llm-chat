import os
import logging

# Get module-level logger
logger = logging.getLogger(__name__)

# File locations to exclude from backup (add more as needed)
BACKUP_EXCLUDE_PATTERNS = [
    '.venv/', 
    '__pycache__/',
    'node_modules/',
    '.git/',
    '.pytest_cache/',
    '.mypy_cache/',
    '*.pyc',
    '*.pyo',
    '*.pyd',
    '*.so',
    '*.dll',
    '*.backup'  # Don't backup backup files
]

def should_backup_file(file_path):
    """
    Determine if a file should be backed up based on exclusion patterns.
    
    Args:
        file_path (str): Path to check
        
    Returns:
        bool: True if the file should be backed up, False otherwise
    """
    logger.debug(f"Checking if file '{file_path}' should be backed up")
    
    # Normalize path for consistent matching
    normalized_path = os.path.normpath(file_path).replace('\\', '/')
    
    # Check against exclusion patterns
    for pattern in BACKUP_EXCLUDE_PATTERNS:
        if pattern.endswith('/'):  # Directory pattern
            if pattern[:-1] in normalized_path.split('/'):
                logger.debug(f"File '{file_path}' matches directory exclusion pattern '{pattern}', skipping backup")
                return False
        elif '*' in pattern:  # Wildcard pattern
            import fnmatch
            if fnmatch.fnmatch(os.path.basename(normalized_path), pattern):
                logger.debug(f"File '{file_path}' matches wildcard exclusion pattern '{pattern}', skipping backup")
                return False
        elif pattern in normalized_path:  # Simple substring match
            logger.debug(f"File '{file_path}' matches substring exclusion pattern '{pattern}', skipping backup")
            return False
    
    logger.debug(f"File '{file_path}' will be backed up")
    return True

def backup_file(file_path):
    """
    Create a backup of a file before editing.
    
    Args:
        file_path (str): Path to the file to backup
        
    Returns:
        tuple: (backup_path or None, success)
    """
    logger.debug(f"backup_file called for '{file_path}'")
    
    # Check if file should be backed up
    if not should_backup_file(file_path):
        logger.info(f"File '{file_path}' excluded from backup")
        return None, True
        
    # Check if file exists
    if not os.path.exists(file_path):
        logger.warning(f"File '{file_path}' doesn't exist, no backup needed")
        return None, True  # Nothing to backup
        
    if not os.path.isfile(file_path):
        logger.warning(f"'{file_path}' is not a file, cannot backup")
        return None, False  # Not a file
        
    # Create backup path
    backup_path = f"{file_path}.backup"
    logger.debug(f"Creating backup at '{backup_path}'")
    
    try:
        # Copy the file
        with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        logger.info(f"Successfully created backup of '{file_path}' to '{backup_path}'")
        return backup_path, True
    except Exception as e:
        logger.error(f"Backup error for '{file_path}': {str(e)}")
        return None, False

def undo_edit(file_path):
    """
    Restore a file from its backup.
    
    Args:
        file_path (str): Path to the file to restore
        
    Returns:
        tuple: (result message, error_occurred)
    """
    logger.debug(f"undo_edit called for '{file_path}'")
    
    try:
        # Check if original file exists
        if not os.path.exists(file_path):
            logger.warning(f"File '{file_path}' does not exist, cannot restore")
            return f"Error: File '{file_path}' does not exist", True
            
        # Check if backup exists
        backup_path = f"{file_path}.backup"
        if not os.path.exists(backup_path):
            logger.warning(f"No backup found for '{file_path}'")
            return f"Error: No backup found for '{file_path}'", True
            
        try:
            # Restore from backup
            logger.debug(f"Restoring '{file_path}' from backup '{backup_path}'")
            with open(backup_path, 'rb') as src, open(file_path, 'wb') as dst:
                dst.write(src.read())
                
            # Return success message
            logger.info(f"File '{file_path}' successfully restored from backup")
            return f"File '{file_path}' successfully restored from backup.", False
            
        except PermissionError:
            logger.error(f"Permission denied accessing file '{file_path}' or its backup")
            return f"Error: Permission denied accessing file '{file_path}' or its backup", True
        except Exception as e:
            logger.error(f"Error restoring file from backup: {str(e)}")
            return f"Error restoring file from backup: {str(e)}", True
            
    except Exception as e:
        logger.error(f"Unexpected error in undo_edit: {str(e)}")
        return f"Unexpected error in undo_edit: {str(e)}", True

# Backup tracking for multiple edits
# This stores the original backup for a file so multiple edits can be undone to the original state
backup_registry = {}

def register_for_backup(file_path):
    """
    Register a file for backup if not already backed up in this session.
    
    Args:
        file_path (str): Path to the file to register
        
    Returns:
        bool: True if backup was created, False otherwise
    """
    logger.debug(f"register_for_backup called for '{file_path}'")
    
    if file_path not in backup_registry:
        logger.debug(f"File '{file_path}' not in backup registry, creating backup")
        backup_path, success = backup_file(file_path)
        if success and backup_path:
            backup_registry[file_path] = backup_path
            logger.info(f"File '{file_path}' registered in backup registry")
            return True
        else:
            logger.warning(f"Failed to register '{file_path}' in backup registry")
    else:
        logger.debug(f"File '{file_path}' already in backup registry, skipping backup")
    
    return False

# Updates to command handlers to use backup system

# Wrapper function for commands that modify files
def with_backup(func):
    """Decorator to automatically backup files before modification"""
    def wrapper(file_path, *args, **kwargs):
        logger.debug(f"with_backup decorator called for function '{func.__name__}' on file '{file_path}'")
        register_for_backup(file_path)
        return func(file_path, *args, **kwargs)
    return wrapper