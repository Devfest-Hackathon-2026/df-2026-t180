import type { ReactNode } from "react";
import styles from "./Tag.module.css";

type Props = {
  children: ReactNode;
  tone?: "plain" | "manners" | "transport" | "living" | "highlight";
  icon?: ReactNode;
};

/** Small monospace label in an outlined pill. */
export function Tag({ children, tone = "plain", icon }: Props) {
  return (
    <span className={styles.tag} data-tone={tone}>
      {icon}
      {children}
    </span>
  );
}
