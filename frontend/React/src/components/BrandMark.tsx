import { Link } from "react-router";
import { appName } from "@/content/copy";
import type { Lang } from "@/content/types";
import { href } from "@/content/url";
import styles from "./BrandMark.module.css";

/** Four colour dots and the product name. The dots hop one after another on hover. */
export function BrandMark({ lang, as = "p" }: { lang: Lang; as?: "h1" | "p" }) {
  const Tag = as;
  return (
    <Tag className={styles.brand}>
      <Link className={styles.link} to={href("/", { lang: lang === "en" ? "en" : undefined })}>
        <span className={styles.dots} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </span>
        {appName[lang]}
      </Link>
    </Tag>
  );
}
