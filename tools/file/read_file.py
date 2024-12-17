from pathlib import Path
from langchain_core.tools import tool
@tool
def read_file(filepath: str) -> str:
    """Read content from a file."""
    try:
        path = Path(filepath)
        if not path.exists():
            return f"Error: File {filepath} does not exist"
            
        with open(filepath, 'r', encoding='utf-8') as f:
    except Exception as e:
        return f"Error reading file: {str(e)}"