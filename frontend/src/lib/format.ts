import type { DocumentStatus, FindingStatus } from "../api/types";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

const DOC_TONES: Record<DocumentStatus, string> = {
  uploaded: "neutral",
  validating: "info",
  extracting: "info",
  ocr: "info",
  chunking: "info",
  embedding: "info",
  ready: "positive",
  failed: "danger",
  unsupported: "warning",
  empty: "warning",
};

export function documentTone(status: DocumentStatus): "neutral" | "positive" | "warning" | "danger" | "info" {
  return (DOC_TONES[status] ?? "neutral") as "neutral" | "positive" | "warning" | "danger" | "info";
}

const FINDING_TONES: Record<FindingStatus, string> = {
  supported: "positive",
  partially_supported: "warning",
  unsupported_by_sources: "neutral",
  conflicts_with_sources: "danger",
  citation_issue: "warning",
};

export function findingTone(status: FindingStatus): "neutral" | "positive" | "warning" | "danger" | "info" {
  return (FINDING_TONES[status] ?? "neutral") as "neutral" | "positive" | "warning" | "danger" | "info";
}

export function isProcessing(status: DocumentStatus): boolean {
  return ["uploaded", "validating", "extracting", "ocr", "chunking", "embedding"].includes(status);
}

export function confidenceLabel(value: number): string {
  if (value >= 0.8) return "High";
  if (value >= 0.6) return "Medium";
  return "Low";
}
