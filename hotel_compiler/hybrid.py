"""Independent Pattern-grammar / VADER–TextBlob hybrid with auditable evidence.

No baseline parser, vocabulary, sense selection, or scoring is used here.
"""
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from hashlib import sha256
from importlib import metadata, resources
from math import fsum, isfinite

from uuid import uuid4

from .hybrid_nlp import (MAX_REVIEW_LENGTH, NLPAnalysis, NLPDiagnostic,
                         analyze_language, domain_adjustment, prepare_text)
from .sentiment_policy import DEFAULT_POLICY, SentimentPolicy, overall_polarity
from .hybrid_vocabulary import vocabulary, has_alias, normalize_opinions


class HybridDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class HybridPolicy:
    vader_weight: float = 0.5
    bands: SentimentPolicy = DEFAULT_POLICY

    def __post_init__(self):
        if (isinstance(self.vader_weight, bool) or not isinstance(self.vader_weight, (int, float))
                or not isfinite(self.vader_weight) or not 0 < self.vader_weight < 1):
            raise ValueError('Hybrid weight must be finite and strictly between 0 and 1; both tools are used.')
        if not isinstance(self.bands, SentimentPolicy):
            raise TypeError('bands must be a SentimentPolicy.')


@dataclass(frozen=True)
class HybridEvidence:
    text: str
    score: float | None
    polarity: str
    strength: str
    status: str
    vader_compound: float | None
    vader_positive: float | None
    vader_neutral: float | None
    vader_negative: float | None
    textblob_polarity: float | None
    textblob_subjectivity: float | None
    textblob_assessments: tuple
    vader_has_evidence: bool
    textblob_has_evidence: bool
    component_disagreement: bool
    errors: tuple[str, ...]
    fusion_rule: str = 'weighted_both'
    lexical_fusion_score: float | None = None
    domain_rule_id: str | None = None
    domain_matched_text: str | None = None
    vocabulary_normalization: dict | None = None


