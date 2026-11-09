import { useEffect, useState } from "react";
import { adminLive as apiLive } from "@/api/adminAuth";
import { rules as sampleRules } from "@/content/rules";
import type { Rule } from "@/content/types";

/**
 * A region's published rules for the guide. When the app is connected to the project (Firebase
 * settings in .env), they come from GET /api/regions/{id}/rules (機能C); otherwise the sample
 * rules are used. Rules from the API have no category, place or location yet (#22, #15).
 */
const base = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "").replace(/\/$/, "");

type ApiRule = {
  id: string;
  region: string;
  statement: Rule["statement"];
  updated_at: string;
};

export type RulesStatus = "loading" | "ready" | "failed";

// Kept for the session, so reopening the sheet doesn't fetch again.
const cache = new Map<string, Rule[]>();

async function fetchRules(regionId: string): Promise<Rule[]> {
  const response = await fetch(`${base}/api/regions/${encodeURIComponent(regionId)}/rules`);
  if (!response.ok) throw new Error(`rules ${response.status}`);
  const list = (await response.json()) as ApiRule[];
  return list.map((rule) => ({
    id: rule.id,
    region: rule.region,
    statement: rule.statement,
    // Shown as a date in Japan time.
    updatedAt: new Date(new Date(rule.updated_at).getTime() + 9 * 3600 * 1000)
      .toISOString()
      .slice(0, 10),
  }));
}

export function useRegionRules(regionId: string): { rules: Rule[]; status: RulesStatus } {
  const [loaded, setLoaded] = useState<{ id: string; rules?: Rule[]; failed?: boolean }>();

  useEffect(() => {
    if (!apiLive || cache.has(regionId)) return;
    let cancelled = false;
    fetchRules(regionId)
      .then((list) => {
        cache.set(regionId, list);
        if (!cancelled) setLoaded({ id: regionId, rules: list });
      })
      .catch(() => {
        if (!cancelled) setLoaded({ id: regionId, failed: true });
      });
    return () => {
      cancelled = true;
    };
  }, [regionId]);

  if (!apiLive) {
    return { rules: sampleRules.filter((rule) => rule.region === regionId), status: "ready" };
  }
  const cached = cache.get(regionId);
  if (cached) return { rules: cached, status: "ready" };
  if (loaded?.id === regionId && loaded.failed) return { rules: [], status: "failed" };
  return { rules: [], status: "loading" };
}
