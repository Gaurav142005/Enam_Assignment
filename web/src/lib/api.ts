// Server components call the API directly; the browser goes through the /api rewrite (next.config.ts).
const SERVER_BASE = process.env.API_URL ?? "http://localhost:8000";

export class ApiError extends Error {}

export async function api<T>(path: string): Promise<T> {
  const base = typeof window === "undefined" ? SERVER_BASE : "/api";
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, { cache: "no-store" });
  } catch {
    throw new ApiError("FINN's backend isn't reachable. Start it with `make api`.");
  }
  if (!res.ok) throw new ApiError(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(`${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function detail(res: Response, path: string): Promise<never> {
  let msg = `${path} → ${res.status}`;
  try {
    const body = await res.json();
    if (typeof body.detail === "string") msg = body.detail;
  } catch {}
  throw new ApiError(msg);
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) return detail(res, path);
  return res.json() as Promise<T>;
}

export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`/api${path}`, { method: "POST", body: form });
  if (!res.ok) return detail(res, path);
  return res.json() as Promise<T>;
}

export async function apiDelete(path: string): Promise<unknown> {
  const res = await fetch(`/api${path}`, { method: "DELETE" });
  if (!res.ok) return detail(res, path);
  return res.status === 204 ? null : res.json();
}
