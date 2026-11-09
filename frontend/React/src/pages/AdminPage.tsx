import { type CSSProperties, useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import {
  AdminApiError,
  decideCandidate,
  editRule,
  listCandidates,
  listRules,
} from "@/api/adminApi";
import { adminLive, signOut } from "@/api/adminAuth";
import { AdminHeader } from "@/components/AdminHeader";
import { CandidateCard, type Decision } from "@/components/CandidateCard";
import { CategoryIcon } from "@/components/CategoryIcon";
import { Icon } from "@/components/Icon";
import { Mascot } from "@/components/Mascot";
import { StateCard } from "@/components/StateCard";
import { Tag } from "@/components/Tag";
import {
  type Candidate,
  type CandidateType,
  formatJst,
  sampleCandidates,
  ta,
} from "@/content/admin";
import { categories } from "@/content/copy";
import { rules as sampleRules } from "@/content/rules";
import type { Category, Lang, Localised } from "@/content/types";
import { href, readLang, type Params } from "@/content/url";
import styles from "./AdminPage.module.css";

const types: CandidateType[] = ["add", "update", "review"];
const typeLabel = { add: "typeAdd", update: "typeUpdate", review: "typeReview" } as const;
const today = () => new Date().toISOString().slice(0, 10);
/** How long a decision can still be undone before it is sent (live mode). */
const UNDO_MS = 5000;

type Load = "loading" | "ready" | "failed";
/** Why a save didn't happen: an error, or someone else changed the rule first (409). */
type Alert = "saveFailed" | "changed";

const alertFor = (error: unknown): Alert =>
  error instanceof AdminApiError && error.status === 409 ? "changed" : "saveFailed";

/**
 * Admin (機能D): review the candidate queue and edit published rules. With Firebase configured
 * (adminLive) everything goes through the admin API; otherwise it runs on sample data and says so.
 */
export function AdminPage() {
  const { area } = useParams();
  const [searchParams] = useSearchParams();
  const params: Params = Object.fromEntries(searchParams);
  const lang = readLang(params);
  const navigate = useNavigate();
  const view = area === "rules" ? "rules" : "candidates";

  // Kept here so decisions and counts survive switching to 公開ルール and back.
  const [items, setItems] = useState<Candidate[]>(adminLive ? [] : sampleCandidates);
  const [load, setLoad] = useState<Load>(adminLive ? "loading" : "ready");
  const [reload, setReload] = useState(0);
  const [alert, setAlert] = useState<Alert>();
  // Decisions already sent can no longer be undone.
  const [sent, setSent] = useState<ReadonlySet<string>>(new Set());
  const originals = useRef(new Map<string, Candidate>());
  const queued = useRef(new Map<string, { timer: number; send: () => void }>());

  const tab: CandidateType = types.includes(params.type as CandidateType)
    ? (params.type as CandidateType)
    : "add";
  const pending = (type: CandidateType) =>
    items.filter((c) => c.type === type && c.status === "pending").length;
  const open = view === "candidates";

  // A plain value (not read from params) so the callback below can depend on it safely.
  const english = searchParams.get("lang") === "en";

  /** Not signed in, or not an admin: back to sign-in (with the reason for non-admins). */
  const leave = useCallback(
    (error: unknown) => {
      if (!(error instanceof AdminApiError)) return false;
      const langParam = { lang: english ? "en" : undefined };
      if (error.status === 401) {
        navigate(href("/admin", langParam), { replace: true });
        return true;
      }
      if (error.status === 403) {
        void signOut();
        navigate(href("/admin", langParam, { state: "forbidden" }), { replace: true });
        return true;
      }
      return false;
    },
    [navigate, english],
  );

  useEffect(() => {
    if (!adminLive) return;
    let cancelled = false;
    listCandidates()
      .then((list) => {
        if (cancelled) return;
        setItems(list);
        setLoad("ready");
      })
      .catch((error) => {
        if (cancelled || leave(error)) return;
        setLoad("failed");
      });
    return () => {
      cancelled = true;
    };
  }, [reload, leave]);

  // Leaving the page sends any decisions still inside their undo window; closing the tab asks
  // first, because those would be lost.
  useEffect(() => {
    const waiting = queued.current;
    const warn = (event: BeforeUnloadEvent) => {
      if (waiting.size > 0) event.preventDefault();
    };
    window.addEventListener("beforeunload", warn);
    return () => {
      window.removeEventListener("beforeunload", warn);
      for (const { timer, send } of waiting.values()) {
        window.clearTimeout(timer);
        send();
      }
      waiting.clear();
    };
  }, []);

  function restore(id: string) {
    const original = originals.current.get(id);
    if (original) setItems((all) => all.map((c) => (c.id === id ? original : c)));
  }

  function decide(id: string, decision: Decision, statement?: Localised) {
    const original = items.find((c) => c.id === id);
    if (!original) return;
    originals.current.set(id, original);
    setAlert(undefined);
    setItems((all) =>
      all.map((c) =>
        c.id === id
          ? {
              ...c,
              status: decision === "approve" ? "approved" : "rejected",
              // Shown until the server answers: the edited text, the rule confirmed as still
              // correct, or the proposal as published. The proposal itself is never replaced.
              decidedStatement:
                decision === "approve"
                  ? (statement ??
                    (c.type === "review" ? c.current?.statement : undefined) ??
                    c.statement)
                  : undefined,
            }
          : c,
      ),
    );
    if (!adminLive) return;

    const send = () => {
      queued.current.delete(id);
      setSent((all) => new Set(all).add(id));
      // Sends the rule version the admin saw when deciding (in `original`), never a newer one:
      // if another approval changed the rule meanwhile, the server answers 409 and the queue
      // reloads so the admin decides again on the latest text.
      decideCandidate(original, decision, statement)
        .then(({ candidate: decided }) =>
          setItems((all) => all.map((c) => (c.id === id ? decided : c))),
        )
        .catch((error) => {
          if (leave(error)) return;
          setSent((all) => {
            const next = new Set(all);
            next.delete(id);
            return next;
          });
          restore(id);
          setAlert(alertFor(error));
          // Someone else decided it or changed its rule meanwhile: fetch the queue again.
          if (error instanceof AdminApiError && error.status === 409) setReload((n) => n + 1);
        });
    };
    queued.current.set(id, { timer: window.setTimeout(send, UNDO_MS), send });
  }

  function undo(id: string) {
    const waiting = queued.current.get(id);
    if (waiting) {
      window.clearTimeout(waiting.timer);
      queued.current.delete(id);
    }
    restore(id);
  }

  return (
    <main className={styles.page} lang={lang}>
      <AdminHeader lang={lang} current={view} />
      <h1 className="sr-only">{ta(open ? "candidates" : "publishedRules", lang)}</h1>

      {/* Candidate filters roll down under 候補 and roll away on 公開ルール. */}
      <div className={styles.filters} data-open={open || undefined} inert={!open}>
        <div className={styles.filtersInner}>
          <nav
            className={styles.tabs}
            aria-label={ta("candidates", lang)}
            style={{ "--active": types.indexOf(tab) } as CSSProperties}
          >
            {types.map((type) => (
              <Link
                key={type}
                className={styles.tab}
                to={href("/admin/candidates", params, { type })}
                aria-current={open && type === tab ? "page" : undefined}
                replace
              >
                {ta(typeLabel[type], lang)}
                <span className={styles.count}>{pending(type)}</span>
              </Link>
            ))}
            <span className={styles.indicator} aria-hidden="true" />
          </nav>
        </div>
      </div>

      {!adminLive && (
        <p className={styles.sample} role="note">
          {ta("sampleData", lang)}
        </p>
      )}
      {alert && (
        <p className={styles.alert} role="alert">
          {ta(alert, lang)}
        </p>
      )}

      {open ? (
        <CandidatesView
          lang={lang}
          load={load}
          items={items.filter((c) => c.type === tab)}
          onDecide={decide}
          canUndo={(id) => !sent.has(id)}
          onUndo={undo}
          onRetry={() => {
            setLoad("loading");
            setReload((n) => n + 1);
          }}
        />
      ) : (
        <RulesView lang={lang} onLeave={leave} />
      )}
    </main>
  );
}

type CandidatesProps = {
  lang: Lang;
  load: Load;
  items: Candidate[];
  onDecide: (id: string, decision: Decision, statement?: Localised) => void;
  canUndo: (id: string) => boolean;
  onUndo: (id: string) => void;
  onRetry: () => void;
};

function CandidatesView(props: CandidatesProps) {
  const { lang, load, items, onDecide, canUndo, onUndo, onRetry } = props;
  if (load === "loading") return <Loading lang={lang} />;
  if (load === "failed") return <LoadFailed lang={lang} onRetry={onRetry} />;
  const noneLeft = items.every((c) => c.status !== "pending");

  return (
    <>
      {noneLeft && (
        <div className={styles.empty} role="status">
          <Mascot size={72} />
          <p>{ta("noneLeft", lang)}</p>
        </div>
      )}

      <ul className={styles.list}>
        {items.map((c) => (
          <CandidateCard
            key={c.id}
            candidate={c}
            lang={lang}
            onDecide={onDecide}
            onUndo={canUndo(c.id) ? onUndo : undefined}
          />
        ))}
      </ul>
    </>
  );
}

function Loading({ lang }: { lang: Lang }) {
  return (
    <p className={styles.loading} role="status">
      {ta("loading", lang)}
    </p>
  );
}

function LoadFailed({ lang, onRetry }: { lang: Lang; onRetry: () => void }) {
  return (
    <div className={styles.failed}>
      <StateCard title={ta("loadFailed", lang)} tone="warning">
        <button type="button" className={styles.secondary} onClick={onRetry}>
          {ta("retry", lang)}
        </button>
      </StateCard>
    </div>
  );
}

/** A published rule as the rules page shows it. Category and place exist only in sample data. */
type RuleRow = {
  id: string;
  statement: Localised;
  updatedAt: string;
  /** From the admin API; sample rows have none. */
  version?: string;
  category?: Category;
  place?: Localised;
};

const sampleRows = (): RuleRow[] =>
  sampleRules.map(({ id, statement, updatedAt, category, place }) => ({
    id,
    statement,
    updatedAt,
    category,
    place,
  }));

function RulesView({ lang, onLeave }: { lang: Lang; onLeave: (error: unknown) => boolean }) {
  const [items, setItems] = useState<RuleRow[]>(adminLive ? [] : sampleRows);
  const [load, setLoad] = useState<Load>(adminLive ? "loading" : "ready");
  const [reload, setReload] = useState(0);
  const [editing, setEditing] = useState<string>();
  const [draft, setDraft] = useState<Localised>({ ja: "", en: "" });
  // The version the draft was written against. Saving sends this, never a version loaded later.
  const [base, setBase] = useState<string>();
  // Someone else saved this rule first: the admin must choose how to continue before saving.
  const [conflict, setConflict] = useState(false);
  const [saved, setSaved] = useState<string>();
  const [saving, setSaving] = useState(false);
  const [alert, setAlert] = useState<Alert>();

  useEffect(() => {
    if (!adminLive) return;
    let cancelled = false;
    listRules()
      .then((list) => {
        if (cancelled) return;
        setItems(list);
        setLoad("ready");
      })
      .catch((error) => {
        if (cancelled || onLeave(error)) return;
        setLoad("failed");
      });
    return () => {
      cancelled = true;
    };
  }, [reload, onLeave]);

  function startEditing(row: RuleRow) {
    setDraft(row.statement);
    setBase(row.version);
    setConflict(false);
    setEditing(row.id);
    setSaved(undefined);
  }

  async function save(row: RuleRow, version = base) {
    setAlert(undefined);
    let saved: Pick<RuleRow, "statement" | "updatedAt" | "version"> = {
      statement: draft,
      updatedAt: today(),
    };
    if (adminLive) {
      setSaving(true);
      try {
        const rule = await editRule(row.id, draft, version ?? "");
        saved = { statement: rule.statement, updatedAt: rule.updatedAt, version: rule.version };
      } catch (error) {
        setSaving(false);
        if (onLeave(error)) return;
        setAlert(alertFor(error));
        if (error instanceof AdminApiError && error.status === 409) {
          // Changed by someone else: load their text and show it next to this draft. Saving is
          // blocked until the admin either starts again from their text or replaces it on purpose.
          setConflict(true);
          setReload((n) => n + 1);
        }
        return;
      }
      setSaving(false);
    }
    setItems((all) => all.map((r) => (r.id === row.id ? { ...r, ...saved } : r)));
    setEditing(undefined);
    setConflict(false);
    setSaved(row.id);
  }

  if (load === "loading") return <Loading lang={lang} />;
  if (load === "failed")
    return (
      <LoadFailed
        lang={lang}
        onRetry={() => {
          setLoad("loading");
          setReload((n) => n + 1);
        }}
      />
    );

  return (
    <>
      {alert && (
        <p className={styles.alert} role="alert">
          {ta(alert, lang)}
        </p>
      )}
      <ul className={styles.rules}>
        {items.map((rule) => (
          <li key={rule.id} className={styles.rule}>
            {(rule.category || rule.place) && (
              <div className={styles.ruleHead}>
                {rule.category && (
                  <Tag
                    tone={rule.category}
                    icon={<CategoryIcon category={rule.category} size={14} />}
                  >
                    {categories[rule.category].label[lang]}
                  </Tag>
                )}
                {rule.place && (
                  <span className={styles.place}>
                    <Icon name="pin" size={14} />
                    {rule.place[lang]}
                  </span>
                )}
              </div>
            )}

            {editing === rule.id ? (
              <div className={styles.editor}>
                {conflict && (
                  <div className={styles.latest} aria-label={ta("latestPublished", lang)}>
                    <p className={styles.latestLabel}>{ta("latestPublished", lang)}</p>
                    {(["ja", "en"] as const).map((l) => (
                      <p key={l} lang={l}>
                        {rule.statement[l]}
                      </p>
                    ))}
                  </div>
                )}
                {(["ja", "en"] as const).map((l) => (
                  <label key={l} className={styles.editField}>
                    <span className={styles.langLabel}>{l === "ja" ? "JP" : "EN"}</span>
                    <textarea
                      className={styles.textarea}
                      rows={2}
                      lang={l}
                      value={draft[l]}
                      aria-label={ta(l === "ja" ? "japanese" : "english", lang)}
                      onChange={(event) => setDraft({ ...draft, [l]: event.target.value })}
                    />
                  </label>
                ))}
              </div>
            ) : (
              <dl className={styles.langs}>
                {(["ja", "en"] as const).map((l) => (
                  <div key={l} className={styles.langRow}>
                    <dt className={styles.langLabel}>{l === "ja" ? "JP" : "EN"}</dt>
                    <dd lang={l}>{rule.statement[l]}</dd>
                  </div>
                ))}
              </dl>
            )}

            {/* Footer: when it was last updated on the left, the edit control on the right. */}
            <div className={styles.ruleFoot}>
              <span className={styles.date}>
                {ta("updatedAt", lang)} {formatJst(rule.updatedAt)}
              </span>
              {saved === rule.id && (
                <span className={styles.saved} role="status">
                  <Icon name="check" size={14} strokeWidth={2.4} />
                  {ta("savedRule", lang)}
                </span>
              )}
              {editing === rule.id ? (
                <div className={styles.editActions}>
                  <button
                    type="button"
                    className={styles.secondary}
                    onClick={() => {
                      setEditing(undefined);
                      setConflict(false);
                    }}
                  >
                    {ta("cancel", lang)}
                  </button>
                  {conflict ? (
                    <>
                      <button
                        type="button"
                        className={styles.secondary}
                        disabled={saving}
                        onClick={() => startEditing(rule)}
                      >
                        {ta("useLatest", lang)}
                      </button>
                      <button
                        type="button"
                        className={styles.primary}
                        disabled={saving || !draft.ja.trim() || !draft.en.trim()}
                        // Replaces exactly the text shown above (its version), on purpose.
                        onClick={() => {
                          setBase(rule.version);
                          void save(rule, rule.version);
                        }}
                      >
                        {ta("overwrite", lang)}
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      className={styles.primary}
                      disabled={saving || !draft.ja.trim() || !draft.en.trim()}
                      onClick={() => void save(rule)}
                    >
                      {ta("save", lang)}
                    </button>
                  )}
                </div>
              ) : (
                <button
                  type="button"
                  className={styles.editIcon}
                  aria-label={`${ta("editRule", lang)}: ${rule.statement[lang]}`}
                  title={ta("editRule", lang)}
                  onClick={() => startEditing(rule)}
                >
                  <Icon name="edit" size={20} />
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
