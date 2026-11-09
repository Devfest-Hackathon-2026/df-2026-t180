import { type CSSProperties, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { AdminHeader } from "@/components/AdminHeader";
import { CandidateCard, type Decision } from "@/components/CandidateCard";
import { CategoryIcon } from "@/components/CategoryIcon";
import { Icon } from "@/components/Icon";
import { Mascot } from "@/components/Mascot";
import { Tag } from "@/components/Tag";
import { type Candidate, type CandidateType, sampleCandidates, ta } from "@/content/admin";
import { categories } from "@/content/copy";
import { formatDate, rules as publishedRules } from "@/content/rules";
import type { Lang, Localised, Rule } from "@/content/types";
import { href, readLang, type Params } from "@/content/url";
import styles from "./AdminPage.module.css";

const types: CandidateType[] = ["add", "update", "review"];
const typeLabel = { add: "typeAdd", update: "typeUpdate", review: "typeReview" } as const;
const today = () => new Date().toISOString().slice(0, 10);

/**
 * Admin (機能D): review the candidate queue and edit published rules. Actions are mocked in
 * local state; they become PATCH /api/admin/candidates/{id} and PATCH /api/admin/rules/{id}.
 */
export function AdminPage() {
  const { area } = useParams();
  const [searchParams] = useSearchParams();
  const params: Params = Object.fromEntries(searchParams);
  const lang = readLang(params);
  const view = area === "rules" ? "rules" : "candidates";
  // Kept here so decisions and counts survive switching to 公開ルール and back.
  const [items, setItems] = useState<Candidate[]>(sampleCandidates);
  const tab: CandidateType = types.includes(params.type as CandidateType)
    ? (params.type as CandidateType)
    : "add";
  const pending = (type: CandidateType) =>
    items.filter((c) => c.type === type && c.status === "pending").length;
  const open = view === "candidates";

  function decide(id: string, decision: Decision, statement?: Localised) {
    setItems((all) =>
      all.map((c) =>
        c.id === id
          ? {
              ...c,
              status: decision === "approve" ? "approved" : "rejected",
              statement: statement ?? c.statement,
            }
          : c,
      ),
    );
  }

  function undo(id: string) {
    const original = sampleCandidates.find((c) => c.id === id);
    setItems((all) => all.map((c) => (c.id === id && original ? original : c)));
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

      {open ? (
        <CandidatesView
          lang={lang}
          items={items.filter((c) => c.type === tab)}
          onDecide={decide}
          onUndo={undo}
        />
      ) : (
        <RulesView lang={lang} />
      )}
    </main>
  );
}

type CandidatesProps = {
  lang: Lang;
  items: Candidate[];
  onDecide: (id: string, decision: Decision, statement?: Localised) => void;
  onUndo: (id: string) => void;
};

function CandidatesView({ lang, items, onDecide, onUndo }: CandidatesProps) {
  return (
    <>
      {items.length > 0 && items.every((c) => c.status !== "pending") && (
        <div className={styles.empty} role="status">
          <Mascot size={72} />
          <p>{ta("noneLeft", lang)}</p>
        </div>
      )}

      <ul className={styles.list}>
        {items.map((c) => (
          <CandidateCard key={c.id} candidate={c} lang={lang} onDecide={onDecide} onUndo={onUndo} />
        ))}
      </ul>
    </>
  );
}

function RulesView({ lang }: { lang: Lang }) {
  const [items, setItems] = useState<Rule[]>(publishedRules);
  const [editing, setEditing] = useState<string>();
  const [draft, setDraft] = useState<Localised>({ ja: "", en: "" });
  const [saved, setSaved] = useState<string>();

  function save(id: string) {
    setItems((all) =>
      all.map((r) => (r.id === id ? { ...r, statement: draft, updatedAt: today() } : r)),
    );
    setEditing(undefined);
    setSaved(id);
  }

  return (
    <ul className={styles.rules}>
      {items.map((rule) => (
        <li key={rule.id} className={styles.rule}>
          <div className={styles.ruleHead}>
            <Tag tone={rule.category} icon={<CategoryIcon category={rule.category} size={14} />}>
              {categories[rule.category].label[lang]}
            </Tag>
            {rule.place && (
              <span className={styles.place}>
                <Icon name="pin" size={14} />
                {rule.place[lang]}
              </span>
            )}
            <span className={styles.date}>
              {ta("updatedAt", lang)} {formatDate(rule.updatedAt)}
            </span>
          </div>

          {editing === rule.id ? (
            <div className={styles.editor}>
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
              <div className={styles.editActions}>
                <button
                  type="button"
                  className={styles.primary}
                  disabled={!draft.ja.trim() || !draft.en.trim()}
                  onClick={() => save(rule.id)}
                >
                  {ta("save", lang)}
                </button>
                <button
                  type="button"
                  className={styles.secondary}
                  onClick={() => setEditing(undefined)}
                >
                  {ta("cancel", lang)}
                </button>
              </div>
            </div>
          ) : (
            <div className={styles.ruleBody}>
              <dl className={styles.langs}>
                {(["ja", "en"] as const).map((l) => (
                  <div key={l} className={styles.langRow}>
                    <dt className={styles.langLabel}>{l === "ja" ? "JP" : "EN"}</dt>
                    <dd lang={l}>{rule.statement[l]}</dd>
                  </div>
                ))}
              </dl>
              <button
                type="button"
                className={styles.secondary}
                onClick={() => {
                  setDraft(rule.statement);
                  setEditing(rule.id);
                  setSaved(undefined);
                }}
              >
                {ta("editRule", lang)}
              </button>
            </div>
          )}

          {saved === rule.id && (
            <p className={styles.saved} role="status">
              <Icon name="check" size={16} strokeWidth={2.4} />
              {ta("savedRule", lang)}
            </p>
          )}
        </li>
      ))}
    </ul>
  );
}
