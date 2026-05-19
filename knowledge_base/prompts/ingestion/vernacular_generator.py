from pydantic import BaseModel

MODEL = "gemini-2.5-flash"
MAX_TOKENS = 256


class VernacularOutput(BaseModel):
    terms: list[str]


SYSTEM_PROMPT = "Generate spoken-language aliases someone might use to refer to this item."

USER_TEMPLATE = (
    "Title: {title}\nSummary: {summary}\nTags: {tags}\n"
    "Return 3-8 short spoken aliases for this item."
)
