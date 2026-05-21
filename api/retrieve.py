from api.models import Guide


def build_guide_context(guide: Guide, current_step_index: int) -> str:
    step = guide.steps[current_step_index]
    steps_context = "\n".join(
        f"Step {s.index + 1}: {s.title} — {s.content}" for s in guide.steps
    )
    return (
        f"Guide: {guide.title}\n"
        f"Current step: Step {step.index + 1} of {len(guide.steps)}\n"
        f"Step title: {step.title}\n"
        f"Step content: {step.content}\n\n"
        f"All steps:\n{steps_context}"
    )
