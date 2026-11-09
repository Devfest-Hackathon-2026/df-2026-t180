/**
 * Resident posts (機能A): POST /api/posts. No sign-in needed. Like the admin API, calls go to /api
 * on the same address (Vite forwards them in development; see vite.config.ts).
 *
 * The chosen map location is not sent yet: the backend Post has no location field while #15 is on
 * hold, and it rejects unknown fields.
 */
const base = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "").replace(/\/$/, "");

export type NewPost = { region: string; text: string; reason?: string };

/** Sends a post and returns its ID; throws if the server rejects it or can't be reached. */
export async function sendPost(post: NewPost): Promise<string> {
  const body: NewPost = { region: post.region, text: post.text.trim() };
  if (post.reason?.trim()) body.reason = post.reason.trim();
  const response = await fetch(`${base}/api/posts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`POST /api/posts failed: ${response.status}`);
  return ((await response.json()) as { id: string }).id;
}
