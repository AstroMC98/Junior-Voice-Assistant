from anthropic import Anthropic
from api.models import Guide, Step, SessionResponse
from api.utils import extract_json


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
            "text": (
                "Extract all ordered steps from this guide. "
                "For steps associated with an image, set image_index to that [Page N] number."
            ),
        })
    else:
        user_content.append({"type": "text", "text": text or ""})

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=(
            "Extract ordered steps from this guide document.\n"
            "Return ONLY a valid JSON array. Each element must follow this shape exactly:\n"
            '{ "index": number, "title": string, "content": string, "image_index"?: number, '
            '"crop"?: { "x": number, "y": number, "w": number, "h": number } }\n'
            "image_index refers to which [Page N] label the step's image appears on.\n"
            "crop is the relevant region of that page image as percentage of image dimensions (0-100).\n"
            "No markdown, no prose — JSON array only."
        ),
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

    system_prompt = (
        f'You are Junior, a hands-free guide assistant.\n'
        f'Guide: "{guide.title}"\n'
        f"All steps:\n{steps_context}\n\n"
        f"Current step: {step.index + 1} of {len(guide.steps)} — {step.title}: {step.content}\n\n"
        "Rules:\n"
        "- Respond in 1-2 sentences, naturally spoken\n"
        '- If the user says "next", "done", or "continue": set action to "advance", '
        "step to the next 0-based step index (current + 1)\n"
        '- If the user says "go back", "back", or "previous": set action to "advance", '
        "step to the previous 0-based index (current - 1, minimum 0)\n"
        '- If the user asks to see something visually ("show me", "what does it look like"): '
        'set action to "show_image", step to current 0-based index\n'
        "- On a camera photo: assess whether it matches the current step; give clear go/no-go feedback\n"
        "- Always respond as valid JSON only — no prose outside the JSON:\n"
        '  { "speech": "...", "action": "show_image" | "advance" | null, "step": <0-based number or null> }'
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
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
