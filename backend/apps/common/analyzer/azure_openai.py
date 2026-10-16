"""Azure OpenAI analyzer (opt-in).

Enabled with ANALYZER_BACKEND=azure_openai plus AZURE_OPENAI_ENDPOINT and
AZURE_OPENAI_DEPLOYMENT. Authenticates with a managed identity by default;
set AI_API_KEY to use an API key instead.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from django.conf import settings

from .base import AIAssessment, AIWritingNote, Analyzer, EvidenceCandidate
from .prompts import build_claim_messages


class AzureOpenAIAnalyzer(Analyzer):
    name = "azure_openai"
    version = "1.0.0"

    def __init__(self, endpoint: str | None = None, deployment: str | None = None, api_version: str | None = None):
        self.endpoint = (endpoint or settings.AZURE_OPENAI_ENDPOINT).rstrip("/")
        self.deployment = deployment or settings.AZURE_OPENAI_DEPLOYMENT
        self.api_version = api_version or settings.AZURE_OPENAI_API_VERSION
        if not (self.endpoint and self.deployment):
            raise RuntimeError("azure_openai analyzer requires AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT")

    def _token(self) -> str:
        if settings.AI_API_KEY:
            return settings.AI_API_KEY
        from azure.identity import DefaultAzureCredential

        cred = DefaultAzureCredential()
        return cred.get_token("https://cognitiveservices.azure.com/.default").token

    def _chat(self, messages: list[dict]) -> dict:
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )
        payload = json.dumps(
            {"messages": messages, "temperature": 0, "response_format": {"type": "json_object"}}
        ).encode()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Authorization": f"Bearer {self._token()}", "Content-Type": "application/json"},
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
