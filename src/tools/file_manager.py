"""
File Manager Tool - Secure file operations within the sandbox directory.
This module provides tools for agents to safely read and write files.

SECURITY: All operations are restricted to the sandbox directory.
"""
import os
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Import configuration
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.config import SANDBOX_DIR


class SecurityException(Exception):
    """Raised when an operation attempts to escape the sandbox."""
    pass


def _validate_path(file_path: str) -> Path:
    """
    Validate that a path is within the sandbox directory.
    
    Args:
        file_path: Path to validate (relative or absolute)
        
    Returns:
        Absolute Path object within sandbox
        
    Raises:
        SecurityException: If path is outside sandbox
    """
    # Convert to Path object
    if isinstance(file_path, str):
        path = Path(file_path)
    else:
        path = file_path
    
    # Make absolute relative to sandbox if not already absolute
    if not path.is_absolute():
        path = SANDBOX_DIR / path
    
    # Resolve to handle .. and symlinks
    try:
        resolved_path = path.resolve()
        sandbox_resolved = SANDBOX_DIR.resolve()
        
        # Check if the resolved path is within sandbox
        if not str(resolved_path).startswith(str(sandbox_resolved)):
            raise SecurityException(
                f"🚨 SECURITY VIOLATION: Attempted to access path outside sandbox!\n"
                f"   Requested: {file_path}\n"
                f"   Resolved to: {resolved_path}\n"
                f"   Sandbox: {sandbox_resolved}"
            )
        
        return resolved_path
    except Exception as e:
        raise SecurityException(f"Path validation failed for {file_path}: {str(e)}")


def read_file(file_path: str) -> str:
    """
    Safely read a file from the sandbox directory.
    
    Args:
        file_path: Path to file (relative to sandbox or absolute within sandbox)
        
    Returns:
        File contents as string
        
    Raises:
        SecurityException: If path is outside sandbox
        FileNotFoundError: If file doesn't exist
    """
    validated_path = _validate_path(file_path)
    
    if not validated_path.exists():
        raise FileNotFoundError(f"File not found: {file_path} (resolved to {validated_path})")
    
    if not validated_path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    
    try:
        with open(validated_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except UnicodeDecodeError:
        # Try with latin-1 as fallback
        with open(validated_path, 'r', encoding='latin-1') as f:
            content = f.read()
        return content


def write_file(file_path: str, content: str) -> bool:
    """
    Safely write content to a file in the sandbox directory.
    Creates parent directories if needed.
    
    Args:
        file_path: Path to file (relative to sandbox or absolute within sandbox)
        content: Content to write
        
    Returns:
        True if successful
        
    Raises:
        SecurityException: If path is outside sandbox
    """
    validated_path = _validate_path(file_path)
    
    # Create parent directories if they don't exist
    validated_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(validated_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        raise IOError(f"Failed to write file {file_path}: {str(e)}")


def list_python_files(directory: str = ".") -> List[str]:
    """
    List all Python files in a directory within the sandbox.
    
    Args:
        directory: Directory to search (relative to sandbox, default is sandbox root)
        
    Returns:
        List of Python file paths relative to sandbox
        
    Raises:
        SecurityException: If path is outside sandbox
    """
    validated_path = _validate_path(directory)
    
    if not validated_path.exists():
        return []
    
    if not validated_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")
    
    python_files = []
    for root, dirs, files in os.walk(validated_path):
        # Skip __pycache__ and hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                full_path = Path(root) / file
                # Get path relative to sandbox
                relative_path = full_path.relative_to(SANDBOX_DIR)
                python_files.append(str(relative_path))
    
    return sorted(python_files)


def get_file_info(file_path: str) -> Dict[str, any]:
    """
    Get metadata about a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dictionary with file metadata (size, lines, exists, etc.)
    """
    try:
        validated_path = _validate_path(file_path)
        
        if not validated_path.exists():
            return {
                "exists": False,
                "path": str(file_path)
            }
        
        # Count lines if it's a text file
        line_count = 0
        try:
            content = read_file(file_path)
            line_count = len(content.splitlines())
        except:
            line_count = -1  # Binary or unreadable file
        
        return {
            "exists": True,
            "path": str(file_path),
            "absolute_path": str(validated_path),
            "size_bytes": validated_path.stat().st_size,
            "line_count": line_count,
            "is_python": str(file_path).endswith('.py')
        }
    except SecurityException:
        raise
    except Exception as e:
        return {
            "exists": False,
            "path": str(file_path),
            "error": str(e)
        }


def delete_file(file_path: str) -> bool:
    """
    Safely delete a file from the sandbox.
    
    Args:
        file_path: Path to file
        
    Returns:
        True if deleted, False if file didn't exist
        
    Raises:
        SecurityException: If path is outside sandbox
    """
    validated_path = _validate_path(file_path)
    
    if not validated_path.exists():
        return False
    
    if validated_path.is_file():
        validated_path.unlink()
        return True
    else:
        raise ValueError(f"Path is not a file: {file_path}")


# ===== Convenience functions for common operations =====

def copy_directory_to_sandbox(source_dir: str, target_subdir: str = ".") -> List[str]:
    """
    Copy an entire directory into the sandbox for processing.
    
    Args:
        source_dir: Source directory path (can be outside sandbox)
        target_subdir: Target subdirectory within sandbox
        
    Returns:
        List of copied file paths (relative to sandbox)
    """
    import shutil
    
    source_path = Path(source_dir).resolve()
    if not source_path.exists() or not source_path.is_dir():
        raise ValueError(f"Source directory does not exist: {source_dir}")
    
    # Validate target is within sandbox
    target_path = _validate_path(target_subdir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    copied_files = []
    
    # Copy all files
    for item in source_path.rglob('*'):
        if item.is_file():
            # Calculate relative path from source
            rel_path = item.relative_to(source_path)
            target_file = target_path / rel_path
            
            # Create parent directory
            target_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file
            shutil.copy2(item, target_file)
            
            # Add to list (relative to sandbox)
            copied_files.append(str(target_file.relative_to(SANDBOX_DIR)))
    
    return copied_files


if __name__ == "__main__":
    # Quick test
    print("🧪 Testing File Manager...")
    print(f"Sandbox directory: {SANDBOX_DIR}")
    
    # Test write
    test_content = "# Test file\nprint('Hello from sandbox!')\n"
    write_file("test_file.py", test_content)
    print("✅ Write test passed")
    
    # Test read
    read_content = read_file("test_file.py")
    assert read_content == test_content
    print("✅ Read test passed")
    
    # Test list
    files = list_python_files()
    assert "test_file.py" in files
    print(f"✅ List test passed: {files}")
    
    # Test security (should fail)
    try:
        read_file("../../etc/passwd")
        print("❌ Security test FAILED - should have blocked!")
    except SecurityException:
        print("✅ Security test passed - blocked unauthorized access")
    
    # Cleanup
    delete_file("test_file.py")
    print("✅ Delete test passed")
    
    print("\n🎉 All file manager tests passed!")