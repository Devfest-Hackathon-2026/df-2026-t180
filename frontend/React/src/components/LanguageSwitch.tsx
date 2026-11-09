import { Link, useLocation, useSearchParams } from "react-router";
import { t } from "@/content/copy";
import type { Lang } from "@/content/types";
import { href, readLang } from "@/content/url";
import styles from "./LanguageSwitch.module.css";

const options: { lang: Lang; label: string; name: string }[] = [
  { lang: "ja", label: "JP", name: "日本語" },
  { lang: "en", label: "EN", name: "English" },
];

/** Two-option switch that keeps the current screen and state, changing only the language. */
export function LanguageSwitch() {
  const { pathname } = useLocation();
  const [searchParams] = useSearchParams();
  const params = Object.fromEntries(searchParams);
  const lang = readLang(params);

  return (
    <nav className={styles.switch} data-lang={lang} aria-label={t("language", lang)}>
      <span className={styles.thumb} aria-hidden="true" />
      {options.map((option) => (
        <Link
          key={option.lang}
          className={styles.option}
          to={href(pathname, params, { lang: option.lang === "ja" ? undefined : option.lang })}
          aria-current={option.lang === lang ? "true" : undefined}
          lang={option.lang}
          replace
          preventScrollReset
        >
          <span aria-hidden="true">{option.label}</span>
          <span className="sr-only">{option.name}</span>
        </Link>
      ))}
    </nav>
  );
}
