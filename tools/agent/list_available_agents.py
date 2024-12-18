from typing import List
from langchain_core.tools import tool

def list_available_agents() -> List[str]:
    """List all available agents in the system."""
    return all_agents()