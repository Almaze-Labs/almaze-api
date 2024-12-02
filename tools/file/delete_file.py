from pathlib import Path
from langchain_core.tools import tool

@tool
def delete_file(filepath: str) -> str:
    """Delete a file."""
    try:
        path = Path(filepath)
        if not path.exists():
            return f"Error: File {filepath} does not exist"
            
        path.unlink()
        return f"Successfully deleted {filepath}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"