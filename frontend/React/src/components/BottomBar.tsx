import type { ReactNode } from "react";
import type { Lang } from "@/content/types";
import { AppNav } from "./AppNav";
import styles from "./BottomBar.module.css";

type Props = {
  lang: Lang;
  current: "explore" | "residents";
  /** Sits on top of the row, left-aligned (the map wordmark on Explore). */
  above?: ReactNode;
  /** The round 56px button to the right of the nav: location on Explore, send on Residents. */
  action?: ReactNode;
  className?: string;
};

/**
 * The bottom row shared by every screen, so 探す / 地元の方 sits in exactly the same place
 * everywhere and its thumb can slide between pages. It stays 30px above the bottom edge, clear of
 * the Google logo and map credits that the Maps terms require to remain visible.
 */
export function BottomBar({ lang, current, above, action, className }: Props) {
  return (
    <div className={[styles.bar, className].filter(Boolean).join(" ")}>
      {above}
      <div className={styles.row}>
        <AppNav lang={lang} current={current} />
        {action ?? <span className={styles.slot} aria-hidden="true" />}
      </div>
    </div>
  );
}
