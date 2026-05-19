import base64
from api.models import Guide, Step, SessionResponse
from api.utils import extract_json
from api.prompts import (
    PROCESS_GUIDE_MODEL, PROCESS_GUIDE_MAX_TOKENS,
    PROCESS_GUIDE_SYSTEM, PROCESS_GUIDE_USER_IMAGE_SUFFIX,
    SESSION_TURN_MODEL, SESSION_TURN_MAX_TOKENS, SESSION_TURN_SYSTEM_TEMPLATE,
)
from knowledge_base.llm_clients import make_client
from knowledge_base.utils.async_llm import run_llm, generate_with_images, generate_with_image


async def process_guide(
    source: str,
    text: str | None,
    images: list[str] | None,
    api_key: str,
) -> list[Step]:
    client = make_client(provider="claude", model=PROCESS_GUIDE_MODEL, api_key=api_key)

    if images:
        image_bytes = [base64.b64decode(img) for img in images]
        page_labels = "\n".join(f"[Page {i}]" for i in range(len(image_bytes)))
        prompt = f"{page_labels}\n{PROCESS_GUIDE_USER_IMAGE_SUFFIX}"
        response = await generate_with_images(
            client, image_bytes, prompt,
            system_instruction=PROCESS_GUIDE_SYSTEM,
            max_output_tokens=PROCESS_GUIDE_MAX_TOKENS,
        )
    else:
        response = await run_llm(
            client.generate,
            text or "",
            system_instruction=PROCESS_GUIDE_SYSTEM,
            max_output_tokens=PROCESS_GUIDE_MAX_TOKENS,
        )

    raw = extract_json(response.text)
    return [Step(**item) for item in raw]


async def session_turn(
    guide: Guide,
    current_step_index: int,
    transcript: str,
    photo: str | None,
    api_key: str,
) -> SessionResponse:
    client = make_client(provider="claude", model=SESSION_TURN_MODEL, api_key=api_key)
    step = guide.steps[current_step_index]

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

    if photo:
        photo_bytes = base64.b64decode(photo)
        response = await generate_with_image(
            client, photo_bytes, transcript,
            system_instruction=system_prompt,
            max_output_tokens=SESSION_TURN_MAX_TOKENS,
        )
    else:
        response = await run_llm(
            client.generate,
            transcript,
            system_instruction=system_prompt,
            max_output_tokens=SESSION_TURN_MAX_TOKENS,
        )

    try:
        raw = extract_json(response.text)
        return SessionResponse(**raw)
    except Exception:
        return SessionResponse(
            speech="Sorry, I had trouble with that. Please try again.",
            action=None,
            step=None,
        )
