import { t } from "@/content/copy";
import type { Lang } from "@/content/types";
import { Icon } from "./Icon";
import styles from "./LocationButton.module.css";

export function LocationButton({ lang, denied = false }: { lang: Lang; denied?: boolean }) {
  return (
    <button
      className={styles.button}
      type="button"
      data-denied={denied || undefined}
      aria-label={t(denied ? "locateDenied" : "locate", lang)}
    >
      <Icon name={denied ? "locateOff" : "locate"} />
    </button>
  );
}
