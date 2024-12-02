# agents/base.py
from typing import List, Any, Dict, TypedDict, Union, Literal
from abc import ABC, abstractmethod

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

class AgentState(TypedDict):
    """Type definition for agent state."""
    messages: List[Any]
    iterations: int
    final_answer: str | None

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name: str, system_prompt: str, tools: List[Any], max_iterations: int = 5):
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools if tools is not None else []
        self.max_iterations = max_iterations
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            timeout=30  # 30 second timeout
        )
        self.prompt = self._create_prompt()
        self.tool_schemas = [convert_to_openai_function(t) for t in self.tools]
        self.graph = self._build_graph()

    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the prompt template."""
        return ChatPromptTemplate.from_messages([
            ("system", f"""{self.system_prompt}

Available tools:
{self._format_tools_description()}

Instructions:
1. If you can answer directly, do so without using tools.
2. If you need to use tools, use them and then provide a clear final answer.
3. Always ensure you provide a clear, complete response."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
        ])

    def _format_tools_description(self) -> str:
        """Format tools description for the prompt."""
        if not self.tools:
            return "No tools available"
        return "\n".join(f"- {t.name}: {t.description}" for t in self.tools)

    def _build_graph(self):
        """Build the agent's processing graph."""
        workflow = StateGraph(AgentState)
        
        # Add processing steps
        workflow.add_node("process", self._process_step)
        
        # Set entry point
        workflow.set_entry_point("process")
        
        # Add conditional ending
        workflow.add_conditional_edges(
            "process",
            self._should_continue,
            {
                "continue": "process",
                END: END
            }
        )
        
        return workflow.compile()

    def _process_step(self, state: AgentState) -> AgentState:
        """Process a single step."""
        messages = state.get('messages', [])
        iterations = state.get('iterations', 0)
        final_answer = state.get('final_answer')
        
        print(f"\n{self.name} is thinking... (iteration {iterations + 1}/{self.max_iterations})")
        
        try:
            # If we've reached max iterations, generate final answer
            if iterations >= self.max_iterations:
                final_response = self._generate_final_answer(messages)
                return {
                    "messages": messages,
                    "iterations": iterations + 1,
                    "final_answer": final_response
                }
            
            # Get the last message
            last_message = messages[-1] if messages else None
            if not last_message:
                return state
            
            # Get chat history
            chat_history = messages[:-1] if len(messages) > 1 else []
            
            # Get model response
            response = self.llm.invoke(
                self.prompt.format_messages(
                    input=last_message.content if hasattr(last_message, 'content') else str(last_message),
                    chat_history=chat_history
                ),
                functions=self.tool_schemas if self.tools else None
            )
            
            # If response has function call, execute tool
            if hasattr(response, 'function_call') and response.function_call:
                tool_result = self._execute_tool(response.function_call)
                new_messages = messages + [
                    AIMessage(content="", function_call=response.function_call),
                    SystemMessage(content=str(tool_result))
                ]
            else:
                new_messages = messages + [AIMessage(content=response.content)]
                final_answer = response.content
            
            return {
                "messages": new_messages,
                "iterations": iterations + 1,
                "final_answer": final_answer
            }
            
        except Exception as e:
            print(f"Error in processing: {str(e)}")
            error_msg = f"Error occurred: {str(e)}"
            return {
                "messages": messages + [SystemMessage(content=error_msg)],
                "iterations": iterations + 1,
                "final_answer": error_msg
            }

    def _execute_tool(self, function_call: Any) -> str:
        """Execute a tool call."""
        try:
            tool = next((t for t in self.tools if t.name == function_call.name), None)
            if tool:
                return tool.invoke(function_call.arguments)
            return f"Tool {function_call.name} not found"
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    def _generate_final_answer(self, messages: List[Any]) -> str:
        """Generate a final answer from the conversation history."""
        try:
            # Create a prompt to summarize the conversation
            summary_prompt = f"""Based on the conversation history, provide a clear final answer.
            If no clear answer was reached, provide the best possible response based on available information.
            
            History: {[m.content for m in messages if hasattr(m, 'content')]}"""
            
            response = self.llm.invoke(summary_prompt)
            return response.content
        except Exception as e:
            return f"Failed to generate final answer: {str(e)}"

    def _should_continue(self, state: AgentState) -> Literal["continue", END]:
        """Determine whether to continue processing."""
        iterations = state.get('iterations', 0)
        final_answer = state.get('final_answer')
        
        if final_answer is not None or iterations >= self.max_iterations:
            return END
        return "continue"

    def process(self, input_text: str) -> str:
        """Process input and return response."""
        initial_state = {
            "messages": [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=input_text)
            ],
            "iterations": 0,
            "final_answer": None
        }
        
        try:
            final_state = self.graph.invoke(initial_state)
            
            if final_state.get('final_answer'):
                return final_state['final_answer']
            
            if final_state and "messages" in final_state:
                messages = final_state["messages"]
                return messages[-1].content if messages else "No response generated"
            
            return "No response generated"
        except Exception as e:
            print(f"Processing error: {str(e)}")
            return f"Error processing request: {str(e)}"