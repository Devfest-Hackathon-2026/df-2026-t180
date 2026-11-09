import { type FormEvent, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { adminLive as apiLive } from "@/api/adminAuth";
import { sendPost } from "@/api/posts";
import { BottomBar } from "@/components/BottomBar";
import { BrandMark } from "@/components/BrandMark";
import { Icon } from "@/components/Icon";
import { LanguageSwitch } from "@/components/LanguageSwitch";
import { MapView } from "@/components/MapView";
import { Mascot } from "@/components/Mascot";
import { PillLink } from "@/components/PillLink";
import { Select } from "@/components/Select";
import { StateCard } from "@/components/StateCard";
import { t } from "@/content/copy";
import { regions } from "@/content/rules";
import type { LatLng } from "@/content/types";
import { href, readLang, type Params } from "@/content/url";
import styles from "./ContributePage.module.css";

const MAX = 300;

/**
 * Resident submission (機能A): text and area are required, reason and place are optional.
 * When the app is connected to the project (Firebase configured in .env), sending goes to
 * POST /api/posts; otherwise it is a sample run and the thank-you screen says nothing was sent.
 */
export function ContributePage() {
  const [searchParams] = useSearchParams();
  const params: Params = Object.fromEntries(searchParams);
  const lang = readLang(params);
  const navigate = useNavigate();
  const langParam = { lang: lang === "en" ? "en" : undefined };

  const [region, setRegion] = useState("");
  const [text, setText] = useState("");
  const [reason, setReason] = useState("");
  const [location, setLocation] = useState<LatLng>();
  const [picking, setPicking] = useState(false);
  const [centre, setCentre] = useState<LatLng>();
  const [tried, setTried] = useState(false);
  const [sending, setSending] = useState(false);
  const [sendFailed, setSendFailed] = useState(false);
  const regionRef = useRef<{ focus: () => void }>(null);
  const textRef = useRef<HTMLTextAreaElement>(null);

  const regionError = tried && !region;
  const textError = tried && !text.trim();
  const pickRegion = regions.find((item) => item.id === region) ?? regions[0];

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTried(true);
    if (!region) return regionRef.current?.focus();
    if (!text.trim()) return textRef.current?.focus();
    if (sending) return;
    if (apiLive) {
      setSending(true);
      setSendFailed(false);
      try {
        await sendPost({ region, text, reason, location });
      } catch {
        setSendFailed(true);
        setSending(false);
        return;
      }
      setSending(false);
    }
    // Sent: clear everything so "Send another" starts from an empty form. (Switching language
    // doesn't come through here, so inputs are kept when the visitor changes JP/EN.)
    setRegion("");
    setText("");
    setReason("");
    setLocation(undefined);
    setCentre(undefined);
    setPicking(false);
    setTried(false);
    navigate(href("/contribute", langParam, { step: "done" }));
  }

  if (params.step === "done") {
    return (
      <main className={styles.page} lang={lang}>
        <Top lang={lang} />
        <div className={styles.done}>
          <Mascot size={150} />
          <h1 className={styles.doneTitle}>{t("thanksTitle", lang)}</h1>
          <p className={styles.doneBody}>{t("thanksBody", lang)}</p>
          {!apiLive && (
            <p className={styles.sample} role="note">
              {t("sampleNotSent", lang)}
            </p>
          )}
          <div className={styles.doneActions}>
            <PillLink to={href("/", langParam)} icon="back" tone="plain">
              {t("backToMap", lang)}
            </PillLink>
            <Link className={styles.again} to={href("/contribute", langParam)}>
              {t("postAnother", lang)}
            </Link>
          </div>
        </div>
        <BottomBar lang={lang} current="residents" />
      </main>
    );
  }

  return (
    <main className={styles.page} lang={lang}>
      <Top lang={lang} />

      <form id="contribute-form" className={styles.form} onSubmit={onSubmit} noValidate>
        <h1 className={styles.title}>{t("formTitle", lang)}</h1>

        {(params.state === "error" || sendFailed) && (
          <StateCard
            title={t("sendFailed", lang)}
            body={t("sendFailedBody", lang)}
            tone="warning"
          />
        )}

        <div className={styles.field}>
          <span className={styles.label} id="region-label">
            {t("fieldRegion", lang)}
            <span className={styles.badge} data-required>
              {t("required", lang)}
            </span>
          </span>
          <Select
            id="region"
            ref={regionRef}
            labelledBy="region-label"
            value={region}
            onChange={setRegion}
            placeholder={t("fieldRegionPlaceholder", lang)}
            options={regions.map((item) => ({ value: item.id, label: item.name[lang] }))}
            invalid={regionError}
            describedBy={regionError ? "region-error" : undefined}
          />
          {regionError && (
            <p className={styles.error} id="region-error">
              {t("errorRegion", lang)}
            </p>
          )}
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="text">
            {t("fieldText", lang)}
            <span className={styles.badge} data-required>
              {t("required", lang)}
            </span>
          </label>
          <textarea
            id="text"
            ref={textRef}
            className={styles.control}
            rows={4}
            maxLength={MAX}
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder={t("fieldTextPlaceholder", lang)}
            required
            aria-invalid={textError || undefined}
            aria-describedby={textError ? "text-error text-count" : "text-count"}
          />
          <div className={styles.under}>
            {textError ? (
              <p className={styles.error} id="text-error">
                {t("errorRequired", lang)}
              </p>
            ) : (
              <span />
            )}
            <span className={styles.count} id="text-count">
              {text.length}/{MAX}
            </span>
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.label} htmlFor="reason">
            {t("fieldReason", lang)}
          </label>
          <textarea
            id="reason"
            className={styles.control}
            rows={3}
            maxLength={MAX}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder={t("fieldReasonPlaceholder", lang)}
          />
        </div>

        <div className={styles.field}>
          <span className={styles.label} id="place-label">
            {t("fieldPlace", lang)}
          </span>

          {location && !picking && (
            <div className={styles.chosen}>
              <Icon name="pin" size={18} />
              <span className={styles.chosenText}>
                {t("placeChosen", lang)}
                <span className={styles.coords}>
                  {location.lat.toFixed(4)}, {location.lng.toFixed(4)}
                </span>
              </span>
              <button
                type="button"
                className={styles.remove}
                onClick={() => setLocation(undefined)}
                aria-label={t("removePlace", lang)}
              >
                <Icon name="close" size={18} />
              </button>
            </div>
          )}

          {!location && !picking && (
            <button type="button" className={styles.pick} onClick={() => setPicking(true)}>
              <Icon name="pin" size={18} />
              {t("pickPlace", lang)}
            </button>
          )}

          {picking && (
            <div className={styles.picker} role="group" aria-labelledby="place-label">
              <p className={styles.hint}>{t("pickHint", lang)}</p>
              <div className={styles.mapBox}>
                <MapView
                  lang={lang}
                  center={location ?? pickRegion.center}
                  zoom={16}
                  pins={[]}
                  onCenterChange={setCentre}
                />
                <span className={styles.crosshair} aria-hidden="true" />
              </div>
              <div className={styles.pickActions}>
                <button
                  type="button"
                  className={styles.secondary}
                  onClick={() => setPicking(false)}
                >
                  {t("cancel", lang)}
                </button>
                <button
                  type="button"
                  className={styles.primarySmall}
                  disabled={!centre}
                  onClick={() => {
                    setLocation(centre);
                    setPicking(false);
                  }}
                >
                  {t("usePlace", lang)}
                </button>
              </div>
            </div>
          )}
        </div>
      </form>

      <BottomBar
        lang={lang}
        current="residents"
        action={
          <button
            type="submit"
            form="contribute-form"
            className={styles.send}
            aria-label={t("submit", lang)}
            aria-busy={sending || undefined}
            disabled={sending}
          >
            <Icon name="send" size={24} strokeWidth={2.2} />
          </button>
        }
      />
    </main>
  );
}

function Top({ lang }: { lang: "ja" | "en" }) {
  return (
    <header className={styles.top}>
      <BrandMark lang={lang} />
      <LanguageSwitch />
    </header>
  );
}
