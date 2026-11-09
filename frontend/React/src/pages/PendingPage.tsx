import { useLocation, useSearchParams } from "react-router";
import { AppNav } from "@/components/AppNav";
import { BrandMark } from "@/components/BrandMark";
import { LanguageSwitch } from "@/components/LanguageSwitch";
import { Mascot } from "@/components/Mascot";
import { PillLink } from "@/components/PillLink";
import { t } from "@/content/copy";
import { href, readLang } from "@/content/url";
import styles from "./PendingPage.module.css";

/** Holding page for screens built in later slices, such as /contribute. */
export function PendingPage() {
  const [searchParams] = useSearchParams();
  const lang = readLang(Object.fromEntries(searchParams));
  const onResidents = useLocation().pathname.startsWith("/contribute");

  return (
    <main className={styles.page} lang={lang}>
      <header className={styles.top}>
        <BrandMark lang={lang} />
        <LanguageSwitch />
      </header>
      <div className={styles.center}>
        <Mascot size={160} />
        <h1 className={styles.title}>{t("pendingTitle", lang)}</h1>
        <PillLink
          to={href("/", { lang: lang === "en" ? "en" : undefined })}
          icon="back"
          tone="plain"
        >
          {t("backToMap", lang)}
        </PillLink>
      </div>
      {onResidents && (
        <div className={styles.nav}>
          <AppNav lang={lang} current="residents" />
        </div>
      )}
    </main>
  );
}
