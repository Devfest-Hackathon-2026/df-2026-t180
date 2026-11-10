import { afterEach, describe, expect, it, vi } from "vitest";
import { sendPost } from "./posts";

afterEach(() => vi.unstubAllGlobals());

/** Sends one post to a fake server and returns the JSON body it received. */
async function sent(post: Parameters<typeof sendPost>[0]) {
  const fetch = vi.fn(async () => new Response(JSON.stringify({ id: "post_1" }), { status: 201 }));
  vi.stubGlobal("fetch", fetch);
  await sendPost(post);
  const [, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
  return JSON.parse(String(init.body)) as Record<string, unknown>;
}

describe("sendPost", () => {
  it("sends the place picked on the map as location", async () => {
    const body = await sent({
      region: "sakai",
      text: "夜は静かに",
      location: { lat: 34.5738, lng: 135.4795 },
    });

    expect(body).toEqual({
      region: "sakai",
      text: "夜は静かに",
      location: { lat: 34.5738, lng: 135.4795 },
    });
  });

  it("leaves location out when no place was picked", async () => {
    const body = await sent({ region: "sakai", text: "夜は静かに" });

    expect(body).toEqual({ region: "sakai", text: "夜は静かに" });
  });
});
