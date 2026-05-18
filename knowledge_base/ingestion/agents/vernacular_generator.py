import json
import anthropic

anthropic_client = anthropic.AsyncAnthropic()


class VernacularGenerator:
    async def generate(self, title: str, summary: str, tags: list[str]) -> list[str]:
        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system="Generate spoken-language aliases someone might use to refer to this item.",
            messages=[{"role": "user", "content": (
                f"Title: {title}\nSummary: {summary}\nTags: {', '.join(tags)}\n"
                "Return a JSON array of 3-8 short spoken aliases: [\"alias1\", ...]"
            )}],
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
