import { t } from "@/content/copy";
import type { Lang } from "@/content/types";
import type { LocationStatus } from "@/hooks/useMyLocation";
import { Icon } from "./Icon";
import styles from "./LocationButton.module.css";

type Props = {
  lang: Lang;
  status: LocationStatus;
  onClick?: () => void;
  /** "row" matches the height of the nav pill when they share the bottom row. */
  size?: "default" | "row";
};

const labels = {
  idle: "locate",
  locating: "locating",
  on: "locate",
  denied: "locateDenied",
  unavailable: "locate",
} as const;

/**
 * Toggles showing the visitor on the map. Lifted onto its hard shadow while on (tap again to turn it off); dashed and
 * crossed out when the browser refused permission (tap to ask again).
 */
export function LocationButton({ lang, status, onClick, size = "default" }: Props) {
  const off = status === "denied";
  return (
    <button
      className={styles.button}
      type="button"
      data-status={status}
      data-size={size}
      onClick={onClick}
      aria-label={t(labels[status], lang)}
      aria-busy={status === "locating" || undefined}
      aria-pressed={status === "on"}
    >
      <Icon name={off ? "locateOff" : "locate"} />
    </button>
  );
}
