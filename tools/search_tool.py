import logging
from tavily import TavilyClient
from config.settings import settings

logger = logging.getLogger(__name__)


class WebSearchTool:

    def __init__(self):
        self._client = TavilyClient(api_key=settings.tavily_api_key)

    def search(self, query: str, max_results: int = 3) -> str:
        """
        Searches the web for the given query and returns a
        formatted string of results ready to inject into an LLM prompt.
        """
        logger.info(f"[Search] Querying Tavily: {query}")

        try:
            response = self._client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
            )

            results = response.get("results", [])

            if not results:
                return "No relevant search results found."

            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(
                    f"[{i}] {r.get('title', 'No title')}\n"
                    f"URL: {r.get('url', '')}\n"
                    f"Summary: {r.get('content', '')[:300]}"
                )

            return "\n\n".join(formatted)

        except Exception as e:
            logger.error(f"[Search] Tavily search failed: {e}")
            return f"Web search failed: {str(e)}"


# Singleton
_search_tool: WebSearchTool | None = None


def get_search_tool() -> WebSearchTool:
    global _search_tool
    if _search_tool is None:
        _search_tool = WebSearchTool()
    return _search_tool