import os
import sys

# Ensure the root project directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force UTF-8 encoding for standard output (Required for MCP stdio transport in Windows)
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import asyncio
import logging
from mcp.server.fastmcp import FastMCP
from app.api.deps import search_service_dep

logger = logging.getLogger(__name__)

# Initialize FastMCP Server
mcp = FastMCP("Stripe Docs Knowledge Base")

@mcp.tool()
def search_stripe_docs(query: str, top_k: int = 8) -> str:
    """
    Search the official Stripe Documentation.
    Use this tool whenever you need to find technical details, guides, or API references about Stripe products (Payments, Billing, Connect, Webhooks, etc).
    
    Args:
        query: The search query. Be descriptive and specific (e.g. 'How do I confirm a PaymentIntent?').
        top_k: Number of results to retrieve (default 8).
    """
    try:
        # Resolve the search_service using the existing dependency injection
        # Since FastMCP runs synchronously or asynchronously depending on the handler,
        # we can just call our synchronous/blocking search service for now.
        search_service = search_service_dep()
        
        # Execute the search
        out = search_service.search(query=query, top_k=top_k)
        
        results = out.get("results", [])
        if not results:
            return f"No results found for query: '{query}'."

        # Format the results into a readable markdown string for Claude
        formatted_output = f"## Search Results for '{query}'\n\n"
        for i, r in enumerate(results, 1):
            url = r.get("url", "")
            if r.get("anchor"):
                url += f"#{r.get('anchor')}"
                
            formatted_output += f"### {i}. {r.get('title', 'Untitled')}\n"
            formatted_output += f"**URL:** {url}\n"
            if "section_path" in r.get("metadata", {}):
                formatted_output += f"**Section:** {r['metadata']['section_path']}\n"
            formatted_output += f"**Content:**\n{r.get('content', '')}\n\n---\n\n"

        return formatted_output
    except Exception as e:
        logger.exception("Failed to execute search_stripe_docs tool.")
        return f"Error executing search: {str(e)}"

if __name__ == "__main__":
    # Start the MCP server using stdio transport (required for Claude Desktop)
    mcp.run(transport='stdio')
