import os

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
    # Normalize path for consistent matching
    normalized_path = os.path.normpath(file_path).replace('\\', '/')
    
    # Check against exclusion patterns
    for pattern in BACKUP_EXCLUDE_PATTERNS:
        if pattern.endswith('/'):  # Directory pattern
            if pattern[:-1] in normalized_path.split('/'):
                return False
        elif '*' in pattern:  # Wildcard pattern
            import fnmatch
            if fnmatch.fnmatch(os.path.basename(normalized_path), pattern):
                return False
        elif pattern in normalized_path:  # Simple substring match
            return False
            
    return True

def backup_file(file_path):
    """
    Create a backup of a file before editing.
    
    Args:
        file_path (str): Path to the file to backup
        
    Returns:
        tuple: (backup_path or None, success)
    """
    # Check if file should be backed up
    if not should_backup_file(file_path):
        return None, True
        
    # Check if file exists
    if not os.path.exists(file_path):
        return None, True  # Nothing to backup
        
    if not os.path.isfile(file_path):
        return None, False  # Not a file
        
    # Create backup path
    backup_path = f"{file_path}.backup"
    
    try:
        # Copy the file
        with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        return backup_path, True
    except Exception as e:
        print(f"Backup error for {file_path}: {str(e)}")
        return None, False

def undo_edit(file_path):
    """
    Restore a file from its backup.
    
    Args:
        file_path (str): Path to the file to restore
        
    Returns:
        tuple: (result message, error_occurred)
    """
    try:
        # Check if original file exists
        if not os.path.exists(file_path):
            return f"Error: File '{file_path}' does not exist", True
            
        # Check if backup exists
        backup_path = f"{file_path}.backup"
        if not os.path.exists(backup_path):
            return f"Error: No backup found for '{file_path}'", True
            
        try:
            # Restore from backup
            with open(backup_path, 'rb') as src, open(file_path, 'wb') as dst:
                dst.write(src.read())
                
            # Return success message
            return f"File '{file_path}' successfully restored from backup.", False
            
        except PermissionError:
            return f"Error: Permission denied accessing file '{file_path}' or its backup", True
        except Exception as e:
            return f"Error restoring file from backup: {str(e)}", True
            
    except Exception as e:
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
    if file_path not in backup_registry:
        backup_path, success = backup_file(file_path)
        if success and backup_path:
            backup_registry[file_path] = backup_path
            return True
    return False

# Updates to command handlers to use backup system

# Wrapper function for commands that modify files
def with_backup(func):
    """Decorator to automatically backup files before modification"""
    def wrapper(file_path, *args, **kwargs):
        register_for_backup(file_path)
        return func(file_path, *args, **kwargs)
    return wrapper