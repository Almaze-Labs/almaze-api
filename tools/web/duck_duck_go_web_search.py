import os
from typing import List, Dict, Optional, Union
from langchain_core.tools import tool
import http.client
import json
import logging
from urllib.parse import quote_plus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WebSearchTool:
    
    def __init__(self, max_results: int = 5):
        self.max_results = max_results
        # Serper API key
        self.serper_api_key = os.getenv('SERPER_API_KEY')

    def _clean_text(self, text: str) -> str:
        return ' '.join(text.split())

    def search_duckduckgo(self, query: str) -> List[Dict[str, str]]:
        try:
            import requests
            
            encoded_query = quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Add abstract if available
            if data.get('Abstract'):
                results.append({
                    'title': data.get('AbstractSource', 'DuckDuckGo Abstract'),
                    'link': data.get('AbstractURL', ''),
                    'snippet': self._clean_text(data.get('Abstract', ''))
                })
            
            # Add related topics
            for topic in data.get('RelatedTopics', [])[:self.max_results]:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append({
                        'title': topic.get('FirstURL', '').split('/')[-1].replace('_', ' '),
                        'link': topic.get('FirstURL', ''),
                        'snippet': self._clean_text(topic.get('Text', ''))
                    })
            
            return results
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return []

    def search_serper(self, query: str) -> List[Dict[str, str]]:
        if not self.serper_api_key:
            logger.warning("Serper API key not found")
            return []
        
        try:
            conn = http.client.HTTPSConnection("google.serper.dev")
            payload = json.dumps({
                "q": query,
                "num": self.max_results
            })
            headers = {
                'X-API-KEY': self.serper_api_key,
                'Content-Type': 'application/json'
            }
            
            conn.request("POST", "/search", payload, headers)
            res = conn.getresponse()
            data = res.read().decode("utf-8")
            
            # Parse the JSON response
            search_results = json.loads(data)
            
            results = []
            for result in search_results.get('organic', []):
                results.append({
                    'title': result.get('title', ''),
                    'link': result.get('link', ''),
                    'snippet': self._clean_text(result.get('snippet', ''))
                })
            
            return results
        except Exception as e:
            logger.error(f"Serper search error: {e}")
            return []

    def search(self, query: str) -> List[Dict[str, str]]:

        search_methods = [
            self.search_serper,  # Changed order to try Serper first
            self.search_duckduckgo,
        ]
        
        for method in search_methods:
            results = method(query)
            if results:
                return results
        
        # Fallback if all methods fail
        logger.warning(f"No results found for query: {query}")
        return [{
            'title': 'Search Unavailable',
            'link': '',
            'snippet': f"Unable to find information about {query}. Please try a different query."
        }]
# Create a tool wrapper
@tool
def duck_duck_go_web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Web search tool with multiple search strategies.
    
    :param query: Search query
    :param max_results: Maximum number of results to return
    :return: List of search results
    """
    search_tool = WebSearchTool(max_results=max_results)
    return search_tool.search(query)