from typing import Dict
from langchain_core.tools import tool

@tool
def assign_agent_to_task(agent_name: str, task: str) -> str:
    """Assigns a task to a specific agent."""
    try:
        # Import agent module
        agent_module = __import__(f"agents.{agent_name}", fromlist=[agent_name])
        
        # Get agent function
        agent_func = getattr(agent_module, agent_name)
        
        # Execute task with session ID (if required)
        if agent_name == 'compass':
            return agent_func('internal_session', task)
        else:
            return agent_func(task)
    except ImportError:
        return f"Error: Agent '{agent_name}' not found"
    except AttributeError:
        return f"Error: Agent function '{agent_name}' not found in module"
    except Exception as e:
        return f"Error assigning task to agent {agent_name}: {str(e)}"