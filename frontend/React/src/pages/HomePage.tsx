import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { AppNav } from "@/components/AppNav";
import { BottomBar } from "@/components/BottomBar";
import { BrandMark } from "@/components/BrandMark";
import { Icon } from "@/components/Icon";
import { LanguageSwitch } from "@/components/LanguageSwitch";
import { LocationButton } from "@/components/LocationButton";
import { MapView, type MapPin } from "@/components/MapView";
import { SearchBar } from "@/components/SearchBar";
import { PlaceSheet } from "@/components/PlaceSheet";
import { StateCard } from "@/components/StateCard";
import { Tag } from "@/components/Tag";
import { appName, categoryOrder, t } from "@/content/copy";
import { adminLive as apiLive } from "@/api/adminAuth";
import { findRegion, pinnedRules, regions, rules } from "@/content/rules";
import type { Category, GuideTab, LatLng, Region } from "@/content/types";
import { href, readLang, type Params } from "@/content/url";
import { distanceKm, isDemoLocation, useMyLocation } from "@/hooks/useMyLocation";
import styles from "./HomePage.module.css";

/**
 * Pins come from the sample rules only. Real rules (from the API when connected) have no location
 * or place yet (#15, #22), so with a live connection the map shows no sample pins rather than
 * mixing sample places with real rules; the guide opens from search instead.
 */
const mapRules = apiLive ? [] : pinnedRules;

function searchRegions(query: string): Region[] {
  const needle = query.trim().toLowerCase();
  return regions.filter((region) => {
    const names = [region.name.ja, region.name.en];
    const pins = mapRules.filter((rule) => rule.region === region.id);
    pins.forEach((rule) => names.push(rule.place.ja, rule.place.en));
    return names.some((name) => name.toLowerCase().includes(needle));
  });
}

const isGuideTab = (value: string | undefined): value is GuideTab =>
  value === "all" || categoryOrder.includes(value as Category);

/** Params that belong to the sheet; cleared together when it closes. */
const noSheet = { spot: undefined, region: undefined, sheet: undefined, tab: undefined };

