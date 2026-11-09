import { useEffect } from "react";
import { Link } from "react-router";
import { t } from "@/content/copy";
import type { Lang } from "@/content/types";
import { href } from "@/content/url";
import { Icon } from "./Icon";
import styles from "./AppNav.module.css";

type Area = "explore" | "residents";
type Props = { lang: Lang; current: Area };

const items = [
  { id: "explore", path: "/", icon: "explore" },
  { id: "residents", path: "/contribute", icon: "residents" },
] as const;

/**
 * Each area is a different page, so the nav remounts on every switch. Remembering the area that
 * was active before lets the new nav slide its thumb across from there instead of jumping.
 */
let lastArea: Area | undefined;

/** Switches between the visitor map and the resident side. */
export function AppNav({ lang, current }: Props) {
  const from = lastArea && lastArea !== current ? lastArea : undefined;
  const langParam = { lang: lang === "en" ? "en" : undefined };

  useEffect(() => {
    lastArea = current;
  }, [current]);

  return (
    <nav
      className={styles.nav}
      aria-label={t("primaryNav", lang)}
      data-current={current}
      data-from={from}
    >
      <span className={styles.thumb} aria-hidden="true" />
      {items.map((item) => (
        <Link
          key={item.id}
          className={styles.item}
          to={href(item.path, langParam)}
          aria-current={item.id === current ? "page" : undefined}
        >
          <Icon name={item.icon} size={20} />
          {t(item.id, lang)}
        </Link>
      ))}
    </nav>
  );
}
