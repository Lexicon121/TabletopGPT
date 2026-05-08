import random
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class DiceResult:
    notation: str
    rolls: list[int]
    modifier: int
    total: int


_DICE_RE = re.compile(r"^(?:(\d+))?d(\d+)([+-]\d+)?$")


def roll(notation: str) -> DiceResult:
    cleaned = notation.strip().lower()
    match = _DICE_RE.fullmatch(cleaned)
    if not match:
        raise ValueError("unsupported dice notation")

    count = int(match.group(1) or "1")
    sides = int(match.group(2))
    modifier = int(match.group(3) or "0")
    if count < 1 or count > 20 or sides < 2 or sides > 100:
        raise ValueError("dice count or sides out of range")

    rolls = [random.randint(1, sides) for _ in range(count)]
    return DiceResult(cleaned, rolls, modifier, sum(rolls) + modifier)


def death_save() -> dict:
    result = roll("d20")
    natural = result.rolls[0]
    return {
        "roll": natural,
        "successes": 2 if natural == 20 else int(natural >= 10),
        "failures": 2 if natural == 1 else int(natural < 10),
        "critical_success": natural == 20,
        "critical_failure": natural == 1,
    }
