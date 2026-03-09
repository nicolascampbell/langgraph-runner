from langchain_core.tools import tool


@tool
def web_search(query: str) -> str:
    """Search the web and return the top results as a formatted string."""
    from ddgs import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))

    if not results:
        return "No results found."

    lines = []
    for r in results:
        lines.append(f"Title: {r.get('title', '')}")
        lines.append(f"URL: {r.get('href', '')}")
        lines.append(f"Snippet: {r.get('body', '')}")
        lines.append("")

    return "\n".join(lines).strip()


def get_web_search_tools():
    return [web_search]
