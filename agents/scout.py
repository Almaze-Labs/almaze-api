from typing import List, Any, Dict, Literal, Optional
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import END
from agents.base import BaseAgent, AgentState
from tools.web.duck_duck_go_web_search import duck_duck_go_web_search
import json
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ScoutAgent(BaseAgent):
    def __init__(self):
        system_prompt = """# Scout Agent

## Role & Objective
You are a professional web researcher focused on delivering accurate, comprehensive, and well-structured information for any query.

## Core Principles
1. Research Quality
   - Thorough search across credible sources
   - Fact verification and cross-referencing
   - Focus on recent, reliable information

2. Response Structure
   - Clear, logical organization
   - Key points with bullet points
   - Supporting evidence and examples
   - Source citations when relevant

3. Content Balance
   - Accuracy over speculation
   - Clarity over complexity
   - Concise yet comprehensive
   - Neutral and objective tone

## Process Flow
1. Analyze query intent
2. Gather relevant information
3. Synthesize findings
4. Present structured response with:
   - Main concept explanation
   - Key facts and details
   - Related context

Your responses should be informative, clear, and well-organized, focusing on providing maximum value with optimal efficiency."""

        super().__init__(
            name="scout",
            system_prompt=system_prompt,
            tools=[duck_duck_go_web_search],
            max_iterations=1
        )

    def _clean_text(self, text: str) -> str:
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', text)
            
            # Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip()
            
            # Remove special characters and normalize
            text = re.sub(r'[^\w\s.,!?-]', '', text)
            
            return text
        except Exception as e:
            logger.warning(f"Text cleaning error: {e}")
            return text

    def _format_query(self, query: str) -> str:
        query = query.lower().strip()
        
        # Common query transformations
        patterns = [
            (r'^what\s+is\s+', ''),
            (r'^who\s+is\s+', ''),
            (r'^how\s+does\s+', ''),
            (r'^why\s+', '')
        ]
        
        for pattern, repl in patterns:
            query = re.sub(pattern, repl, query).strip()
        
        # Enhance query with descriptive terms
        enhance_terms = [
            "definition", "explanation", "overview", 
            "key concepts", "main features", "important aspects"
        ]
        
        return f"{query} {' '.join(enhance_terms)}"

    def _process_search_results(self, search_results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        try:
            compiled_info = []
            sources = []
            
            for result in search_results:
                # Only add non-empty, unique snippets
                snippet = self._clean_text(result.get('snippet', ''))
                if snippet and snippet not in compiled_info:
                    compiled_info.append(snippet)
                
                # Collect unique sources
                link = result.get('link', '')
                if link and link not in sources:
                    sources.append(link)
            
            # Limit sources and info
            sources = sources[:3]
            compiled_info = compiled_info[:5]
            
            if not compiled_info:
                return {
                    "status": "no_results",
                    "query": query,
                    "timestamp": datetime.now().isoformat(),
                    "error": "No information found",
                    "suggestions": [
                        f"Ask about specific aspects of {query}",
                        "Use more specific terms",
                        "Rephrase your question"
                    ]
                }
            
            return {
                "status": "success",
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "compiled_info": compiled_info,
                "sources": sources
            }
        
        except Exception as e:
            logger.error(f"Search result processing error: {e}")
            return {
                "status": "error",
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "suggestions": [
                    "Try a different search approach",
                    "Check your internet connection",
                    "Simplify your query"
                ]
            }

    def _process_step(self, state: AgentState) -> AgentState:
        logger.info(f"{self.name} is researching...")
        messages = state.get('messages', [])

        try:
            # Extract and format query
            query = messages[-1].content if messages and hasattr(messages[-1], 'content') else "No query provided"
            formatted_query = self._format_query(query)

            # Perform web search
            search_results = duck_duck_go_web_search.invoke({
                "query": formatted_query,
                "max_results": 3
            })

            # Process search results
            processed_results = self._process_search_results(search_results, query)
            
            # Handle no results scenario
            if processed_results["status"] == "no_results":
                return {
                    "messages": messages + [AIMessage(content=json.dumps(processed_results))],
                    "iterations": 1
                }

            # Generate comprehensive response
            response_prompt = f"""Based on the following information, provide a comprehensive response about: {query}

Information:
{chr(10).join(processed_results['compiled_info'])}

Please structure your response as:
1. Direct, concise explanation and example (2-3 sentences)
2. Key characteristics or facts (3-4 bullet points)
3. Additional contextual information
4. Practical applications or implications (if relevant)

and dont show these points as heading instead directly show your response in place of these points.

Focus on clarity, accuracy, and providing meaningful insights."""

            # Generate LLM response
            llm_response = self.llm.invoke(response_prompt)
            
            # Prepare final response
            response_data = {
                "status": "success",
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "message": llm_response.content,
                "sources": processed_results.get("sources", []),
                "key_points": [
                    point.strip() for point in llm_response.content.split('\n') 
                    if point.strip() and not point.strip().startswith('1.') and not point.strip().startswith('2.')
                ]
            }

            return {
                "messages": messages + [AIMessage(content=json.dumps(response_data))],
                "iterations": 1
            }

        except Exception as e:
            logger.error(f"Research process error: {e}")
            error_response = {
                "status": "error",
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "message": "Error occurred during research",
                "suggestions": [
                    "Try being more specific",
                    "Rephrase your question",
                    "Check your internet connection"
                ]
            }
            return {
                "messages": messages + [SystemMessage(content=json.dumps(error_response))],
                "iterations": 1
            }

    def _should_continue(self, state: AgentState) -> Literal["continue", END]:
        """Always end after one iteration."""
        return END

def scout(task: str) -> str:
    """Execute research task and return findings."""
    agent = ScoutAgent()
    return agent.process(task)