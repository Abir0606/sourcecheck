from __future__ import annotations

from django.conf import settings

from .base import Analyzer

_analyzer: Analyzer | None = None


def get_analyzer() -> Analyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = _build()
    return _analyzer


def _build() -> Analyzer:
    backend = settings.ANALYZER_BACKEND
    if backend == "azure_openai":
        from .azure_openai import AzureOpenAIAnalyzer

        return AzureOpenAIAnalyzer()
    if backend == "openai_compatible":
        from .openai_compatible import OpenAICompatibleAnalyzer

        return OpenAICompatibleAnalyzer()
    from .rules import RulesAnalyzer

    return RulesAnalyzer()


def reset_analyzer() -> None:
    global _analyzer
    _analyzer = None
