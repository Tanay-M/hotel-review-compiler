"""Evaluate controlled opinion senses using genuine SentiWordNet 3.0 data."""

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

from .models import AspectResult, ScoreEvidence, SemanticRecord
from .vocabulary import load_vocabulary
from .compiler_profiles import current_profile, compiler_profile


class ResourceError(RuntimeError):
    """A required lexical resource is missing or inconsistent."""


@dataclass(frozen=True)
class SentiSynset:
    positive: float
    negative: float
    terms: tuple[str, ...]
    gloss: str


@lru_cache(maxsize=2)
def _load_synsets(profile) -> dict[str, SentiSynset]:
    resource_dir = files("hotel_compiler").joinpath("resources")
    try:
        suffix = '_expanded' if profile == 'expanded' else ''
        data = resource_dir.joinpath(f'sentiwordnet{suffix}.tsv').read_bytes()
        provenance = json.loads(resource_dir.joinpath(f'provenance{suffix}.json').read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ResourceError("The packaged SentiWordNet resource is missing or unreadable.") from error
    if hashlib.sha256(data).hexdigest() != provenance["subset_sha256"]:
        raise ResourceError("SentiWordNet checksum mismatch. Restore or regenerate the packaged resource.")
    synsets: dict[str, SentiSynset] = {}
    for line in data.decode("utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        pos, offset, positive, negative, terms, gloss = line.split("\t", 5)
        synsets[f"{pos}:{offset}"] = SentiSynset(
            float(positive), float(negative), tuple(terms.split()), gloss
        )
    try:
        with compiler_profile(profile):
            vocabulary = load_vocabulary()
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise ResourceError("The controlled vocabulary is missing or inconsistent.") from error
    for term, spec in vocabulary["opinions"].items():
        for selected in [spec, *spec.get("category_senses", {}).values()]:
            sense = synsets.get(selected["synset"])
            if sense is None or spec.get('source_lemma', term) not in {t.rsplit("#", 1)[0] for t in sense.terms}:
                raise ResourceError(f"Missing or mismatched SentiWordNet sense for {term!r}.")
    return synsets


def load_synsets() -> dict[str, SentiSynset]:
    return _load_synsets(current_profile())


load_synsets.cache_clear = _load_synsets.cache_clear
load_synsets.__wrapped__ = lambda: _load_synsets.__wrapped__(current_profile())


def evaluate(semantic: SemanticRecord, review_id: str) -> AspectResult:
    vocabulary = load_vocabulary()
    opinion_spec = vocabulary["opinions"][semantic.opinion_term]
    context = opinion_spec.get("category_senses", {}).get(semantic.category, {})
    sense_id = context.get("synset", opinion_spec["synset"])
    sense = load_synsets()[sense_id]
    lexical_score = sense.positive - sense.negative
    calibrations = opinion_spec.get("calibration", {})
    domain_score = context.get("calibration", calibrations.get(semantic.category, lexical_score))
    reason = context.get("reason") if "calibration" in context else opinion_spec.get("calibration_reason") if semantic.category in calibrations else None
    if context and "calibration" not in context:
        # A different sense does not inherit a calibration derived for the default sense.
        domain_score, reason = lexical_score, None
    negation_multiplier = -1 if semantic.negated else 1
    raw_score = domain_score * semantic.intensity_multiplier * negation_multiplier
    final_score = round(max(-1.0, min(1.0, raw_score)), 6)
    threshold = vocabulary["neutral_threshold"]
    polarity = "Positive" if final_score > threshold else "Negative" if final_score < -threshold else "Neutral"
    evidence = ScoreEvidence(
        synset=sense_id, gloss=sense.gloss,
        positive_score=sense.positive, negative_score=sense.negative,
        objective_score=1.0 - sense.positive - sense.negative,
        lexical_score=lexical_score, domain_score=domain_score,
        calibration_reason=reason, intensity_multiplier=semantic.intensity_multiplier,
        negation_multiplier=negation_multiplier, unclipped_score=raw_score,
        final_score=final_score,
        normalization_rule=semantic.normalization_rule,
        domain_rule_id=context.get("rule_id", opinion_spec.get("calibration_rule_id")) if reason else None,
        sense_selection=f"Explicit {semantic.category} sense." if context else opinion_spec.get("sense_selection", "Configured hotel-domain sense."),
    )
    return AspectResult(
        review_id=review_id, category=semantic.category, issue=semantic.issue,
        aspect_term=semantic.aspect_term, opinion_term=semantic.opinion_term,
        opinion_expression=semantic.opinion_expression, polarity=polarity,
        score=final_score, start=semantic.start, end=semantic.end, evidence=evidence,
    )

