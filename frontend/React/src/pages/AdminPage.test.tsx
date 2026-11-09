import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Localised } from "@/content/types";
import { AdminPage } from "./AdminPage";

// Signed in as an admin with a fixed token; everything else goes through the real admin API
// client to the fake server below.
vi.mock("@/api/adminAuth", () => ({
  adminLive: true,
  idToken: async () => "admin-token",
  currentUser: async () => ({ uid: "admin_uid" }),
  signIn: async () => {},
  signOut: async () => {},
}));

const text = (ja: string): Localised => ({ ja, en: `${ja} (en)` });

/**
 * Stands in for the admin API, with the same version rule: a write must send the version of the
 * rule it was based on, or it gets 409 and nothing changes.
 */
class FakeServer {
  rule = { id: "rule_1", region: "sakai", statement: text("既存のルール"), version: 1 };
  candidates = ["post_1_2", "post_1_5"].map((id, i) => ({
    id,
    source: "post",
    post_id: "post_1",
    region: "sakai",
    statement: text(i === 0 ? "Aの提案" : "Bの提案"),
    status: "pending",
    type: "update",
    target_rule_id: "rule_1",
  }));
  writes: { path: string; body: Record<string, unknown> }[] = [];

  /** Another admin edits the rule outside this screen. */
  editElsewhere(statement: Localised) {
    this.rule = { ...this.rule, statement, version: this.rule.version + 1 };
  }

  private apiRule() {
    return {
      id: this.rule.id,
      region: this.rule.region,
      statement: this.rule.statement,
      updated_at: "2026-11-09T00:00:00Z",
      last_reviewed_at: null,
      version: `v${this.rule.version}`,
    };
  }

  fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const path = String(input);
    const json = (status: number, body: unknown) => new Response(JSON.stringify(body), { status });
    if (!init?.method || init.method === "GET") {
      if (path.startsWith("/api/admin/candidates")) {
        const { statement, version } = this.apiRule();
        return json(
          200,
          this.candidates
            .filter((c) => c.status === "pending")
            .map((c) => ({
              ...c,
              current: { statement, updated_at: "2026-11-09T00:00:00Z", version },
            })),
        );
      }
      return json(200, [this.apiRule()]);
    }

    const body = JSON.parse(String(init.body)) as Record<string, unknown>;
    this.writes.push({ path, body });
    if (body.expected_version !== undefined && body.expected_version !== `v${this.rule.version}`) {
      return json(409, { detail: "rule has changed since it was loaded" });
    }
    if (path.startsWith("/api/admin/candidates/")) {
      const candidate = this.candidates.find((c) => path.endsWith(c.id))!;
      candidate.status = "approved";
      this.rule = {
        ...this.rule,
        statement: candidate.statement,
        version: this.rule.version + 1,
      };
      return json(200, { candidate, rule: this.apiRule() });
    }
    this.rule = {
      ...this.rule,
      statement: body.statement as Localised,
      version: this.rule.version + 1,
    };
    return json(200, this.apiRule());
  };
}

let server: FakeServer;

beforeEach(() => {
  server = new FakeServer();
  vi.stubGlobal("fetch", server.fetch);
  // Only the undo window's timers are faked, so the 5-second wait takes no real time.
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

/** Lets pending requests and timers run (fake time), then applies React updates. */
const wait = (ms = 0) =>
  act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });

async function open(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/admin/:area" element={<AdminPage />} />
        <Route path="/admin" element={<p>sign in</p>} />
      </Routes>
    </MemoryRouter>,
  );
  await wait();
}

const textarea = (name: string) => screen.getByRole("textbox", { name }) as HTMLTextAreaElement;

const approveButtons = () => screen.queryAllByRole("button", { name: "採用" });

