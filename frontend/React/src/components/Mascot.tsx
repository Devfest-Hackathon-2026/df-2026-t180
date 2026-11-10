import styles from "./Mascot.module.css";

type Props = {
  /** "guide" holds up a tour flag; "puzzled" is used for empty and error states. */
  mood?: "guide" | "puzzled";
  size?: number;
  className?: string;
};

/** The local guide character: a one-head-tall sprout who carries a tour flag. Decorative only. */
export function Mascot({ mood = "guide", size = 96, className }: Props) {
  const puzzled = mood === "puzzled";
  return (
    <svg
      className={[styles.mascot, className].filter(Boolean).join(" ")}
      data-mood={mood}
      width={size}
      height={(size * 120) / 140}
      viewBox="0 0 140 120"
      aria-hidden="true"
    >
      <g className={styles.body}>
        {!puzzled && (
          <g className={styles.flag}>
            <path d="M113 22v44" stroke="var(--color-ink)" strokeWidth="3" strokeLinecap="round" />
            <path
              d="M113 22h22l-6 8 6 8h-22z"
              fill="var(--g-yellow)"
              stroke="var(--color-ink)"
              strokeWidth="3"
              strokeLinejoin="round"
            />
          </g>
        )}

        <g fill="var(--lime)" stroke="var(--color-ink)" strokeWidth="3">
          <ellipse cx="46" cy="108" rx="10" ry="6" />
          <ellipse cx="74" cy="108" rx="10" ry="6" />
          <path d="M60 30c25 0 43 16 43 38 0 21-18 36-43 36S17 89 17 68c0-22 18-38 43-38z" />
        </g>

        <g
          className={styles.sprout}
          stroke="var(--color-ink)"
          strokeWidth="3"
          strokeLinejoin="round"
        >
          <path d="M60 29.5c0-5.5 0-8.5 1-12.5" fill="none" strokeLinecap="round" />
          <path d="M61 19c-7-9-17-8-18-1 5 4 12 5 18 1z" fill="var(--g-green)" />
          <path d="M61 17c6-10 17-10 18-2-5 4-12 5-18 2z" fill="var(--g-green)" />
        </g>

        <g className={styles.face}>
          <g className={styles.eyes} fill="var(--color-ink)">
            <ellipse cx="46" cy={puzzled ? 66 : 64} rx="3.8" ry={puzzled ? 3.8 : 5.2} />
            <ellipse cx="74" cy={puzzled ? 66 : 64} rx="3.8" ry={puzzled ? 3.8 : 5.2} />
          </g>
          <ellipse cx="35" cy="76" rx="6" ry="3.6" fill="var(--g-red)" opacity="0.35" />
          <ellipse cx="85" cy="76" rx="6" ry="3.6" fill="var(--g-red)" opacity="0.35" />
          <path
            d={puzzled ? "M55 80h10" : "M53 77c4 5 10 5 14 0"}
            fill="none"
            stroke="var(--color-ink)"
            strokeWidth="3"
            strokeLinecap="round"
          />
        </g>

        <g fill="var(--lime)" stroke="var(--color-ink)" strokeWidth="3">
          <circle cx="19" cy="74" r="7" />
          {puzzled ? <circle cx="101" cy="74" r="7" /> : <circle cx="110" cy="66" r="7" />}
        </g>

        {puzzled && (
          <text className={styles.question} x="98" y="38">
            ?
          </text>
        )}
      </g>
    </svg>
  );
}
