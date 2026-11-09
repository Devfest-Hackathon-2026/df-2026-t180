import type { Candidate } from "@/content/admin";
import type { Localised } from "@/content/types";
import { idToken } from "./adminAuth";

/**
 * Client for the admin API (機能D). Calls go to /api on the same address: in development Vite
 * forwards them to the FastAPI server (see vite.config.ts), in production Firebase Hosting can do
 * the same. VITE_API_BASE_URL points elsewhere if needed.
 */
const base = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "").replace(/\/$/, "");

/** status is the HTTP status, or 0 when the server couldn't be reached. */
export class AdminApiError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`Admin API error ${status}`);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await idToken();
  if (!token) throw new AdminApiError(401);
  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
      },
    });
  } catch {
    // Server unreachable.
    throw new AdminApiError(0);
  }
  if (!response.ok) throw new AdminApiError(response.status);
  return (await response.json()) as T;
}

/** A published rule as the admin API returns it (no category or place yet). */
export type AdminRule = {
  id: string;
  region: string;
  statement: Localised;
  updatedAt: string;
  lastReviewedAt?: string;
};

type ApiRule = {
  id: string;
  region: string;
  statement: Localised;
  updated_at: string;
  last_reviewed_at?: string | null;
};

type ApiCandidate = {
  id: string;
  source: "post" | "stale_rule";
  post_id?: string | null;
  region: string;
  statement: Localised;
  status: Candidate["status"];
  type: Candidate["type"];
  target_rule_id?: string | null;
  review_reason?: string | null;
  post?: { text: string; reason?: string | null; created_at: string } | null;
  current?: { statement: Localised; updated_at: string; last_reviewed_at?: string | null } | null;
};

const toRule = (rule: ApiRule): AdminRule => ({
  id: rule.id,
  region: rule.region,
  statement: rule.statement,
  updatedAt: rule.updated_at,
  lastReviewedAt: rule.last_reviewed_at ?? undefined,
});

const toCandidate = (c: ApiCandidate): Candidate => ({
  id: c.id,
  source: c.source,
  postId: c.post_id ?? undefined,
  region: c.region,
  type: c.type,
  status: c.status,
  statement: c.statement,
  targetRuleId: c.target_rule_id ?? undefined,
  reviewReason: c.review_reason ?? undefined,
  post: c.post
    ? { text: c.post.text, reason: c.post.reason ?? undefined, createdAt: c.post.created_at }
    : undefined,
  current: c.current
    ? {
        statement: c.current.statement,
        updatedAt: c.current.updated_at,
        lastReviewedAt: c.current.last_reviewed_at ?? undefined,
      }
    : undefined,
});

/** Candidates waiting for a decision, with their post and the rule they would change. */
export async function listCandidates(): Promise<Candidate[]> {
  return (await request<ApiCandidate[]>("/api/admin/candidates")).map(toCandidate);
}

/** Approve (optionally with edited text) or reject. Returns the decided candidate. */
export async function decideCandidate(
  id: string,
  action: "approve" | "reject",
  statement?: Localised,
): Promise<Candidate> {
  const result = await request<{ candidate: ApiCandidate }>(
    `/api/admin/candidates/${encodeURIComponent(id)}`,
    { method: "PATCH", body: JSON.stringify({ action, ...(statement ? { statement } : {}) }) },
  );
  return toCandidate(result.candidate);
}

export async function listRules(): Promise<AdminRule[]> {
  return (await request<ApiRule[]>("/api/admin/rules")).map(toRule);
}

export async function editRule(id: string, statement: Localised): Promise<AdminRule> {
  return toRule(
    await request<ApiRule>(`/api/admin/rules/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ statement }),
    }),
  );
}
