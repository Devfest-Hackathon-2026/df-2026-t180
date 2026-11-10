import { Link } from "react-router";
import { Icon, type IconName } from "./Icon";
import styles from "./PillLink.module.css";

type Props = {
  to: string;
  children: string;
  icon?: IconName;
  tone?: "highlight" | "plain";
};

/** Pill link with a round black arrow, which turns to point forward on hover. */
export function PillLink({ to, children, icon = "arrowUpRight", tone = "highlight" }: Props) {
  return (
    <Link className={styles.pill} to={to} data-tone={tone} data-icon={icon}>
      <span>{children}</span>
      <span className={styles.circle} aria-hidden="true">
        <Icon name={icon} size={18} strokeWidth={2.4} />
      </span>
    </Link>
  );
}
