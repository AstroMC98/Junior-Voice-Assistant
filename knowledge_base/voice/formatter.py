from knowledge_base.models.session import Session


class ResponseFormatter:
    def format(self, answer: str, session: Session, confirm_inputs: dict | None = None) -> str:
        urgency = session.urgency
        if urgency == "high":
            return answer.split(".")[0].strip() + "."
        elif urgency == "normal":
            parts = []
            if confirm_inputs:
                recap = ", ".join(f"{k}: {v}" for k, v in confirm_inputs.items())
                parts.append(f"Got it — {recap}.")
            parts.append(answer)
            return " ".join(parts)
        else:  # low / exploratory
            return answer
