const FLOW_KEY = "planify_flow_id";
const INVITE_KEY = "planify_invite_token";

export function saveFlowId(flowId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(FLOW_KEY, flowId);
}

export function loadFlowId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(FLOW_KEY);
}

export function clearFlowId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(FLOW_KEY);
}

export function saveInviteToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(INVITE_KEY, token);
}

export function loadInviteToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(INVITE_KEY);
}

export function clearInviteToken() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(INVITE_KEY);
}

export async function resolveFlowId() {
  const existing = loadFlowId();
  if (existing) return existing;
  try {
    const res = await fetch("/api/signup/status");
    if (!res.ok) return null;
    const data = (await res.json()) as { flowId?: string } | null;
    if (data?.flowId) {
      saveFlowId(data.flowId);
      return data.flowId;
    }
  } catch {
    return null;
  }
  return null;
}
