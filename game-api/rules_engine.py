from dataclasses import asdict

import dice
import security


DEFAULT_ACTION_ROLL = "d20"


def validate_official_action(action_text: str) -> str:
    text = security.clamp_text(action_text, "action_text", 1, 1000)
    security.reject_prompt_injection(text)
    return text


def resolve_action(action_text: str) -> dict:
    """Starter mechanics: every official action gets one server-side d20 roll."""
    validated = validate_official_action(action_text)
    result = dice.roll(DEFAULT_ACTION_ROLL)
    return {
        "action_text": validated,
        "roll": asdict(result),
        "mechanics": {
            "outcome_band": "strong" if result.total >= 15 else "mixed" if result.total >= 8 else "complication"
        },
    }


def health_status(hp: int, max_hp: int) -> str:
    if hp <= -max_hp:
        return "dead"
    if hp <= 0:
        return "dying"
    ratio = hp / max_hp
    if ratio <= 0.25:
        return "critical"
    if ratio <= 0.5:
        return "bloodied"
    if ratio < 1:
        return "wounded"
    return "healthy"
