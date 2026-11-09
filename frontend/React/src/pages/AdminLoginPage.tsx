import { type FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { AdminHeader } from "@/components/AdminHeader";
import { Icon } from "@/components/Icon";
import { ManagerMascot, type ManagerState } from "@/components/ManagerMascot";
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
  const [focus, setFocus] = useState<"email" | "password">();
  const [signedIn, setSignedIn] = useState(false);
  const [pointer, setPointer] = useState({ x: 0, y: 0 });
  const mascotRef = useRef<HTMLDivElement>(null);
  const failed = params.state === "error";
  const missing = tried && (!email.trim() || !password);

  // The manager's eyes follow the pointer while nothing is focused.
  useEffect(() => {
    function onMove(event: PointerEvent) {
      const box = mascotRef.current?.getBoundingClientRect();
      if (!box) return;
      const clamp = (n: number) => Math.max(-1, Math.min(1, n));
      setPointer({
        x: clamp((event.clientX - (box.left + box.width / 2)) / 240),
        y: clamp((event.clientY - (box.top + box.height / 2)) / 240),
      });
    }
    window.addEventListener("pointermove", onMove);
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  const state: ManagerState = signedIn
    ? "happy"
    : focus === "password"
      ? "password"
      : missing || (failed && !email && !password)
        ? "error"
        : focus === "email"
          ? "email"
          : "idle";
  // Typing an email: look down at the field and read along as it grows.
  const look = state === "email" ? { x: -0.8 + Math.min(email.length, 28) / 17.5, y: 1 } : pointer;

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTried(true);
    if (!email.trim() || !password) return;
    setFocus(undefined);
    setSignedIn(true);
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.setTimeout(
      () => navigate(href("/admin/candidates", { lang: lang === "en" ? "en" : undefined })),
      reduce ? 0 : 600,
    );
  }

  return (
    <main className={styles.page} lang={lang}>
      <AdminHeader lang={lang} />
      <div className={styles.stage}>
        <div className={styles.wrap}>
          <div className={styles.manager} ref={mascotRef}>
            <ManagerMascot state={state} look={look} />
          </div>
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
                onFocus={() => setFocus("email")}
                onBlur={() => setFocus(undefined)}
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
                onFocus={() => setFocus("password")}
                onBlur={() => setFocus(undefined)}
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
        </div>
      </div>
    </main>
  );
}
