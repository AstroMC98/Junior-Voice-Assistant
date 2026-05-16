import re
import json
from nanoid import generate as _nanoid_generate
from bs4 import BeautifulSoup


def generate_id(size: int = 10) -> str:
    return _nanoid_generate(size=size)


def extract_json(text: str):
    clean = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    clean = re.sub(r"\s*```\s*$", "", clean, flags=re.MULTILINE).strip()
    return json.loads(clean)


def strip_html(html: str, max_chars: int = 50_000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
