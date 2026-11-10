import { Link } from "react-router";
import { t } from "@/content/copy";
import type { Lang } from "@/content/types";
import { href, readLang } from "@/content/url";
import { useSlideNavigate } from "@/hooks/useSlideNavigate";
import { Icon } from "./Icon";
import styles from "./AppNav.module.css";

type Area = "explore" | "residents";
type Props = { lang: Lang; current: Area };

/** The language in the address right now (it can change while the thumb slides). */
const currentLang = () => {
  const lang = readLang(Object.fromEntries(new URLSearchParams(window.location.search)));
  return { lang: lang === "en" ? "en" : undefined };
};

const items = [
  { id: "explore", path: "/", icon: "explore" },
  { id: "residents", path: "/contribute", icon: "residents" },
] as const;

/**
 * Switches between the visitor map and the resident side. The thumb slides on the current screen
 * first and the page changes once it lands (see useSlideNavigate), so the slide never competes
 * with building the next screen.
 */
export function AppNav({ lang, current }: Props) {
  const langParam = { lang: lang === "en" ? "en" : undefined };
  const { shown, go } = useSlideNavigate<Area>(current);

  return (
    <nav className={styles.nav} aria-label={t("primaryNav", lang)} data-current={shown}>
      <span className={styles.thumb} aria-hidden="true" />
      {items.map((item) => {
        const to = href(item.path, langParam);
        return (
          <Link
            key={item.id}
            className={styles.item}
            to={to}
            // Read the language when the slide lands, so switching JP/EN mid-slide sticks (#32).
            onClick={(event) => go(item.id, () => href(item.path, currentLang()), event)}
            aria-current={item.id === current ? "page" : undefined}
            data-active={item.id === shown || undefined}
          >
            <Icon name={item.icon} size={20} />
            {t(item.id, lang)}
          </Link>
        );
      })}
    </nav>
  );
}
