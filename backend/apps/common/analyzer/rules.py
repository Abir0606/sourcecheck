"""
Offline, deterministic analyzer.

This is the default (`ANALYZER_BACKEND=rules`). It never contacts the network,
so the application is fully usable without Azure or any AI credentials. It
performs fuzzy string comparison between a claim and already-retrieved evidence
candidates, then maps similarity to a finding status.

It is intentionally conservative: absence of evidence yields
"unsupported_by_sources" (never "false"), with a human-review flag.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from apps.common.constants import FindingStatus, needs_human_review

from .base import AIAssessment, AIWritingNote, Analyzer, EvidenceCandidate

_SUPPORT_THRESHOLD = 0.72
_PARTIAL_THRESHOLD = 0.5
_REFUTE_TOKENS = {"not", "no", "never", "cannot", "isn't", "aren't", "doesn't"}
_NUM_RE = re.compile(r"\b\d[\d,\.]*\b")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _numeric_conflict(claim: str, evidence: str) -> bool:
    claim_nums = set(_NUM_RE.findall(claim))
    ev_nums = set(_NUM_RE.findall(evidence))
    if not claim_nums or not ev_nums:
        return False
    return not (claim_nums & ev_nums)


class RulesAnalyzer(Analyzer):
    name = "rules"
    version = "1.0.0"

    def assess_claim(self, *, claim_text: str, candidates: list[EvidenceCandidate]) -> AIAssessment:
        if not candidates:
            return AIAssessment(
                status=FindingStatus.UNSUPPORTED_BY_SOURCES,
                explanation=(
                    "No matching passage was found in the uploaded sources. This means the "
                    "uploaded sources do not cover this statement; it does not mean the "
                    "statement is false."
                ),
                confidence=0.4,
                cited_evidence_ids=[],
                needs_human_review=True,
            )

        scored = sorted(
            ((c, _similarity(claim_text, c.text)) for c in candidates),
            key=lambda pair: pair[1],
            reverse=True,
        )
        best, score = scored[0]
        conflicting = [c for c, s in scored if s >= 0.4 and _numeric_conflict(claim_text, c.text)]

        if conflicting:
            c = conflicting[0]
            return AIAssessment(
                status=FindingStatus.CONFLICTS_WITH_SOURCES,
                explanation=(
                    "The uploaded source states different figures or facts than this "
                    "statement. Confirm which is correct."
                ),
                confidence=round(min(0.9, 0.5 + score / 2), 2),
                cited_evidence_ids=[c.evidence_id],
                needs_human_review=True,
            )

        if score >= _SUPPORT_THRESHOLD:
            status = FindingStatus.SUPPORTED
            explanation = "A passage in the uploaded sources closely matches this statement."
        elif score >= _PARTIAL_THRESHOLD:
            status = FindingStatus.PARTIALLY_SUPPORTED
            explanation = (
                "The uploaded sources support part of this statement but not all of it."
            )
        else:
            status = FindingStatus.UNSUPPORTED_BY_SOURCES
            explanation = (
                "No passage in the uploaded sources substantially matches this statement. "
                "This does not mean the statement is false."
            )

        cited = [best.evidence_id] if score >= _PARTIAL_THRESHOLD else []
        confidence = round(max(0.3, min(0.95, score)), 2)
        return AIAssessment(
            status=status,
            explanation=explanation,
            confidence=confidence,
            cited_evidence_ids=cited,
            needs_human_review=needs_human_review(status, confidence, has_evidence=bool(cited)),
        )

    def review_writing(self, *, text: str) -> list[AIWritingNote]:
        notes: list[AIWritingNote] = []
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        long_sentences = [s for s in sentences if len(s.split()) > 35]
        if long_sentences:
            notes.append(
                AIWritingNote(
                    category="readability",
                    severity="info",
                    message=f"{len(long_sentences)} sentence(s) exceed 35 words.",
                    suggestion="Split long sentences to improve readability.",
                )
            )
        if re.search(r"\bin order to\b", text, re.I):
            notes.append(
                AIWritingNote(
                    category="clarity",
                    severity="info",
                    message="Consider 'to' instead of 'in order to'.",
                    suggestion="Replace 'in order to' with 'to'.",
                )
            )
        if re.search(r"\butilis", text, re.I):
            notes.append(
                AIWritingNote(
                    category="grammar",
                    severity="info",
                    message="Spelling variant 'utilis...' detected (US: 'utiliz...').",
                    suggestion="Choose one spelling convention consistently.",
                )
            )
        return notes
