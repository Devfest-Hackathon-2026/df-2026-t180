import { act, cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The built-in placeholder map draws the same pins without loading Google Maps.
vi.hoisted(() => vi.stubEnv("VITE_GOOGLE_MAPS_API_KEY", ""));

// Connected to the project, so rules come from the (fake) API below.
vi.mock("@/api/adminAuth", () => ({ adminLive: true }));

const { HomePage } = await import("./HomePage");

const rule = (
  id: string,
  ja: string,
  location?: { lat: number; lng: number },
  extra: Record<string, unknown> = {},
) => ({
  id,
  region: "sakai",
  statement: { ja, en: `${ja} (en)` },
  updated_at: "2026-11-09T00:00:00Z",
  last_reviewed_at: null,
  location: location ?? null,
  ...extra,
});

beforeEach(() => {
  // The sheet measures itself; the simulated browser has no ResizeObserver.
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      unobserve() {}
      disconnect() {}
    },
  );
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify([
            rule("rule_park", "公園の芝生ではバーベキューをしないでください。", {
              lat: 34.5612,
              lng: 135.4873,
            }),
            rule("rule_area", "ごみは決められた日に出してください。"),
            rule(
              "rule_bus",
              "駅前のバス乗り場は行き先ごとに分かれています。",
              { lat: 34.5753, lng: 135.4832 },
              {
                category: "transport",
                place: { ja: "堺東駅 バス乗り場", en: "Sakai-higashi Sta." },
              },
            ),
          ]),
          { status: 200 },
        ),
    ),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function open(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    </MemoryRouter>,
  );
  await act(async () => {});
}

describe("map pins from published rules", () => {
  it("pins only the rules that have a location, labelled with the rule", async () => {
    await open("/");

    const pin = screen.getByRole("link", {
      name: "公園の芝生ではバーベキューをしないでください。",
    });
    // No category yet (#22): a neutral pin, not a category colour.
    expect(pin.getAttribute("data-category")).toBeNull();
    // The area-wide rule has no pin.
    expect(screen.queryByRole("link", { name: /ごみは決められた日/ })).toBeNull();
  });

  it("opens the sheet for a pin, titled with the area when there is no place name", async () => {
    await open("/?spot=rule_park");

    const sheet = screen.getByRole("region", { name: "堺市" });
    expect(sheet.textContent).toContain("公園の芝生ではバーベキューをしないでください。");
  });
});

describe("category and place from the API (#22)", () => {
  it("colours the pin by category and labels it with the place name", async () => {
    await open("/");

    const pin = screen.getByRole("link", { name: /^堺東駅 バス乗り場/ });
    expect(pin.getAttribute("data-category")).toBe("transport");
  });

  it("counts rules under their category tab in the guide", async () => {
    await open("/?region=sakai&sheet=full");

    const tab = screen.getByRole("link", { name: /^交通/ });
    expect(tab.textContent).toContain("1");
    expect(screen.getByRole("link", { name: /^すべて/ }).textContent).toContain("3");
  });
});
