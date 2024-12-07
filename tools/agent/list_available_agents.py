from typing import List
from utils import all_agents

@tool
def list_available_agents() -> List[str]:
    """List all available agents in the system."""
    return all_agents()