/** Search and map. Every review state lives in the URL, so it can be opened without a backend. */
export function HomePage() {
  const [searchParams] = useSearchParams();
  const params: Params = Object.fromEntries(searchParams);
  const lang = readLang(params);
  const { state, q } = params;

  const results = q ? searchRegions(q) : [];
  const selected = mapRules.find((rule) => rule.id === params.spot);
  const isLoading = state === "loading";
  const isError = state === "error";
  const isEmpty = state === "empty" || (Boolean(q) && results.length === 0);

  // Sheet: a pin opens it at half height; the guide (full) can also open straight from search.
  const sheetRegion = findRegion(selected?.region ?? params.region);
  const sheetMode = selected && params.sheet !== "full" ? "half" : "full";
  // A tapped pin opens its rule's category; opening from search shows every rule.
  const tab: GuideTab = isGuideTab(params.tab) ? params.tab : (selected?.category ?? "all");
  const sheetOpen = Boolean(sheetRegion) && !isLoading && !isError;
  const here = (patch: Params) => href("/", params, patch);

  const region = sheetRegion ?? regions[0];

  // The visitor's location. URL state=denied still previews the refused state for reviewers.
  const me = useMyLocation();
  const locationStatus = state === "denied" ? "denied" : me.status;
  // The map follows the newest request: "go to me" (location button) or "back to the region".
  const [back, setBack] = useState<{ center: LatLng; zoom?: number; key: number }>();
  const goToMe =
    me.focus && me.position
      ? { center: me.position, zoom: isDemoLocation() ? 15 : 16, key: me.focus }
      : undefined;
  const flyTo = [goToMe, back]
    .filter((target) => target !== undefined)
    .sort((a, b) => b.key - a.key)[0];
  const farFromRegion = Boolean(me.position) && distanceKm(me.position!, region.center) > 15;
  // Where the map is centred, reported when it comes to rest. The location button uses it to tell
  // "showing the visitor" from "moved elsewhere" (back to the region, or panned away).
  const [mapCentre, setMapCentre] = useState<LatLng>();
  const showingMe = Boolean(
    me.position && (mapCentre ? distanceKm(mapCentre, me.position) < 0.05 : flyTo === goToMe),
  );
  const onLocate = () => me.toggle(showingMe);

  const controls = (
    <>
      <span className={styles.wordmark} aria-hidden="true">
        {appName[lang]}
      </span>
      <LocationButton lang={lang} status={locationStatus} onClick={onLocate} />
    </>
  );
  const pins: MapPin[] = mapRules.map((rule) => ({
    id: rule.id,
    name: rule.place[lang],
    category: rule.category,
    location: rule.location,
    to: here({ ...noSheet, spot: rule.id }),
  }));

  return (
    <main className={styles.shell} lang={lang} data-sheet={sheetOpen ? sheetMode : undefined}>
      {!isError && (
        <MapView
          lang={lang}
          center={region.center}
          zoom={region.zoom}
          pins={pins}
          selectedId={selected?.id}
          dimmed={isEmpty}
          loading={isLoading}
          you={me.position}
          flyTo={flyTo}
          onCenterChange={setMapCentre}
        />
      )}

      <header className={styles.top}>
        <div className={styles.bar}>
          <div className={styles.brand}>
            <BrandMark lang={lang} as="h1" />
          </div>
          <SearchBar lang={lang} query={q} />
          <div className={styles.barNav}>
            <AppNav lang={lang} current="explore" />
          </div>
          <LanguageSwitch />
        </div>

        <div className={styles.under}>
          {me.status === "unavailable" && state !== "denied" && (
            <p className={styles.denied} role="status">
              <Icon name="locateOff" size={18} />
              <strong>{t("locateFailed", lang)}</strong>
            </p>
          )}

          {farFromRegion && flyTo === goToMe && !sheetOpen && (
            <button
              type="button"
              className={styles.backTo}
              onClick={() => setBack({ center: region.center, zoom: region.zoom, key: Date.now() })}
            >
              <Icon name="back" size={18} />
              {lang === "ja"
                ? `${region.name.ja}${t("backTo", lang)}`
                : `${t("backTo", lang)}${region.name.en}`}
            </button>
          )}

          {locationStatus === "denied" && (
            <p className={styles.denied}>
              <Icon name="locateOff" size={18} />
              <span>
                <strong>{t("deniedTitle", lang)}</strong> · {t("deniedBody", lang)}
              </span>
            </p>
          )}

          {isEmpty && <StateCard title={t("emptyTitle", lang)} body={t("emptyBody", lang)} />}

          {!isEmpty && !sheetOpen && results.length > 0 && (
            <section className={styles.results} aria-label={t("results", lang)}>
              <ul>
                {results.map((region) => (
                  <li key={region.id}>
                    <Link
                      className={styles.result}
                      to={here({ ...noSheet, region: region.id, sheet: "full" })}
                    >
                      <span className={styles.resultText}>
                        <span className={styles.resultName}>{region.name[lang]}</span>
                        <span className={styles.resultMeta}>
                          {/* Sample label and count only for sample data; real counts are in the guide. */}
                          {!apiLive && region.sample && (
                            <Tag tone="highlight">{t("sample", lang)}</Tag>
                          )}
                          {!apiLive && (
                            <>
                              {rules.filter((rule) => rule.region === region.id).length}{" "}
                              {t("rules", lang)}
                            </>
                          )}
                        </span>
                      </span>
                      <span className={styles.resultArrow} aria-hidden="true">
                        <Icon name="arrowUpRight" size={20} strokeWidth={2.4} />
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </header>

      {isLoading && (
        <p className={styles.loading} role="status">
          <span className={styles.loadingDots} aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </span>
          {t("loading", lang)}
        </p>
      )}

      {isError && (
        <div className={styles.error}>
          <StateCard title={t("errorTitle", lang)} tone="warning">
            <Link className={styles.retry} to={href("/", params, { state: undefined })}>
              {t("retry", lang)}
              <Icon name="arrow" size={18} />
            </Link>
          </StateCard>
        </div>
      )}

      {sheetOpen && sheetRegion ? (
        <PlaceSheet
          mode={sheetMode}
          region={sheetRegion}
          rule={selected}
          tab={tab}
          lang={lang}
          linkTo={here}
          closeTo={here(noSheet)}
          expandTo={here({ sheet: "full", tab })}
          collapseTo={selected ? here({ sheet: undefined }) : here(noSheet)}
          above={controls}
          me={me.position}
        />
      ) : null}

      <div className={styles.dock}>
        <div className={styles.controls}>{controls}</div>
      </div>

      {/* Phones: the shared bottom row, with the wordmark on top and the location button. */}
      <BottomBar
        className={styles.bottom}
        lang={lang}
        current="explore"
        above={
          <span className={`${styles.wordmark} ${styles.wordmarkAbove}`} aria-hidden="true">
            {appName[lang]}
          </span>
        }
        action={
          <LocationButton lang={lang} status={locationStatus} onClick={onLocate} size="row" />
        }
      />
    </main>
  );
}
