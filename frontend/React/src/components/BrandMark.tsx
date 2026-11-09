import { Link } from "react-router";
import { appName } from "@/content/copy";
import type { Lang } from "@/content/types";
import { href } from "@/content/url";
import styles from "./BrandMark.module.css";

const letters = ["M", "a", "n", "a", "b", "i"];

/**
 * The "Manabi" wordmark in ink. The letters hop one after another on hover. Screen readers hear the name
 * in the current language.
 */
function Wordmark({ className }: { className?: string }) {
  return (
    <span className={[styles.word, className].filter(Boolean).join(" ")} aria-hidden="true">
      {letters.map((letter, i) => (
        <span key={i}>{letter}</span>
      ))}
    </span>
  );
}

export function BrandMark({ lang, as = "p" }: { lang: Lang; as?: "h1" | "p" }) {
  const Tag = as;
  return (
    <Tag className={styles.brand}>
      <Link
        className={styles.link}
        to={href("/", { lang: lang === "en" ? "en" : undefined })}
        aria-label={appName[lang]}
      >
        <Wordmark />
      </Link>
    </Tag>
  );
}
