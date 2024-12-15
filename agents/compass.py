from typing import List, Any, Dict, Literal
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from agents.base import BaseAgent, AgentState
from tools.agent.list_available_agents import list_available_agents
from tools.agent.assign_agent_to_task import assign_agent_to_task
from langgraph.graph import END
import json
import re

AGENT_DESCRIPTIONS = {
    "tool_smith": "Creates new specialized agents for specific tasks",
    "architect": "Creates and manages tools that other agents can use",
    "scout": "Performs internet research and gathers information",
    "techsage": "Handles code-related tasks and software development"
}

class CompassAgent(BaseAgent):
    def __init__(self):
        system_prompt = """You are Compass, the orchestrator agent of ALMAZE.
Your role is to:
1. Understand the user's request
2. Determine which agent(s) would be best suited for the task
3. Coordinate between agents to accomplish the goal

Available specialized agents:
- tool_smith: Creates new specialized agents for specific tasks
- architect: Creates and manages tools that other agents can use
- scout: Performs internet research and gathers information
- techsage: Handles code-related tasks and software development

Follow these steps:
1. Analyze the user's request
2. If the task requires specialized capabilities:
   - Delegate to the appropriate agent using the assign_agent_to_task tool
   - Wait for their response and coordinate any follow-up tasks
3. If no specialized agent is needed:
   - Respond directly to simple queries
   - For complex tasks, break them down and coordinate multiple agents"""
        
        super().__init__("compass", system_prompt, [list_available_agents, assign_agent_to_task])

    def _clean_agent_name(self, name: str) -> str:
        cleaned_name = re.sub(r'^[\d\s\.]+', '', name).strip().lower()
        
        # Ensure the cleaned name matches one of the available agents
        for valid_agent in AGENT_DESCRIPTIONS.keys():
            if valid_agent in cleaned_name:
                return valid_agent
        
        return 'direct'

    def _analyze_task(self, task: str) -> Dict[str, Any]:
        """Analyze the task to determine required agents with stricter agent selection."""
        analysis_prompt = f"""Carefully analyze this task and determine the MOST APPROPRIATE single agent to handle it.
Do NOT suggest multiple agents unless absolutely necessary.

Task: {task}

Available agents:
{AGENT_DESCRIPTIONS}

Return your analysis in this format:
1. Primary agent needed (or 'direct' if compass can handle it)
2. Precise reason for choosing this agent
3. Additional agents (ONLY if truly required, otherwise 'None')
4. Brief task breakdown (if needed)"""
        
        response = self.llm.invoke(analysis_prompt)
        
        # Analyze the response to ensure a more focused agent selection
        analysis = self._parse_analysis(response.content)
        
        # Additional filtering to prevent unnecessary agent chaining
        if analysis['primary_agent'] == 'scout':
            # For web research tasks, prevent automatic additional agents
            analysis['additional_agents'] = []
        
        return analysis

    def _parse_analysis(self, analysis: str) -> Dict[str, Any]:
        """Parse the analysis response into a structured format."""
        try:
            lines = analysis.split('\n')
            return {
                'primary_agent': self._clean_agent_name(lines[0].split(':')[1].strip()),
                'reason': lines[1].split(':')[1].strip() if len(lines) > 1 else '',
                'additional_agents': [
                    self._clean_agent_name(a.strip()) 
                    for a in (lines[2].split(':')[1].split(',') if len(lines) > 2 and ':' in lines[2] 
                    else lines[2].split(',') if len(lines) > 2 else [])
                    if a.strip() and a.strip().lower() != 'none'
                ],
                'task_breakdown': lines[3:] if len(lines) > 3 else []
            }
        except Exception as e:
            print(f"Error parsing analysis: {str(e)}")
            return {
                'primary_agent': 'direct',
                'reason': 'Error in analysis',
                'additional_agents': [],
                'task_breakdown': []
            }

    def _process_step(self, state: AgentState) -> AgentState:
        """Process a single step with proper agent coordination."""
        print(f"\n{self.name} is thinking...")
        iterations = state.get('iterations', 0)
        
        try:
            # Get the last message
            last_message = messages[-1] if messages else None
            if not last_message:
                return state

            # Prepare response data
            response_data = {
                "task": last_message.content,
                "analysis": None,
                "response": None,
                "agent_responses": [],
                "error": None
            }

            # Analyze task and coordinate agents
            analysis = self._analyze_task(last_message.content)
            response_data["analysis"] = analysis

            if analysis['primary_agent'] == 'direct':
                # Direct response from Compass
                chat_history = messages[:-1] if len(messages) > 1 else []
                response = self.llm.invoke(
                    self.prompt.format_messages(
                        input=last_message.content,
                        chat_history=chat_history
                    )
                ).content
                response_data["response"] = response
                response_data["agent_responses"] = [
                    {
                        "agent": "compass",
                        "response": response
                    }
                ]
            else:
                # Delegate to appropriate agents
                response_data["agent_responses"] = self._delegate_to_agents(analysis, last_message.content)
                response = self._format_responses(
                    [resp['response'] for resp in response_data["agent_responses"]], 
                    analysis
                )
                response_data["response"] = response

            # Convert response to JSON
            json_response = json.dumps(response_data)

            # Update state
            return {
                "messages": messages + [AIMessage(content=json_response)],
                "iterations": iterations + 1
            }

        except Exception as e:
            error_msg = f"Error in processing: {str(e)}"
            print(error_msg)
            
            error_response = {
                "task": last_message.content if last_message else "No task",
                "error": error_msg,
                "suggestions": [
                    "Try rephrasing your request",
                    "Break down the task into smaller steps",
                    "Check the task requirements"
                ]
            }
            
            return {
                "messages": messages + [SystemMessage(content=json.dumps(error_response))],
                "iterations": iterations + 1
            }

    def _delegate_to_agents(self, analysis: Dict[str, Any], task: str) -> List[Dict[str, str]]:
        """Delegate task to appropriate agents and return their responses."""
        agent_responses = []
        
        # Handle primary agent
        primary_response = assign_agent_to_task.invoke({
            "agent_name": analysis['primary_agent'],
            "task": task
        })
        agent_responses.append({
            "agent": analysis['primary_agent'],
            "response": primary_response
        })

        # Handle additional agents if needed
        for agent in analysis['additional_agents']:
            if agent != analysis['primary_agent']:
                subtask = self._create_subtask(task, agent, agent_responses)
                response = assign_agent_to_task.invoke({
                    "agent_name": agent,
                    "task": subtask
                })
                agent_responses.append({
                    "agent": agent,
                    "response": response
                })

        return agent_responses
    def _create_subtask(self, original_task: str, agent: str, previous_responses: List[Dict[str, str]]) -> str:
        """Create a subtask for an agent based on context."""
        previous_responses_str = "\n".join([
            f"[{resp['agent']}]: {resp['response']}" for resp in previous_responses
        ])
        
        return f"""Original task: {original_task}

Previous responses:
{previous_responses_str}

Based on the above, complete your part of the task as the {agent} agent.
Focus on your specialization: {AGENT_DESCRIPTIONS.get(agent, 'Complete the task')}"""

    def _format_responses(self, responses: List[str], analysis: Dict[str, Any]) -> str:
        """Format responses into a coherent reply."""
        return f"""Task Analysis:
Primary Agent: {analysis['primary_agent']}
Reason: {analysis['reason']}

Agent Responses:
{chr(10).join(responses)}

Summary:
I've coordinated the appropriate agents to address your request. Above are their combined responses.
Let me know if you need any clarification or have additional questions."""

    def _should_continue(self, state: AgentState) -> Literal["continue", END]:
        """Determine whether to continue processing."""
        iterations = state.get('iterations', 0)
        messages = state.get('messages', [])
        
        if iterations >= self.max_iterations:
            return END
        
        last_message = messages[-1] if messages else None
        if last_message and not hasattr(last_message, 'function_call'):
            return END
            
        return "continue"

def compass(session_id: str, task: str) -> str:
    """The orchestrator that interacts with users and coordinates other agents."""
    agent = CompassAgent()
    return agent.process(task)