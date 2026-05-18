import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()


class DiagramAnalyzer:
    CONFIDENCE_THRESHOLD = 0.70

    async def analyze(self, image: bytes) -> dict:
        b64 = base64.standard_b64encode(image).decode()
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="""Analyze this logic diagram image and extract the decision logic it encodes.
Return ONLY valid JSON:
{
  "type": "venn_logic | decision_tree | flowchart | state_machine",
  "dimensions": ["dimension_name"],
  "regions": [{"conditions": {"dim_name": true_or_false}, "action": "symbol_or_text"}],
  "action_legend": {"symbol": "full meaning of the symbol"},
  "extraction_confidence": 0.0-1.0,
  "raw_description": "plain text description of what the diagram shows"
}
For Venn diagrams, enumerate ALL regions (2^N for N dimensions).
For flowcharts, list all decision nodes and their branches.""",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}
                    },
                    {
                        "type": "text",
                        "text": "Extract the complete decision logic from this diagram. Return JSON only."
                    }
                ]
            }]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)

    def is_high_confidence(self, result: dict) -> bool:
        return result.get("extraction_confidence", 0) >= self.CONFIDENCE_THRESHOLD