class HybridEngine:
    def __init__(self, policy: HybridPolicy | None = None):
        self.policy = policy or HybridPolicy()
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            from textblob.sentiments import PatternAnalyzer
            from textblob.parsers import PatternParser
            from textblob.en import sentiment as pattern_lexicon
        except ImportError as error:
            raise HybridDependencyError('Install research dependencies: python -m pip install -e ".[research]"') from error
        self.vader = SentimentIntensityAnalyzer()
        self.textblob = PatternAnalyzer()
        self.parser = PatternParser()
        self.pattern_lexicon = pattern_lexicon
        self.versions = {name: metadata.version(name) for name in ('vaderSentiment', 'textblob', 'nltk')}
        self.lexicon_hashes = {
            'vader_lexicon': sha256(resources.files('vaderSentiment').joinpath('vader_lexicon.txt').read_bytes()).hexdigest(),
            'textblob_lexicon': sha256(resources.files('textblob.en').joinpath('en-sentiment.xml').read_bytes()).hexdigest(),
            **{name:sha256(resources.files('textblob.en').joinpath(name).read_bytes()).hexdigest()
               for name in ('en-lexicon.txt','en-context.txt','en-morphology.txt','en-entities.txt')},
            'hybrid_domain':sha256(resources.files('hotel_compiler').joinpath('resources/hybrid_domain.json').read_bytes()).hexdigest(),
            'hybrid_vocabulary':sha256(resources.files('hotel_compiler').joinpath('resources/hybrid_vocabulary.json').read_bytes()).hexdigest(),
        }
        # Validate every canonical against native evidence, without learning or
        # importing the baseline vocabulary. Explicit unsupported words remain
        # unavailable rather than receiving invented scores.
        for canonical in {s['canonical'] for s in vocabulary()['lexical_aliases'].values()}:
            if self._score_native(canonical).status != 'scored':
                raise ValueError(f'Hybrid vocabulary canonical has no native sentiment evidence: {canonical}')

    def has_lexical(self, word: str) -> bool:
        return self.has_native_lexical(word) or has_alias(word)

    def has_native_lexical(self, word: str) -> bool:
        return (word in self.vader.lexicon or word in self.pattern_lexicon or
                any(part in self.vader.lexicon for part in self.vader.emojis.get(word,'').split()))

    def score_text(self, text: str, *, category: str | None = None) -> HybridEvidence:
        original = self._score_native(text)
        if original.status == 'processing_error': return original
        working, matches = normalize_opinions(text, category, self.has_native_lexical)
        if not matches: return original
        effective = self._score_native(working)
        return replace(effective, text=text, vocabulary_normalization={
            'version': vocabulary()['version'], 'scoring_text': working,
            'matches': matches, 'original_evidence': asdict(original),
            'scope': 'Scoring copy only; original text, grammar spans and lexical resources unchanged.',
        })

    def _score_native(self, text: str) -> HybridEvidence:
        if not isinstance(text, str):
            raise TypeError('Review text must be a string.')
        if len(text) > MAX_REVIEW_LENGTH:
            raise ValueError(f'At most {MAX_REVIEW_LENGTH} characters are supported.')
        v = t = None
        errors = []
        try:
            v = self.vader.polarity_scores(text)
            for key in ('compound', 'pos', 'neu', 'neg'):
                if not isfinite(v[key]) or not (-1 <= v[key] <= 1):
                    raise ValueError('Invalid VADER output.')
        except Exception as error:
            v = None
            errors.append(f'VADER: {type(error).__name__}: {error}')
        try:
            # Pattern's contraction tokenizer can split n't incorrectly. This
            # working copy preserves casing/punctuation and the original text.
            working,_ = prepare_text(text)
            t = self.textblob.analyze(working, keep_assessments=True)
            if not isfinite(t.polarity) or not -1 <= t.polarity <= 1 or not 0 <= t.subjectivity <= 1:
                raise ValueError('Invalid TextBlob output.')
        except Exception as error:
            t = None
            errors.append(f'TextBlob: {type(error).__name__}: {error}')
        ve = bool(v and (v['pos'] > 0 or v['neg'] > 0))
        te = bool(t and t.assessments)
        status = 'processing_error' if errors else 'scored' if ve or te else 'no_lexical_evidence'
        # Do not dilute lexical evidence with a tool that found no sentiment.
        # Both tools still run; a component exception remains an error.
        fusion_rule = 'weighted_both' if ve and te else 'vader_evidence_only' if ve else 'textblob_evidence_only' if te else 'unavailable'
        score = (round(self.policy.vader_weight*v['compound']+(1-self.policy.vader_weight)*t.polarity,6)
                 if ve and te else round(v['compound'],6) if ve else round(t.polarity,6) if te else None)
        if status != 'scored':
            score=None
            if errors:fusion_rule='component_error'
        bands = self.policy.bands
        return HybridEvidence(
            text, score, bands.polarity(score), bands.strength(score), status,
            v['compound'] if v else None, v['pos'] if v else None,
            v['neu'] if v else None, v['neg'] if v else None,
            t.polarity if t else None, t.subjectivity if t else None,
            tuple((tuple(a[0]), a[1], a[2], a[3]) for a in t.assessments) if t else (),
            ve, te, bool(ve and te and bands.polarity(v['compound']) != bands.polarity(t.polarity)), tuple(errors),
            fusion_rule, score,
        )

    def score_aspect(self, text: str, category: str) -> HybridEvidence:
        evidence=self.score_text(text, category=category)
        rule=domain_adjustment(category,text)
        if not rule or evidence.status=='processing_error':return evidence
        score=rule['score'];bands=self.policy.bands
        return replace(evidence,score=score,polarity=bands.polarity(score),strength=bands.strength(score),
                       status='scored',fusion_rule='contextual_domain_rule',
                       domain_rule_id=rule['rule_id'],domain_matched_text=rule['matched'])


