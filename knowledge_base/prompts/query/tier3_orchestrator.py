MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
MAX_AGENT_CALLS = 10

SEARCH_TOOL_DEFINITION = {
    "name": "search_knowledge_base",
    "description": "Search the knowledge base by keyword. Returns matching entry titles.",
    "input_schema": {
        "type": "object",
        "properties": {"keyword": {"type": "string"}},
        "required": ["keyword"],
    },
}

FALLBACK_RESPONSE = "I was unable to find a definitive answer in the knowledge base."

# Note: no {{ escaping needed — this is a plain string used in an f-string, not .format()
INITIAL_USER_TEMPLATE = (
    "Query: {query}\n"
    "Previous Tier 1 and Tier 2 attempts failed: {failure_trace}\n"
    "Answer ONLY from the knowledge base using the search tool. Cite entry IDs."
)
