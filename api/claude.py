from anthropic import Anthropic
from api.models import Guide, Step, SessionResponse
from api.utils import extract_json
from api.prompts import (
    PROCESS_GUIDE_MODEL, PROCESS_GUIDE_MAX_TOKENS,
    PROCESS_GUIDE_SYSTEM, PROCESS_GUIDE_USER_IMAGE_SUFFIX,
    SESSION_TURN_MODEL, SESSION_TURN_MAX_TOKENS, SESSION_TURN_SYSTEM_TEMPLATE,
)


async def process_guide(
    source: str,
    text: str | None,
    images: list[str] | None,
    api_key: str,
) -> list[Step]:
    client = Anthropic(api_key=api_key)
    user_content: list[dict] = []

    if images:
        for i, img_b64 in enumerate(images):
            user_content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
            })
            user_content.append({"type": "text", "text": f"[Page {i}]"})
        user_content.append({
            "type": "text",
            "text": PROCESS_GUIDE_USER_IMAGE_SUFFIX,
        })
    else:
        user_content.append({"type": "text", "text": text or ""})

    response = client.messages.create(
        model=PROCESS_GUIDE_MODEL,
        max_tokens=PROCESS_GUIDE_MAX_TOKENS,
        system=PROCESS_GUIDE_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    text_out = response.content[0].text if response.content[0].type == "text" else "[]"
    raw = extract_json(text_out)
    return [Step(**item) for item in raw]


async def session_turn(
    guide: Guide,
    current_step_index: int,
    transcript: str,
    photo: str | None,
    api_key: str,
) -> SessionResponse:
    client = Anthropic(api_key=api_key)
    step = guide.steps[current_step_index]
    user_content: list[dict] = []

    if photo:
        user_content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": photo},
        })
    user_content.append({"type": "text", "text": transcript})

    steps_context = "\n".join(
        f"Step {s.index + 1}: {s.title} — {s.content}" for s in guide.steps
    )

    system_prompt = SESSION_TURN_SYSTEM_TEMPLATE.format(
        guide_title=guide.title,
        steps_context=steps_context,
        current_step_num=step.index + 1,
        total_steps=len(guide.steps),
        step_title=step.title,
        step_content=step.content,
    )

    response = client.messages.create(
        model=SESSION_TURN_MODEL,
        max_tokens=SESSION_TURN_MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )

    text_out = response.content[0].text if response.content[0].type == "text" else "{}"
    try:
        raw = extract_json(text_out)
        return SessionResponse(**raw)
    except Exception:
        return SessionResponse(
            speech="Sorry, I had trouble with that. Please try again.",
            action=None,
            step=None,
        )
