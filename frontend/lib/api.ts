import type { AuthResponse, Workflow, WorkflowSummary } from "@/lib/types";

const API_BASE = "/api/backend";
const TOKEN_KEY = "eap_access_token";
const ROLE_KEY = "eap_role";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken() {
  return typeof window === "undefined" ? null : localStorage.getItem(TOKEN_KEY);
}

export function getStoredRole() {
  return typeof window === "undefined" ? null : localStorage.getItem(ROLE_KEY);
}

export function storeSession(auth: AuthResponse) {
  localStorage.setItem(TOKEN_KEY, auth.access_token);
  localStorage.setItem(ROLE_KEY, auth.role);
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ROLE_KEY);
}

async function request<T>(path: string, init: RequestInit = {}, authenticated = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (authenticated) {
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers, cache: "no-store" });
  } catch {
    throw new ApiError("Unable to reach the platform API.", 0);
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status}).`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the status-based message for non-JSON errors.
    }
    if (response.status === 401 && authenticated && typeof window !== "undefined") {
      clearSession();
      window.dispatchEvent(new Event("eap:unauthorized"));
    }
    throw new ApiError(detail, response.status);
  }

  return (await response.json()) as T;
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }, false),

  register: (email: string, password: string, fullName?: string) =>
    request<AuthResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name: fullName || null }),
    }, false),

  health: () => request<{ status: string }>("/health", {}, false),

  listWorkflows: () => request<WorkflowSummary[]>("/workflows?limit=100"),

  getWorkflow: (id: string) => request<Workflow>(`/workflows/${encodeURIComponent(id)}`),

  createWorkflow: (workflowRequest: string) =>
    request<Workflow>("/workflows", {
      method: "POST",
      body: JSON.stringify({ request: workflowRequest }),
    }),

  decideWorkflow: (id: string, decision: "approve" | "reject", reason?: string) =>
    request<Workflow>(`/workflows/${encodeURIComponent(id)}/${decision}`, {
      method: "POST",
      body: JSON.stringify({ reason: reason || null }),
    }),
};
