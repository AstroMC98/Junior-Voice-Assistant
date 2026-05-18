import anthropic
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.store.knowledge_store import KnowledgeStore

MAX_AGENT_CALLS = 10


class Tier3Orchestrator:
    def __init__(self, store: KnowledgeStore):
        self.store = store
        self.client = anthropic.AsyncAnthropic()

    async def resolve(
        self,
        query: ProcessedQuery,
        session: Session,
        failure_trace: list[dict],
    ) -> str:
        tools = [
            {
                "name": "search_knowledge_base",
                "description": "Search the knowledge base by keyword. Returns matching entry titles.",
                "input_schema": {
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                    "required": ["keyword"],
                },
            }
        ]

        messages = [
            {
                "role": "user",
                "content": (
                    f"Query: {query.cleaned_text}\n"
                    f"Previous Tier 1 and Tier 2 attempts failed: {failure_trace}\n"
                    "Answer ONLY from the knowledge base using the search tool. Cite entry IDs."
                ),
            }
        ]

        calls = 0
        while calls < MAX_AGENT_CALLS:
            response = await self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                return next(
                    (b.text for b in response.content if hasattr(b, "text")),
                    "I was unable to find a definitive answer in the knowledge base.",
                )

            tool_use = next(
                (b for b in response.content if b.type == "tool_use"), None
            )
            if not tool_use:
                break

            keyword = tool_use.input.get("keyword", "")
            results = await self.store.search_by_tag(keyword)
            entry_titles = [e.title for e in results[:5]]

            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": str(entry_titles),
                }],
            })
            calls += 1

        return "I was unable to find a definitive answer in the knowledge base."
