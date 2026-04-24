"""PII redaction using Microsoft Presidio (spacy en_core_web_lg backend)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "LOCATION",
]


class PresidioGuard:
    """Wraps AnalyzerEngine + AnonymizerEngine; lazy-initialised on first call."""

    def __init__(self) -> None:
        self._analyzer = None
        self._anonymizer = None
        self._operators = None

    def _load(self) -> None:
        from presidio_analyzer import AnalyzerEngine
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig

        self._analyzer = AnalyzerEngine()
        self._anonymizer = AnonymizerEngine()
        self._operators = {
            e: OperatorConfig("replace", {"new_value": f"[{e}]"}) for e in _ENTITIES
        }

    def redact(self, text: str) -> str:
        if not text.strip():
            return text
        if self._analyzer is None:
            self._load()
        results = self._analyzer.analyze(text=text, language="en", entities=_ENTITIES)
        if not results:
            return text
        anonymized = self._anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=self._operators,
        )
        return anonymized.text
