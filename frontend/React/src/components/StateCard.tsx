import type { ReactNode } from "react";
import { Mascot } from "./Mascot";
import styles from "./StateCard.module.css";

type Props = {
  title: string;
  body?: string;
  children?: ReactNode;
  tone?: "plain" | "warning";
};

/** Empty, error and holding states: the mascot, one line, and at most one action. */
export function StateCard({ title, body, children, tone = "plain" }: Props) {
  return (
    <section className={styles.card} data-tone={tone} role="status">
      <Mascot mood="puzzled" size={84} />
      <div className={styles.text}>
        <h2 className={styles.title}>{title}</h2>
        {body && <p className={styles.body}>{body}</p>}
        {children}
      </div>
    </section>
  );
}
