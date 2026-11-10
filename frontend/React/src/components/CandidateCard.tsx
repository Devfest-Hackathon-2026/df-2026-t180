import { useState } from "react";
import { type Candidate, formatJst, ta } from "@/content/admin";
import { findRegion } from "@/content/rules";
import type { Lang, Localised } from "@/content/types";
import { Icon } from "./Icon";
import { Tag } from "./Tag";
import styles from "./CandidateCard.module.css";

export type Decision = "approve" | "reject";

type Props = {
  candidate: Candidate;
  lang: Lang;
  onDecide: (id: string, decision: Decision, statement?: Localised) => void;
  /** Leave out once the decision has been sent and can no longer be undone. */
  onUndo?: (id: string) => void;
};

const typeLabel = { add: "typeAdd", update: "typeUpdate", review: "typeReview" } as const;
const typeTone = { add: "living", update: "transport", review: "highlight" } as const;

/**
 * One candidate in the admin queue, read as a short chat: the resident's message on the left,
 * the draft rule on the right (quoting the live rule when it would replace it), and a system note
 * for re-checks. Approve publishes; for a re-check it means "still OK" (last_reviewed_at only).
 * Edit fixes the ja/en text before approving. Reject leaves the rule unchanged (#24).
 */
export function CandidateCard({ candidate: c, lang, onDecide, onUndo }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Localised>(c.statement);
  const titleId = `${c.id}-title`;
  const other: Lang = lang === "ja" ? "en" : "ja";
  const replaces = c.current && c.current.statement[lang] !== c.statement[lang];

  if (c.status !== "pending") {
    const done =
      c.status === "rejected" ? "rejected" : c.type === "review" ? "confirmedOk" : "approved";
    return (
      <li className={styles.done} data-status={c.status}>
        <Icon name={c.status === "rejected" ? "close" : "check"} size={18} strokeWidth={2.4} />
        <span className={styles.doneText}>
          <strong>{ta(done, lang)}</strong>
          {/* What was published or confirmed, not necessarily the proposal. */}
          <span className={styles.doneStatement}>{(c.decidedStatement ?? c.statement)[lang]}</span>
        </span>
        {onUndo && (
          <button type="button" className={styles.undo} onClick={() => onUndo(c.id)}>
            {ta("undo", lang)}
          </button>
        )}
      </li>
    );
  }

  return (
    <li className={styles.card} aria-labelledby={titleId}>
      <div className={styles.head}>
        <Tag tone={typeTone[c.type]}>{ta(typeLabel[c.type], lang)}</Tag>
        <span className={styles.meta}>
          {findRegion(c.region)?.name[lang] ?? c.region}
          {c.post && ` · ${formatJst(c.post.createdAt)}`}
        </span>
      </div>

      {c.reviewReason && <p className={styles.system}>{c.reviewReason}</p>}
      {c.ruleChangedSinceGenerated && (
        <p className={styles.warning} role="note">
          {ta("ruleChangedSinceGenerated", lang)}
        </p>
      )}

      {c.post && (
        <div className={styles.message} data-from="resident">
          <span className={styles.who}>{ta("resident", lang)}</span>
          <div className={styles.bubble}>
            <p lang="ja">{c.post.text}</p>
            {c.post.place && (
              <span className={styles.place}>
                <Icon name="pin" size={14} />
                {c.post.place}
              </span>
            )}
          </div>
        </div>
      )}

      <div className={styles.message} data-from="draft">
        <span className={styles.who}>
          {ta(c.current && !replaces ? "liveNow" : "proposed", lang)}
        </span>
        <div className={styles.bubble}>
          {replaces && c.current && (
            <p className={styles.reply}>
              <span className={styles.replyLabel}>{ta("liveNow", lang)}</span>
              <span lang={lang}>{c.current.statement[lang]}</span>
            </p>
          )}
          {editing ? (
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
            </div>
          ) : (
            <>
              <h2 className={styles.title} id={titleId} lang={lang}>
                {c.statement[lang]}
              </h2>
              <p className={styles.translation} lang={other}>
                {c.statement[other]}
              </p>
            </>
          )}
        </div>
      </div>

      <div className={styles.actions} data-count={editing ? 2 : 3}>
        {editing ? (
          <>
            <button
              type="button"
              className={styles.action}
              data-tone="approve"
              disabled={!draft.ja.trim() || !draft.en.trim()}
              onClick={() => onDecide(c.id, "approve", draft)}
            >
              {ta("save", lang)}
            </button>
            <button
              type="button"
              className={styles.action}
              onClick={() => {
                setDraft(c.statement);
                setEditing(false);
              }}
            >
              {ta("cancel", lang)}
            </button>
          </>
        ) : (
          <>
            <button
              type="button"
              className={styles.action}
              data-tone="approve"
              onClick={() => onDecide(c.id, "approve")}
            >
              {ta(c.type === "review" ? "stillCorrect" : "approve", lang)}
            </button>
            <button
              type="button"
              className={styles.action}
              data-tone="edit"
              onClick={() => setEditing(true)}
            >
              {ta("edit", lang)}
            </button>
            <button
              type="button"
              className={styles.action}
              data-tone="reject"
              onClick={() => onDecide(c.id, "reject")}
            >
              {ta("reject", lang)}
            </button>
          </>
        )}
      </div>
    </li>
  );
}
