import { type FormEvent, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { AdminHeader } from "@/components/AdminHeader";
import { Icon } from "@/components/Icon";
import { ta } from "@/content/admin";
import { href, readLang } from "@/content/url";
import styles from "./AdminLoginPage.module.css";

/**
 * Admin sign-in (機能D). Email and password only; accounts are added in the Firebase console, so
 * there is no sign-up. Mocked for now: any non-empty email and password continue to the queue.
 * ?state=error previews the wrong-password message.
 */
export function AdminLoginPage() {
  const [searchParams] = useSearchParams();
  const params = Object.fromEntries(searchParams);
  const lang = readLang(params);
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tried, setTried] = useState(false);
  const failed = params.state === "error";
  const missing = tried && (!email.trim() || !password);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTried(true);
    if (!email.trim() || !password) return;
    navigate(href("/admin/candidates", { lang: lang === "en" ? "en" : undefined }));
  }

  return (
    <main className={styles.page} lang={lang}>
      <AdminHeader lang={lang} />
      <form className={styles.card} onSubmit={onSubmit} noValidate>
        <h1 className={styles.title}>{ta("loginTitle", lang)}</h1>

        {failed && (
          <p className={styles.error} role="alert">
            {ta("signInFailed", lang)}
          </p>
        )}

        <label className={styles.field}>
          <span className={styles.label}>{ta("email", lang)}</span>
          <input
            className={styles.input}
            type="email"
            autoComplete="username"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={(tried && !email.trim()) || undefined}
            required
          />
        </label>

        <label className={styles.field}>
          <span className={styles.label}>{ta("password", lang)}</span>
          <input
            className={styles.input}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            aria-invalid={(tried && !password) || undefined}
            required
          />
        </label>

        {missing && (
          <p className={styles.error} role="alert">
            {lang === "ja" ? "入力してください" : "Please fill in both fields"}
          </p>
        )}

        <button type="submit" className={styles.submit}>
          <span>{ta("signIn", lang)}</span>
          <span className={styles.circle} aria-hidden="true">
            <Icon name="arrowUpRight" size={18} strokeWidth={2.4} />
          </span>
        </button>
      </form>
    </main>
  );
}
