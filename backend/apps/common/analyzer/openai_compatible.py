"""OpenAI-compatible chat completions analyzer (opt-in).

Enabled with ANALYZER_BACKEND=openai_compatible plus AI_BASE_URL / AI_API_KEY /
AI_MODEL. Uses only the standard library so no extra dependency is required.
The response is validated against AIAssessment; invalid ids are dropped later
by the service layer.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings

from .base import AIAssessment, AIWritingNote, Analyzer, EvidenceCandidate
from .prompts import build_claim_messages


class OpenAICompatibleAnalyzer(Analyzer):
    name = "openai_compatible"
    version = "1.0.0"

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.AI_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.AI_API_KEY
        self.model = model or settings.AI_MODEL
        if not (self.base_url and self.api_key and self.model):
            raise RuntimeError("openai_compatible analyzer requires AI_BASE_URL, AI_API_KEY and AI_MODEL")

    def _chat(self, messages: list[dict]) -> dict:
        payload = json.dumps(
            {"model": self.model, "messages": messages, "temperature": 0, "response_format": {"type": "json_object"}}
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            body = json.loads(resp.read().decode())
        return json.loads(body["choices"][0]["message"]["content"])

    def assess_claim(self, *, claim_text: str, candidates: list[EvidenceCandidate]) -> AIAssessment:
        try:
            data = self._chat(build_claim_messages(claim_text, candidates))
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"analyzer request failed: {exc}") from exc
        return AIAssessment.model_validate(data)

    def review_writing(self, *, text: str) -> list[AIWritingNote]:
        return []
