import os
import importlib
import inspect
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_logging(log_level: str = 'INFO') -> None:
    """Configure logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {log_level}')
    logging.getLogger().setLevel(numeric_level)

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent

def load_module_functions(directory: str, module_type: str) -> List[Any]:
    """Load all functions from modules in a directory."""
    functions = []
    dir_path = get_project_root() / directory
    
    for item in os.listdir(dir_path):
        if os.path.isdir(dir_path / item) and not item.startswith('__'):
            # Handle subdirectories
            for file in os.listdir(dir_path / item):
                if file.endswith('.py') and not file.startswith('__'):
                    module_name = f"{directory}.{item}.{file[:-3]}"
                    for name, obj in inspect.getmembers(module):
                        if inspect.isfunction(obj) and hasattr(obj, f"_{module_type}"):
                            functions.append(obj)
        elif item.endswith('.py') and not item.startswith('__'):
            # Handle files in the root of the directory
            module_name = f"{directory}.{item[:-3]}"
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and hasattr(obj, f"_{module_type}"):
                    functions.append(obj)
    return functions

def all_tool_functions(exclude: Optional[List[str]] = None) -> List[Any]:
    """Get all available tool functions."""
    return load_module_functions('tools', 'tool')

def all_agents(exclude: Optional[List[str]] = None) -> List[str]:
    """Get all available agents."""
    agents = []
    agents_dir = get_project_root() / 'agents'
    
    for file in os.listdir(agents_dir):
        if file.endswith('.py') and not file.startswith('__'):
            agent_name = file[:-3]
            if exclude and agent_name in exclude:
                continue
            agents.append(agent_name)
    
    return agents

def checkpointer(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.debug(f"Current state: {state}")
    return state