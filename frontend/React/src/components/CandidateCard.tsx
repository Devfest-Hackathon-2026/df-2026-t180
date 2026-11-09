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
  onUndo: (id: string) => void;
};

const typeLabel = { add: "typeAdd", update: "typeUpdate", review: "typeReview" } as const;
const typeTone = { add: "living", update: "transport", review: "highlight" } as const;

/**
 * One candidate in the admin queue. Approve publishes it; for a re-check it means "still
 * correct" (last_reviewed_at only). Edit lets the admin fix the ja/en text before approving.
 * Reject leaves the rule unchanged (#24).
 */
export function CandidateCard({ candidate: c, lang, onDecide, onUndo }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Localised>(c.statement);
  const titleId = `${c.id}-title`;

  if (c.status !== "pending") {
    const done =
      c.status === "rejected" ? "rejected" : c.type === "review" ? "confirmedOk" : "approved";
    return (
      <li className={styles.done} data-status={c.status}>
        <Icon name={c.status === "rejected" ? "close" : "check"} size={18} strokeWidth={2.4} />
        <span className={styles.doneText}>
          <strong>{ta(done, lang)}</strong>
          <span className={styles.doneStatement}>{c.statement[lang]}</span>
        </span>
        <button type="button" className={styles.undo} onClick={() => onUndo(c.id)}>
          {ta("undo", lang)}
        </button>
      </li>
    );
  }

  return (
    <li className={styles.card} aria-labelledby={titleId}>
      <div className={styles.head}>
        <Tag tone={typeTone[c.type]}>{ta(typeLabel[c.type], lang)}</Tag>
        <span className={styles.meta}>
          {findRegion(c.region)?.name[lang] ?? c.region}
          {c.post && (
            <>
              <span aria-hidden="true"> · </span>
              {formatJst(c.post.createdAt)}
            </>
          )}
        </span>
      </div>

      <h2 className={styles.title} id={titleId}>
        {c.statement[lang]}
      </h2>

      {c.reviewReason && (
        <p className={styles.reason}>
          <Icon name="locate" size={16} />
          <span>
            <span className={styles.kicker}>{ta("reviewReason", lang)}</span> {c.reviewReason}
          </span>
        </p>
      )}

      {c.post && (
        <figure className={styles.block}>
          <figcaption className={styles.kicker}>{ta("fromPost", lang)}</figcaption>
          <blockquote className={styles.quote} lang="ja">
            {c.post.text}
          </blockquote>
          {(c.post.reason || c.post.place) && (
            <p className={styles.small}>
              {c.post.reason && (
                <span>
                  {ta("postReason", lang)}：{c.post.reason}
                </span>
              )}
              {c.post.place && (
                <span className={styles.place}>
                  <Icon name="pin" size={14} />
                  {c.post.place}
                </span>
              )}
            </p>
          )}
        </figure>
      )}

      {c.current && (
        <div className={styles.block}>
          <p className={styles.kicker}>{ta("currentRule", lang)}</p>
          <p className={styles.current}>{c.current.statement[lang]}</p>
          <p className={styles.small}>
            {ta("lastChecked", lang)} {formatJst(c.current.lastReviewedAt ?? c.current.updatedAt)}
          </p>
        </div>
      )}

      <div className={styles.block} data-proposed>
        <p className={styles.kicker}>{ta("proposed", lang)}</p>
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
          <dl className={styles.langs}>
            {(["ja", "en"] as const).map((l) => (
              <div key={l} className={styles.langRow}>
                <dt className={styles.langLabel}>{l === "ja" ? "JP" : "EN"}</dt>
                <dd lang={l}>{c.statement[l]}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>

      <div className={styles.actions}>
        {editing ? (
          <>
            <button
              type="button"
              className={styles.primary}
              disabled={!draft.ja.trim() || !draft.en.trim()}
              onClick={() => onDecide(c.id, "approve", draft)}
            >
              <Icon name="check" size={18} strokeWidth={2.4} />
              {ta("save", lang)}
            </button>
            <button
              type="button"
              className={styles.secondary}
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
              className={styles.primary}
              onClick={() => onDecide(c.id, "approve")}
            >
              <Icon name="check" size={18} strokeWidth={2.4} />
              {ta(c.type === "review" ? "stillCorrect" : "approve", lang)}
            </button>
            <button type="button" className={styles.secondary} onClick={() => setEditing(true)}>
              {ta("edit", lang)}
            </button>
            <button
              type="button"
              className={styles.reject}
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
