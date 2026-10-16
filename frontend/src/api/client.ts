import type { ApiError } from "./types";

const BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class RequestError extends Error {
  status: number;
  code: string;
  detail?: unknown;

  constructor(status: number, error: ApiError) {
    super(error.message);
    this.status = status;
    this.code = error.code;
    this.detail = error.detail;
  }
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
}

type Options = {
  method?: string;
  body?: unknown;
  isForm?: boolean;
  signal?: AbortSignal;
};

export async function request<T>(path: string, options: Options = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = { Accept: "application/json" };

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    if (options.isForm) {
      body = options.body as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }
  }

  if (method !== "GET" && method !== "HEAD") {
    const token = getCookie("csrftoken");
    if (token) headers["X-CSRFToken"] = token;
  }

  const response = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body,
    credentials: "include",
    signal: options.signal,
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("Content-Type") ?? "";
  if (!response.ok) {
    if (contentType.includes("application/json")) {
      const data = await response.json();
      const error: ApiError = data?.error ?? { code: "error", message: "Request failed." };
      throw new RequestError(response.status, error);
    }
    throw new RequestError(response.status, { code: "error", message: response.statusText });
  }

  if (contentType.includes("application/json")) {
    return (await response.json()) as T;
  }
  return (await response.text()) as unknown as T;
}

export async function requestBlob(path: string): Promise<Blob> {
  const response = await fetch(`${BASE}${path}`, { credentials: "include" });
  if (!response.ok) {
    throw new RequestError(response.status, { code: "error", message: "Download failed." });
  }
  return response.blob();
}

/** Upload with progress reporting. Returns the parsed JSON response. */
export function uploadWithProgress<T>(
  path: string,
  form: FormData,
  onProgress: (percent: number) => void,
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE}${path}`);
    xhr.withCredentials = true;
    const token = getCookie("csrftoken");
    if (token) xhr.setRequestHeader("X-CSRFToken", token);
    xhr.setRequestHeader("Accept", "application/json");

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch {
          resolve(undefined as T);
        }
      } else {
        let error: ApiError = { code: "error", message: "Upload failed." };
        try {
          error = JSON.parse(xhr.responseText)?.error ?? error;
        } catch {
          /* keep default */
        }
        reject(new RequestError(xhr.status, error));
      }
    };
    xhr.onerror = () => reject(new RequestError(0, { code: "network", message: "Network error during upload." }));
    xhr.send(form);
  });
}
