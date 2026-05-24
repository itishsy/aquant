const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload && typeof payload === "object" && "detail" in payload ? (payload as any).detail : "";
    const message = typeof detail === "string" && detail ? detail : `API ${response.status}`;
    throw new Error(message);
  }
  if (payload && typeof payload === "object" && "success" in payload && "data" in payload) {
    return payload.data as T;
  }
  return payload as T;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  return parseResponse<T>(response);
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Admin-Token": "dev-admin-token" },
    body: body ? JSON.stringify(body) : undefined,
  });
  return parseResponse<T>(response);
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-Admin-Token": "dev-admin-token" },
    body: JSON.stringify(body),
  });
  return parseResponse<T>(response);
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
  return parseResponse<T>(response);
}
