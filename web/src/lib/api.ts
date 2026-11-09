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
