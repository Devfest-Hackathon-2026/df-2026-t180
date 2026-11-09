import type { CSSProperties } from "react";
import styles from "./ManagerMascot.module.css";

export type ManagerState = "idle" | "email" | "password" | "error" | "happy";

type Props = {
  state: ManagerState;
  /** Where the eyes look, each from -1 to 1 (x: left to right, y: up to down). */
  look?: { x: number; y: number };
  className?: string;
};

const EDGE = 96; // y of the card's top edge in the drawing

/**
 * The guide sprout as the admin "manager": round glasses and a tie, peeking over the top edge of
 * the sign-in card with both hands on it. Drawn in two layers that share one viewBox: the body sits
 * behind the card (so the card hides its lower half) and the hands sit in front of it. Decorative.
 */
export function ManagerMascot({ state, look = { x: 0, y: 0 }, className }: Props) {
  const vars = { "--lx": look.x, "--ly": look.y } as CSSProperties;
  const happy = state === "happy";
  const puzzled = state === "error";

  return (
    <div
      className={[styles.mascot, className].filter(Boolean).join(" ")}
      data-state={state}
      style={vars}
      aria-hidden="true"
    >
      <svg className={styles.back} viewBox="0 0 160 110">
        <g className={styles.body}>
          <g
            className={styles.sprout}
            stroke="var(--color-ink)"
            strokeWidth="3"
            strokeLinejoin="round"
          >
            <path d="M80 22c0-5.5 0-8.5 1-12.5" fill="none" strokeLinecap="round" />
            <path d="M81 11.5c-7-9-17-8-18-1 5 4 12 5 18 1z" fill="var(--g-green)" />
            <path d="M81 9.5c6-10 17-10 18-2-5 4-12 5-18 2z" fill="var(--g-green)" />
          </g>

          <path
            d="M80 22c25 0 43 16 43 38 0 21-18 40-43 40S37 81 37 60c0-22 18-38 43-38z"
            fill="var(--lime)"
            stroke="var(--color-ink)"
            strokeWidth="3"
          />

          {/* Tie: the knot sits under the chin; the blade runs on behind the card. */}
          <g
            stroke="var(--color-ink)"
            strokeWidth="2.5"
            strokeLinejoin="round"
            fill="var(--g-blue)"
          >
            <path d="M75 86h10l-2 5h-6z" />
            <path d="M77 91h6l3 12h-12z" />
          </g>

          <g className={styles.face}>
            {happy ? (
              <g fill="none" stroke="var(--color-ink)" strokeWidth="3" strokeLinecap="round">
                <path d="M61 58q5-6 10 0" />
                <path d="M89 58q5-6 10 0" />
              </g>
            ) : (
              <g className={styles.eyes} fill="var(--color-ink)">
                <ellipse cx="66" cy="57" rx="3.4" ry={puzzled ? 3.4 : 4.6} />
                <ellipse cx="94" cy="57" rx="3.4" ry={puzzled ? 3.4 : 4.6} />
              </g>
            )}

            {/* Round glasses */}
            <g fill="none" stroke="var(--color-ink)" strokeWidth="2.5">
              <circle cx="66" cy="57" r="10" />
              <circle cx="94" cy="57" r="10" />
              <path d="M76 56q4-3 8 0" strokeLinecap="round" />
            </g>

            <ellipse cx="54" cy="72" rx="5.5" ry="3.2" fill="var(--g-red)" opacity="0.35" />
            <ellipse cx="106" cy="72" rx="5.5" ry="3.2" fill="var(--g-red)" opacity="0.35" />
            <path
              d={puzzled ? "M75 74h10" : happy ? "M72 71c4 7 12 7 16 0" : "M74 72c3 4 9 4 12 0"}
              fill="none"
              stroke="var(--color-ink)"
              strokeWidth="3"
              strokeLinecap="round"
            />
          </g>

          {puzzled && (
            <text className={styles.question} x="122" y="26">
              ?
            </text>
          )}
        </g>
      </svg>

      <svg className={styles.front} viewBox="0 0 160 110">
        <g fill="var(--lime)" stroke="var(--color-ink)" strokeWidth="3" strokeLinecap="round">
          <g className={styles.handLeft}>
            <g transform={`translate(52 ${EDGE})`}>
              <circle r="11" />
              <path d="M-4-6.5v4M1-7.5v4" strokeWidth="2" />
            </g>
          </g>
          <g className={styles.handRight}>
            <g transform={`translate(108 ${EDGE})`}>
              <circle r="11" />
              <path d="M-1-7.5v4M4-6.5v4" strokeWidth="2" />
            </g>
          </g>
        </g>
      </svg>
    </div>
  );
}
