// Client-side helpers. All calls go to the Next proxy at /api/clara/*, which
// forwards to the Clara FastAPI backend (CLARA_API) — the browser never talks to
// the Python backend directly, so there is no CORS to configure.

export async function api<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api/clara/${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    /* non-JSON response */
  }
  const err = (data as { error?: string } | null)?.error;
  if (!res.ok || err) {
    throw new Error(err ?? `HTTP ${res.status}`);
  }
  return data as T;
}

export function toBase64(buffer: ArrayBuffer): string {
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

export async function download(path: string, body: unknown, filename: string): Promise<void> {
  const res = await fetch(`/api/clara/${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      msg = ((await res.json()) as { error?: string }).error ?? msg;
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