describe("approving two candidates for the same rule", () => {
  it("sends the version seen when each was approved, so the second gets 409", async () => {
    await open("/admin/candidates?type=update");
    expect(approveButtons()).toHaveLength(2);

    fireEvent.click(approveButtons()[0]); // A, seen at v1
    await wait(2000);
    fireEvent.click(approveButtons()[0]); // B (now the only 採用 left), also seen at v1
    await wait(3000); // A's undo window ends: A is sent and the rule becomes v2
    expect(server.rule.version).toBe(2);
    await wait(2000); // B's undo window ends

    const [a, b] = server.writes;
    expect(a.body.expected_version).toBe("v1");
    // B was decided against v1: it must not be sent as v2 just because A landed meanwhile.
    expect(b.body.expected_version).toBe("v1");
    expect(server.rule.statement).toEqual(text("Aの提案"));
    expect(server.candidates[1].status).toBe("pending");

    // The admin is told, and B comes back showing A's text as the published one.
    expect(screen.getByRole("alert").textContent).toContain("ほかの管理者が先に変更した");
    expect(approveButtons()).toHaveLength(1);
    screen.getByText("Aの提案");
  });

  it("lets the admin decide again after the reload, against the new version", async () => {
    await open("/admin/candidates?type=update");
    fireEvent.click(approveButtons()[0]);
    await wait(5000);
    fireEvent.click(approveButtons()[0]);
    await wait(5000); // 409, reload

    fireEvent.click(approveButtons()[0]); // decided again, now seeing v2
    await wait(5000);

    expect(server.writes.at(-1)!.body.expected_version).toBe("v2");
    expect(server.candidates[1].status).toBe("approved");
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("editing a rule someone else changed", () => {
  async function editAndHitConflict() {
    await open("/admin/rules");
    fireEvent.click(screen.getByRole("button", { name: /^編集/ }));
    fireEvent.change(screen.getByRole("textbox", { name: "日本語" }), {
      target: { value: "私の下書き" },
    });
    server.editElsewhere(text("別の管理者の文")); // v1 → v2 while this draft is open
    fireEvent.click(screen.getByRole("button", { name: "保存" }));
    await wait();
  }

  it("shows their text and blocks a plain re-save of the old draft", async () => {
    await editAndHitConflict();

    expect(server.writes).toHaveLength(1);
    expect(server.writes[0].body.expected_version).toBe("v1");
    expect(server.rule.statement).toEqual(text("別の管理者の文"));
    expect(screen.getByRole("alert").textContent).toContain("ほかの管理者が先に変更した");

    const latest = screen.getByLabelText("公開中の最新の文");
    within(latest).getByText("別の管理者の文");
    // The draft is kept for comparison, but 保存 is gone until the admin chooses.
    expect(textarea("日本語").value).toBe("私の下書き");
    expect(screen.queryByRole("button", { name: "保存" })).toBeNull();
  });

  it("can start again from their text, then save against the new version", async () => {
    await editAndHitConflict();

    fireEvent.click(screen.getByRole("button", { name: "最新の文で書き直す" }));
    expect(textarea("日本語").value).toBe("別の管理者の文");
    fireEvent.change(screen.getByRole("textbox", { name: "日本語" }), {
      target: { value: "両方を反映した文" },
    });
    fireEvent.click(screen.getByRole("button", { name: "保存" }));
    await wait();

    expect(server.writes.at(-1)!.body).toMatchObject({ expected_version: "v2" });
    expect(server.rule.statement.ja).toBe("両方を反映した文");
    expect(screen.queryByLabelText("公開中の最新の文")).toBeNull();
  });

  it("replaces their text only when the admin explicitly chooses to", async () => {
    await editAndHitConflict();

    fireEvent.click(screen.getByRole("button", { name: "この下書きで上書き" }));
    await wait();

    expect(server.writes.at(-1)!.body).toMatchObject({ expected_version: "v2" });
    expect(server.rule.statement.ja).toBe("私の下書き");
  });

  it("still refuses if it changed again while the admin was choosing", async () => {
    await editAndHitConflict();
    server.editElsewhere(text("さらに別の文")); // v2 → v3, not yet shown on screen

    fireEvent.click(screen.getByRole("button", { name: "この下書きで上書き" }));
    await wait();

    // It sent the version of the text on screen (v2), so nothing was overwritten.
    expect(server.writes.at(-1)!.body).toMatchObject({ expected_version: "v2" });
    expect(server.rule.statement.ja).toBe("さらに別の文");
    within(screen.getByLabelText("公開中の最新の文")).getByText("さらに別の文");
  });
});
