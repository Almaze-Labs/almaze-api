from langchain_core.tools import tool

@tool
def delete_file(filepath: str) -> str:
    """Delete a file."""
        path = Path(filepath)
            return f"Error: File {filepath} does not exist"
            
        path.unlink()
        return f"Successfully deleted {filepath}"
        return f"Error deleting file: {str(e)}"