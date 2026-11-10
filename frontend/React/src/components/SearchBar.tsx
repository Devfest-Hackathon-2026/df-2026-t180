import type { FormEvent } from "react";
import { useNavigate } from "react-router";
import { t } from "@/content/copy";
import type { Lang } from "@/content/types";
import { href } from "@/content/url";
import { Icon } from "./Icon";
import styles from "./SearchBar.module.css";

type Props = { lang: Lang; query?: string };

/** Area search. Submitting only updates the URL; matching runs on static sample data. */
export function SearchBar({ lang, query }: Props) {
  const navigate = useNavigate();

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const q = String(new FormData(event.currentTarget).get("q") ?? "").trim();
    navigate(href("/", { lang: lang === "en" ? "en" : undefined, q: q || undefined }));
  }

  return (
    <form className={styles.bar} role="search" onSubmit={onSubmit}>
      <Icon name="search" size={22} />
      <label className="sr-only" htmlFor="area-search">
        {t("searchLabel", lang)}
      </label>
      <input
        id="area-search"
        key={query}
        className={styles.input}
        name="q"
        type="search"
        defaultValue={query}
        placeholder={t("search", lang)}
        autoComplete="off"
        enterKeyHint="search"
      />
    </form>
  );
}
