import anthropic
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.prompts.query.tier3_orchestrator import (
    MODEL, MAX_TOKENS, MAX_AGENT_CALLS,
    SEARCH_TOOL_DEFINITION, FALLBACK_RESPONSE, INITIAL_USER_TEMPLATE,
)


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
        tools = [SEARCH_TOOL_DEFINITION]

        messages = [
            {
                "role": "user",
                "content": INITIAL_USER_TEMPLATE.format(
                    query=query.cleaned_text,
                    failure_trace=failure_trace,
                ),
            }
        ]

        calls = 0
        while calls < MAX_AGENT_CALLS:
            response = await self.client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                tools=tools,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                return next(
                    (b.text for b in response.content if hasattr(b, "text")),
                    FALLBACK_RESPONSE,
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

        return FALLBACK_RESPONSE
