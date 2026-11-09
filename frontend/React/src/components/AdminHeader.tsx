import { Link } from "react-router";
import { ta } from "@/content/admin";
import type { Lang } from "@/content/types";
import { href } from "@/content/url";
import { BrandMark } from "./BrandMark";
import { Icon } from "./Icon";
import { LanguageSwitch } from "./LanguageSwitch";
import { Tag } from "./Tag";
import styles from "./AdminHeader.module.css";

type Props = { lang: Lang; current?: "candidates" | "rules" };

/** Admin top bar: brand with an 管理 tag, the two admin areas, language and sign out. */
export function AdminHeader({ lang, current }: Props) {
  const langParam = { lang: lang === "en" ? "en" : undefined };
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <BrandMark lang={lang} />
        <Tag tone="highlight">{ta("admin", lang)}</Tag>
      </div>
      {current && (
        <nav className={styles.nav} aria-label={ta("adminNav", lang)}>
          {(["candidates", "rules"] as const).map((area) => (
            <Link
              key={area}
              className={styles.item}
              to={href(`/admin/${area}`, langParam)}
              aria-current={area === current ? "page" : undefined}
            >
              {ta(area === "candidates" ? "candidates" : "publishedRules", lang)}
            </Link>
          ))}
        </nav>
      )}
      <div className={styles.end}>
        <LanguageSwitch />
        {current && (
          <Link
            className={styles.signOut}
            to={href("/admin", langParam)}
            aria-label={ta("signOut", lang)}
            title={ta("signOut", lang)}
          >
            <Icon name="signOut" size={22} />
          </Link>
        )}
      </div>
    </header>
  );
}
