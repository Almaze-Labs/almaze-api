from typing import List, Any
from langchain_core.messages import SystemMessage, HumanMessage
from agents.base import BaseAgent, AgentState
from tools.file.write_to_file import write_to_file
from tools.file.read_file import read_file
from tools.file.delete_file import delete_file
from tools.file.overwrite_file import overwrite_file
from tools.agent.assign_agent_to_task import assign_agent_to_task

class ToolSmithAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are tool_smith, a ReAct agent that develops other ReAct agents.
        
        You develop agents in python using LangGraph to define their flow.
        You design agents with the tools they potentially need to complete their tasks.
        
        You approach your given task this way:
        1. Create a detailed plan for how to design an agent to achieve the task.
        2. If new tools are required, assign tasks to the architect agent.
        3. Write the agent implementation and a smoke test to disk.
        4. Verify the smoke test doesn't error.
        5. Confirm the agent is complete with its name and a succinct description of its purpose."""

        tools = [
            write_to_file,
            read_file,
            delete_file,
            overwrite_file,
            assign_agent_to_task
        ]

        super().__init__("tool_smith", system_prompt, tools)

def tool_smith(task: str) -> str:
    """Creates new agents for specific purposes."""
    agent = ToolSmithAgent()
    return agent.process(task)