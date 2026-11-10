import type { Lang } from "./types";

export type Params = Record<string, string | undefined>;

/** Builds a link to `path`, carrying over params and dropping any set to undefined. */
export function href(path: string, current: Params = {}, patch: Params = {}) {
  const merged = { ...current, ...patch };
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(merged)) {
    if (value) query.set(key, value);
  }
  const text = query.toString();
  return text ? `${path}?${text}` : path;
}

export const readLang = (params: Params): Lang => (params.lang === "en" ? "en" : "ja");

/** Only the language follows the visitor between screens. */
export const langOnly = (params: Params): Params => ({ lang: params.lang });
