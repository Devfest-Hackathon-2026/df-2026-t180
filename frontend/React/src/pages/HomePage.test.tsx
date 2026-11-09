import { act, cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// The built-in placeholder map draws the same pins without loading Google Maps.
vi.hoisted(() => vi.stubEnv("VITE_GOOGLE_MAPS_API_KEY", ""));

// Connected to the project, so rules come from the (fake) API below.
vi.mock("@/api/adminAuth", () => ({ adminLive: true }));

const { HomePage } = await import("./HomePage");

const rule = (id: string, ja: string, location?: { lat: number; lng: number }) => ({
  id,
  region: "sakai",
  statement: { ja, en: `${ja} (en)` },
  updated_at: "2026-11-09T00:00:00Z",
  last_reviewed_at: null,
  location: location ?? null,
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
