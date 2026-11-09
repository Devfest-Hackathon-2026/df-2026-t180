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
  /** Sent back when editing, so the server can refuse if the rule changed meanwhile. */
  version: string;
};

type ApiRule = {
  id: string;
  region: string;
  statement: Localised;
  updated_at: string;
  last_reviewed_at?: string | null;
  version: string;
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
  current?: {
    statement: Localised;
    updated_at: string;
    last_reviewed_at?: string | null;
    version: string;
  } | null;
};

const toRule = (rule: ApiRule): AdminRule => ({
  id: rule.id,
  region: rule.region,
  statement: rule.statement,
  updatedAt: rule.updated_at,
  lastReviewedAt: rule.last_reviewed_at ?? undefined,
  version: rule.version,
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
        version: c.current.version,
      }
    : undefined,
});

/** Candidates waiting for a decision, with their post and the rule they would change. */
export async function listCandidates(): Promise<Candidate[]> {
  return (await request<ApiCandidate[]>("/api/admin/candidates")).map(toCandidate);
}

/**
 * Approve (optionally with edited text) or reject. Returns the decided candidate and, when a
 * rule was created or changed, that rule.
 *
 * Approving an update or review sends the version of the rule the admin was looking at
 * (candidate.current.version). If the rule changed since, the server answers 409 and saves nothing.
 */
export async function decideCandidate(
  candidate: Pick<Candidate, "id" | "current">,
  action: "approve" | "reject",
  statement?: Localised,
): Promise<{ candidate: Candidate; rule?: AdminRule }> {
  const expectedVersion = action === "approve" ? candidate.current?.version : undefined;
  const result = await request<{ candidate: ApiCandidate; rule?: ApiRule | null }>(
    `/api/admin/candidates/${encodeURIComponent(candidate.id)}`,
    {
      method: "PATCH",
      body: JSON.stringify({
        action,
        ...(statement ? { statement } : {}),
        ...(expectedVersion ? { expected_version: expectedVersion } : {}),
      }),
    },
  );
  return {
    candidate: toCandidate(result.candidate),
    rule: result.rule ? toRule(result.rule) : undefined,
  };
}

export async function listRules(): Promise<AdminRule[]> {
  return (await request<ApiRule[]>("/api/admin/rules")).map(toRule);
}

/** Edit a rule's text. 409 if it changed since expectedVersion was loaded; nothing is saved. */
export async function editRule(
  id: string,
  statement: Localised,
  expectedVersion: string,
): Promise<AdminRule> {
  return toRule(
    await request<ApiRule>(`/api/admin/rules/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ statement, expected_version: expectedVersion }),
    }),
  );
}
