
@tool
def overwrite_file(filepath: str, content: str) -> str:
    """Overwrite content in an existing file."""
    try:
        if not path.exists():
            return f"Error: File {filepath} does not exist"
            
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully overwrote {filepath}"
    except Exception as e:
