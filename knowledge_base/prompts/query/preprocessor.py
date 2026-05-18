from pydantic import BaseModel

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 256

SYSTEM_PROMPT = "Extract entities from a voice query. Return JSON only."

# Note: {{ and }} render as literal { } after .format(query=...)
USER_TEMPLATE = (
    "Query: {query}\n"
    'Return: {{"colors": [...], "numbers": [...], "positions": ["top","left",...], '
    '"labels": [...], "uncertainty": ["phrases expressing doubt"]}}'
)


class PreprocessorOutput(BaseModel):
    colors: list[str] = []
    numbers: list[str] = []
    positions: list[str] = []
    labels: list[str] = []
    uncertainty: list[str] = []
