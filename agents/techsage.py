from typing import List, Any, Dict, Literal, Optional
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.graph import END
from agents.base import BaseAgent, AgentState
from tools.file.write_to_file import write_to_file
from tools.agent.assign_agent_to_task import assign_agent_to_task
from tools.file.delete_file import delete_file
import json
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TechSageAgent(BaseAgent):
    def __init__(self, max_iterations: int = 1):
        system_prompt = """You are techsage, a specialized development agent.

Your primary task is to generate well-structured, production-ready code based on user requirements.

Response Format:
Always structure your response with:
1. Code implementation in clear, distinct sections with proper file markers
2. Each file should be marked with ```language filename.ext
3. Include setup instructions and usage examples
4. Provide clear API documentation if applicable

Follow these guidelines:
1. Use modern best practices
2. Include error handling
3. Add proper comments and documentation
4. Optimize for readability and maintainability
5. Consider scalability and performance

Code Structure:
- Organize code logically
- Use consistent formatting
- Include necessary imports
- Add type hints where applicable
- Implement error handling
- Add proper validation

Documentation Guidelines:
- Clear setup instructions
- Usage examples
- API documentation
- Configuration details
- Dependencies list
- Error handling guide"""

        super().__init__(
            name="techsage",
            system_prompt=system_prompt,
            tools=[write_to_file, assign_agent_to_task],
            max_iterations=max_iterations
        )

    def _analyze_task(self, task: str) -> Dict[str, Any]:
        """Analyze the task to determine type and requirements with improved error handling."""
        analysis_prompt = f"""Analyze this development task and provide structured output:
Task: {task}

Format response as a valid JSON with these keys:
- task_type: web/script/config/documentation
- language: programming language name
- files_required: list of filenames
- technologies: relevant technologies
- implementation_approach: brief strategy
- primary_features: key features"""

        try:
            response = self.llm.invoke(analysis_prompt)
            # Enhanced parsing to handle various JSON formats
            content = response.content.strip()
            
            # Remove code block markers if present
            content = re.sub(r'^```(json)?|```$', '', content, flags=re.MULTILINE).strip()
            
            # Attempt to parse JSON with fallback
            try:
                analysis = json.loads(content)
            except json.JSONDecodeError:
                # Attempt to fix common JSON formatting issues
                content = re.sub(r'(?<=\w)\'', '"', content)  # Replace single quotes with double quotes
                analysis = json.loads(content)
            
            return analysis
        except Exception as e:
            logger.error(f"Task analysis error: {e}")
            return {
                "task_type": "script",
                "language": "python",
                "files_required": ["main.py"],
                "technologies": ["python"],
                "implementation_approach": "Basic implementation",
                "primary_features": ["core functionality"]
            }

    def _get_implementation_prompt(self, task: str, analysis: Dict[str, Any]) -> str:
        """Generate a more comprehensive implementation prompt."""
        return f"""Comprehensive Code Generation Task

Detailed Requirements:
- Primary Task: {task}
- Language: {analysis['language']}
- Project Type: {analysis['task_type']}
- Key Features: {', '.join(analysis['primary_features'])}

Comprehensive Implementation Guidelines:
1. Create full implementation for each required file
2. Use modern {analysis['language']} best practices
3. Include robust error handling
4. Implement input validation
5. Add comprehensive type hints
6. Write clear, explanatory comments

Structural Requirements:
- Each file must be marked with: ```{analysis['language']} filename.ext
- Include complete implementation
- Add section headers for:
  a. Setup Instructions
  b. Usage Examples
  c. API Documentation (if applicable)
  d. Configuration Guide
  e. Error Handling Guide

Provide a production-ready solution that emphasizes:
- Code quality
- Maintainability
- Scalability
- Performance considerations"""

    def _extract_code_blocks(self, content: str) -> Dict[str, Dict[str, Any]]:
        """Enhanced code block extraction with robust parsing."""
        code_blocks = {}
        code_block_pattern = re.compile(r'```(\w+)?\s*(\S+)\n(.*?)```', re.DOTALL)
        
        for match in code_block_pattern.finditer(content):
            language = match.group(1) or 'text'
            filename = match.group(2)
            code = match.group(3).strip()
            
            code_blocks[filename] = {
                "language": language,
                "content": code,
                "filename": filename
            }
        
        return code_blocks

    def _process_step(self, state: AgentState) -> AgentState:
        """Process a development task with enhanced error handling and logging."""
        logger.info(f"{self.name} is processing development task...")
        messages: List[BaseMessage] = state.get('messages', [])

        try:
            task = messages[-1].content if messages and hasattr(messages[-1], 'content') else "No task provided"
            
            # Task analysis
            analysis = self._analyze_task(task)
            
            # Implementation generation
            implementation = self.llm.invoke(implementation_prompt)
            
            # Process code blocks
            code_blocks = self._extract_code_blocks(implementation.content)
            
            # Write files
            files_created = []
            for filename, file_data in code_blocks.items():
                try:
                    write_to_file.invoke({
                        "filepath": filename,
                        "content": file_data["content"]
                    })
                    files_created.append(filename)
                except Exception as write_error:
                    logger.error(f"File write error for {filename}: {write_error}")
            
            # Comprehensive response generation
            response_data = {
                "status": "success",
                "query": task,
                "timestamp": datetime.now().isoformat(),
                "analysis": {
                    "task_type": analysis.get("task_type", "undefined"),
                    "language": analysis.get("language", "undefined"),
                    "technologies": analysis.get("technologies", [])
                },
                "implementation": {
                    "files": [
                        {
                            "filename": file_data["filename"],
                            "language": file_data["language"],
                            "content": file_data["content"]
                        }
                        for file_data in code_blocks.values()
                    ],
                    "setup": self._extract_section(implementation.content, "Setup Instructions"),
                    "usage": self._extract_section(implementation.content, "Usage Examples"),
                    "api_docs": self._extract_section(implementation.content, "API Documentation"),
                    "configuration": self._extract_section(implementation.content, "Configuration Guide")
                },
                "files_created": files_created
            }

            for filename in files_created:
                try:
                    delete_file.invoke({"filepath": filename})
                except Exception as delete_error:
                    logger.error(f"File deletion error for {filename}: {delete_error}")

            return {
                "messages": messages + [AIMessage(content=json.dumps(response_data, indent=2))],
                "iterations": 1
            }

        except Exception as e:
            logger.error(f"Development task processing error: {e}")
            error_response = {
                "status": "error",
                "query": task,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "message": "Comprehensive error in code generation",
                "suggestions": [
                    "Provide more specific and granular requirements",
                    "Clearly specify the programming language and framework",
                    "Break down complex requirements into smaller, manageable tasks",
                    "Verify the input task description"
                ]
            }
            return {
                "messages": messages + [AIMessage(content=json.dumps(error_response, indent=2))],
                "iterations": 1
            }

    def _extract_section(self, content: str, section_name: str) -> str:
        """Enhanced section extraction with regex and multiple parsing strategies."""
        try:
            # Regex pattern to find section content
            section_pattern = re.compile(
                rf'{section_name}:\n(.*?)(?=\n\n|\Z)', 
                re.DOTALL | re.IGNORECASE
            )
            match = section_pattern.search(content)
            
            if match:
                return match.group(1).strip()
            
            # Fallback parsing strategy
            if section_name in content:
                parts = content.split(section_name)
                if len(parts) > 1:
                    section = parts[1].split('\n\n')[0].strip()
                    return section
        except Exception as e:
            logger.warning(f"Section extraction error for {section_name}: {e}")
        
        return ""

    def _should_continue(self, state: AgentState) -> Literal["continue", END]:
        """Always terminate after one iteration."""
        return END

def techsage(task: str) -> str:
    """Execute development task and return comprehensive results."""
    try:
        agent = TechSageAgent()
        return agent.process(task)
    except Exception as e:
        logger.error(f"Tech Sage agent execution failed: {e}")
        return json.dumps({
            "status": "critical_error",
            "message": "Failed to execute engineering task",
            "error": str(e),
            "suggestions": [
                "Retry the task",
                "Verify input requirements",
                "Contact system administrator"
            ]
        })