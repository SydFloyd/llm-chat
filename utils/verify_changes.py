import os
import logging

# Get module-level logger
logger = logging.getLogger(__name__)

def verify_changes(file_path):
    """
    Verify changes made to a file and provide feedback.
    
    Args:
        file_path (str): Path to the file to verify
        
    Returns:
        tuple: (verification message, has_errors)
    """
    logger.debug(f"Verifying changes to file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.warning(f"Verification failed: File '{file_path}' does not exist")
        return f"Verification failed: File '{file_path}' does not exist", True
        
    if not os.path.isfile(file_path):
        logger.warning(f"Verification failed: '{file_path}' is not a file")
        return f"Verification failed: '{file_path}' is not a file", True
    
    try:
        # Get file stats
        file_size = os.path.getsize(file_path)
        file_type = file_path.split('.')[-1] if '.' in file_path else 'Unknown'
        
        # For Python files, check syntax
        if file_path.endswith('.py'):
            import ast
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                ast.parse(file_content)
                logger.info(f"Python syntax check passed for '{file_path}'")
                return f"Verification successful: Python syntax check passed. File size: {file_size} bytes.", False
            except SyntaxError as e:
                logger.warning(f"Python syntax error in '{file_path}': {str(e)}")
                return f"Verification warning: Python syntax error at line {e.lineno}, column {e.offset}: {e.msg}", True
            except Exception as e:
                logger.error(f"Error parsing Python file '{file_path}': {str(e)}")
                return f"Verification failed: Error parsing Python file: {str(e)}", True
                
        # For JSON files, check JSON syntax
        elif file_path.endswith('.json'):
            import json
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                logger.info(f"JSON syntax check passed for '{file_path}'")
                return f"Verification successful: JSON syntax check passed. File size: {file_size} bytes.", False
            except json.JSONDecodeError as e:
                logger.warning(f"JSON syntax error in '{file_path}': {str(e)}")
                return f"Verification warning: JSON syntax error at line {e.lineno}, column {e.colno}: {e.msg}", True
            except Exception as e:
                logger.error(f"Error parsing JSON file '{file_path}': {str(e)}")
                return f"Verification failed: Error parsing JSON file: {str(e)}", True
                
        # For HTML files, do a basic check
        elif file_path.endswith(('.html', '.htm')):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                # Basic check for HTML tags balance
                if content.count('<') != content.count('>'):
                    logger.warning(f"HTML tags might be unbalanced in '{file_path}'")
                    return f"Verification warning: HTML tags might be unbalanced (found {content.count('<')} opening tags and {content.count('>')} closing tags). File size: {file_size} bytes.", True
                logger.info(f"Basic HTML check passed for '{file_path}'")
                return f"Verification successful: Basic HTML check passed. File size: {file_size} bytes.", False
            except Exception as e:
                logger.error(f"Error checking HTML file '{file_path}': {str(e)}")
                return f"Verification failed: Error checking HTML file: {str(e)}", True
                
        # For other file types, just verify it's readable
        else:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    lines = f.readlines()
                line_count = len(lines)
                logger.info(f"File '{file_path}' is readable, contains {line_count} lines")
                return f"Verification successful: File is readable. Contains {line_count} lines, size: {file_size} bytes.", False
            except Exception as e:
                logger.error(f"Error reading file '{file_path}': {str(e)}")
                return f"Verification note: File exists but may not be readable as text: {str(e)}", False
    
    except Exception as e:
        logger.error(f"Unexpected error verifying '{file_path}': {str(e)}")
        return f"Verification failed: Unexpected error: {str(e)}", True