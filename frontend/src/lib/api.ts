// frontend/src/lib/api.ts
export const API_BASE =
  process.env.REACT_APP_API_BASE || "http://localhost:8000";

export async function pingBackend() {
  const res = await fetch(`${API_BASE}/hello`);
  if (!res.ok) throw new Error("Backend not reachable");
  return res.json();
}
