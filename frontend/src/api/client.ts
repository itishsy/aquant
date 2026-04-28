const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`);
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return response.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Admin-Token": "dev-admin-token" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return response.json();
}

export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return response.json();
}

export async function apiDelete<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`API ${response.status}`);
  }
  return response.json();
}
