"""Documented descriptive bands; sentiment magnitude is not confidence."""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class SentimentPolicy:
    neutral: float = 0.05
    strong: float = 0.50

    def __post_init__(self):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v)
               for v in (self.neutral, self.strong)) or not 0 <= self.neutral < self.strong <= 1:
            raise ValueError('Require finite boundaries 0 <= neutral < strong <= 1.')

    def polarity(self, score: float | None) -> str:
        if score is None:
            return 'Unanalyzed'
        self._validate(score)
        return 'Positive' if score > self.neutral else 'Negative' if score < -self.neutral else 'Neutral'

    def strength(self, score: float | None) -> str:
        if score is None:
            return 'Unavailable'
        self._validate(score)
        if score <= -self.strong:
            return 'Strong Negative'
        if score < -self.neutral:
            return 'Weak Negative'
        if score <= self.neutral:
            return 'Neutral'
        if score < self.strong:
            return 'Weak Positive'
        return 'Strong Positive'

    @staticmethod
    def _validate(score):
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not isfinite(score) or not -1 <= score <= 1:
            raise ValueError('Sentiment score must be a finite number in [-1,1].')


DEFAULT_POLICY = SentimentPolicy()


def overall_polarity(polarities) -> str:
    labels = set(polarities) - {'Unanalyzed'}
    if {'Positive', 'Negative'} <= labels:
        return 'Mixed'
    for label in ('Positive', 'Negative', 'Neutral'):
        if label in labels:
            return label
    return 'Unanalyzed'
