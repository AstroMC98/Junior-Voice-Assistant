from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.models.session import Session


class StateManager:
    def advance_step(self, session: Session, entry: KnowledgeEntry) -> dict:
        steps = entry.structured_data.get("steps", [])
        current = session.step_state.get("current_step", 0)
        next_step = current + 1
        session.step_state["current_step"] = next_step

        if next_step < len(steps):
            step = steps[next_step]
            action = step.get("action", "") if isinstance(step, dict) else str(step)
            return {"done": False, "step": next_step, "action": action}
        else:
            session.step_state["current_step"] = 0
            session.active_module = None
            return {"done": True, "step": next_step, "action": None}

    def reset(self, session: Session):
        session.step_state = {}
        session.active_module = None