@lru_cache(maxsize=1)
def default_engine() -> HybridEngine:
    return HybridEngine()


@dataclass(frozen=True)
class HybridAspect:
    category: str
    issue: str
    opinion_expression: str
    start: int
    end: int
    evidence: HybridEvidence
    context_scope: str = 'independent grammatical aspect context; original casing and punctuation'
    aspect_term: str = ''
    aspect_start: int = 0
    aspect_end: int = 0
    grammar_pattern: str = ''
    inherited: bool = False

    @property
    def score(self):
        return self.evidence.score

    @property
    def polarity(self):
        return self.evidence.polarity


@dataclass(frozen=True)
class HybridAnalysis:
    review_id: str
    aspect_analysis_status: str
    records: tuple[HybridAspect, ...]
    whole_text: HybridEvidence
    review_text: str = ''
    language: NLPAnalysis | None = None
    diagnostics: tuple[NLPDiagnostic, ...] = ()

    @property
    def aspect_mean_score(self):
        # Missing aspect scores must not silently become a healthy partial mean.
        if not self.records or any(r.score is None for r in self.records):
            return None
        return round(fsum(r.score for r in self.records) / len(self.records), 6)

    @property
    def overall(self):
        return overall_polarity(r.polarity for r in self.records)

    def to_dict(self):
        result = asdict(self)
        result.update(aspect_mean_score=self.aspect_mean_score, overall=self.overall)
        return result


def analyze_hybrid_review(text: str, review_id: str | None = None, *,
                          compiled=None,
                          engine: HybridEngine | None = None) -> HybridAnalysis:
    if not isinstance(text,str):raise TypeError('Review text must be a string.')
    if len(text)>MAX_REVIEW_LENGTH:raise ValueError(f'At most {MAX_REVIEW_LENGTH} characters are supported.')
    if review_id is not None and (not isinstance(review_id,str) or not review_id.strip()):
        raise ValueError('Review ID must be a nonempty string.')
    # Compatibility only: validate identity, never read baseline analysis fields.
    if compiled is not None and (compiled.review_text != text or (review_id is not None and compiled.review_id != review_id)):
        raise ValueError('The supplied compiler result must refer to the same review.')
    identifier=review_id or (compiled.review_id if compiled is not None else str(uuid4()))
    engine = engine or default_engine()
    try:
        language=analyze_language(text,engine.parser,engine.has_lexical)
    except Exception as error:
        # Preserve per-review failures as failures; never manufacture neutrality.
        diagnostic=NLPDiagnostic('LANGUAGE_PROCESSING_ERROR',f'{type(error).__name__}: {error}',0,len(text))
        language=NLPAnalysis((),(),(),(),(diagnostic,))
        return HybridAnalysis(identifier,'processing_error',(),engine.score_text(text),text,language,(diagnostic,))
    records=[];diagnostics=list(language.diagnostics)
    for candidate in language.candidates:
        evidence=engine.score_aspect(candidate.context,candidate.category)
        records.append(HybridAspect(candidate.category,
                       evidence.domain_rule_id or 'General',candidate.context,candidate.start,candidate.end,evidence,
                       aspect_term=candidate.aspect,aspect_start=candidate.aspect_start,aspect_end=candidate.aspect_end,
                       grammar_pattern=candidate.pattern,inherited=candidate.inherited))
        if evidence.status!='scored':diagnostics.append(NLPDiagnostic(evidence.status.upper(),
            'Attached aspect context has no usable sentiment score.',candidate.start,candidate.end,'hybrid_sentiment'))
    scored=sum(r.score is not None for r in records)
    status=('processing_error' if any(r.evidence.status=='processing_error' for r in records) else
            'complete' if records and not diagnostics else 'partial' if scored else 'unsupported')
    return HybridAnalysis(identifier,status,tuple(records),engine.score_text(text),text,language,tuple(diagnostics))
