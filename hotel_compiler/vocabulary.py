"""Read the project's controlled vocabulary, without any trained NLP model."""

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


def validate_vocabulary(vocabulary: dict[str, Any]) -> None:
    """Reject inconsistent aliases/domain rules before processing a batch."""
    opinions, aspects = vocabulary["opinions"], vocabulary["aspects"]
    categories = set(vocabulary["categories"])
    for term, spec in opinions.items():
        if not set(spec.get("allowed_aspects", [])) <= set(aspects):
            raise ValueError(f"Unknown allowed aspect for opinion {term!r}.")
        if not set(spec.get("allowed_categories", [])) <= categories:
            raise ValueError(f"Unknown allowed category for opinion {term!r}.")
        calibration = spec.get("calibration", {})
        if not set(calibration) <= categories:
            raise ValueError(f"Unknown calibration category for opinion {term!r}.")
        if calibration and (not spec.get("calibration_reason") or not spec.get("calibration_rule_id")):
            raise ValueError(f"Calibration for {term!r} needs an explicit rule ID and reason.")
        if any(not isinstance(score, (int, float)) or isinstance(score, bool) or not -1 <= score <= 1
               for score in calibration.values()):
            raise ValueError(f"Invalid calibration score for opinion {term!r}.")
        for category, context in spec.get("category_senses", {}).items():
            if category not in categories or not isinstance(context.get("synset"), str):
                raise ValueError(f"Invalid category-specific sense for {term!r}.")
            if "calibration" in context and (
                not isinstance(context["calibration"], (int, float)) or isinstance(context["calibration"], bool)
                or not -1 <= context["calibration"] <= 1 or not context.get("rule_id") or not context.get("reason")
            ):
                raise ValueError(f"Invalid category-specific calibration for {term!r}.")
    for alias, spec in vocabulary.get("opinion_aliases", {}).items():
        if alias in opinions or alias in aspects or spec.get("canonical") not in opinions:
            raise ValueError(f"Invalid canonical opinion alias {alias!r}.")
        if spec.get("kind") not in {"OPINION", "FUNCTION_VERB"}:
            raise ValueError(f"Invalid token kind for alias {alias!r}.")
        if spec["kind"] == "FUNCTION_VERB" and spec.get("verb_form") not in {"base", "finite"}:
            raise ValueError(f"Invalid verb form for alias {alias!r}.")
        if not set(spec.get("allowed_categories", [])) <= categories:
            raise ValueError(f"Unknown allowed category for alias {alias!r}.")
        if not set(spec.get("allowed_aspects", [])) <= set(aspects):
            raise ValueError(f"Unknown allowed aspect for alias {alias!r}.")


@lru_cache(maxsize=1)
def load_vocabulary() -> dict[str, Any]:
    content = files("hotel_compiler").joinpath("resources/domain.json").read_text(
        encoding="utf-8"
    )
    vocabulary = json.loads(content)
    validate_vocabulary(vocabulary)
    return vocabulary

