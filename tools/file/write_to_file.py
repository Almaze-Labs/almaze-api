import os
from pathlib import Path
from langchain_core.tools import tool
@tool
def write_to_file(filepath: str, content: str) -> str:
    """Write content to a file, creating directories if they don't exist."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return f"Successfully wrote content to {filepath}"
        return f"Error writing to file: {str(e)}"