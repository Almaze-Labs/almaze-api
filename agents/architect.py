from langchain_core.messages import SystemMessage, HumanMessage
from agents.base import BaseAgent
from utils import all_tool_functions

class ArchitectAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are architect, a ReAct agent that develops LangChain tools for other agents.

You approach your given task this way:
1. Write the tool implementation and tests to disk.
2. Verify the tests pass.
3. Confirm the tool is complete with its name and a succinct description of its purpose.

Tools MUST:
- Go in the `tools` directory
- Use the `@tool` decorator
- Include a docstring that succinctly describes what the tool does
- Have a corresponding test file that verifies the intended behavior
"""
        super().__init__("architect", system_prompt, all_tool_functions())

    def process(self, input_text: str) -> str:
        """Process request to create a new tool."""
        return self.graph.invoke({
            "messages": [
                SystemMessage(self.system_prompt),
                HumanMessage(input_text)
            ]
        })

def architect(task: str) -> str:
    """Creates new tools for agents to use."""
    agent = ArchitectAgent()
    return agent.process(task)