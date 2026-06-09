import type { ApiRow, Incident, Tool, User } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function getToken() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem("incident_agent_token") ?? "";
}

export function setToken(token: string) {
  window.localStorage.setItem("incident_agent_token", token);
}

export function clearToken() {
  window.localStorage.removeItem("incident_agent_token");
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(String(detail.detail ?? response.statusText));
  }
  return response.json() as Promise<T>;
}

export async function login(email: string, password: string) {
  const result = await apiFetch<{ access_token: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
  setToken(result.access_token);
  return result.user;
}

export const api = {
  me: () => apiFetch<User>("/auth/me"),
  incidents: () => apiFetch<Incident[]>("/incidents"),
  incident: (id: string) => apiFetch<Incident>(`/incidents/${id}`),
  incidentTimeline: (id: string) => apiFetch<ApiRow[]>(`/incidents/${id}/timeline`),
  incidentToolCalls: (id: string) => apiFetch<ApiRow[]>(`/incidents/${id}/tool-calls`),
  incidentApprovals: (id: string) => apiFetch<ApiRow[]>(`/incidents/${id}/approvals`),
  incidentReports: (id: string) => apiFetch<ApiRow[]>(`/incidents/${id}/reports`),
  runbooks: () => apiFetch<ApiRow[]>("/runbooks"),
  tools: () => apiFetch<Tool[]>("/mcp/tools"),
  agentRuns: () => apiFetch<ApiRow[]>("/agent/runs"),
  approvals: () => apiFetch<ApiRow[]>("/approvals"),
  reports: () => apiFetch<ApiRow[]>("/reports"),
  evalsSummary: () => apiFetch<ApiRow>("/evals/summary"),
  adminAnalytics: () => apiFetch<ApiRow>("/admin/analytics"),
  adminObservability: () => apiFetch<ApiRow>("/admin/observability"),
  adminAuditLogs: () => apiFetch<ApiRow[]>("/admin/audit-logs"),
  adminSecurity: () => apiFetch<ApiRow[]>("/admin/security"),
  runAgent: (incidentId: string) =>
    apiFetch<ApiRow>("/agent/run-incident-triage", {
      method: "POST",
      body: JSON.stringify({ incident_id: incidentId })
    }),
  callTool: (name: string, payload: ApiRow) =>
    apiFetch<ApiRow>(`/mcp/tools/${name}`, { method: "POST", body: JSON.stringify(payload) }),
  approve: (id: string) =>
    apiFetch<ApiRow>(`/approvals/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ reviewer_notes: "Approved in local demo UI" })
    }),
  generateReport: (incidentId: string) =>
    apiFetch<ApiRow>("/reports/generate", {
      method: "POST",
      body: JSON.stringify({ incident_id: incidentId })
    }),
  runEvals: () => apiFetch<ApiRow>("/evals/run", { method: "POST", body: JSON.stringify({}) })
};

