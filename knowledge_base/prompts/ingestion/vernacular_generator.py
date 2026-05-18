MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 256

SYSTEM_PROMPT = "Generate spoken-language aliases someone might use to refer to this item."

USER_TEMPLATE = (
    "Title: {title}\nSummary: {summary}\nTags: {tags}\n"
    'Return a JSON array of 3-8 short spoken aliases: ["alias1", ...]'
)
