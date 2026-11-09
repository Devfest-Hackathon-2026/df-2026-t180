import type { CSSProperties } from "react";
import { Link, useSearchParams } from "react-router";
import { AppNav } from "@/components/AppNav";
import { BrandMark } from "@/components/BrandMark";
import { Icon } from "@/components/Icon";
import { LanguageSwitch } from "@/components/LanguageSwitch";
import { LocationButton } from "@/components/LocationButton";
import { MapMarker } from "@/components/MapMarker";
import { MapPlaceholder } from "@/components/MapPlaceholder";
import { SearchBar } from "@/components/SearchBar";
import { PlaceSheet } from "@/components/PlaceSheet";
import { StateCard } from "@/components/StateCard";
import { Tag } from "@/components/Tag";
import { appName, categoryOrder, t } from "@/content/copy";
import { findRegion, pinnedRules, regions, rules } from "@/content/rules";
import type { Category, Region } from "@/content/types";
import { href, readLang, type Params } from "@/content/url";
import styles from "./HomePage.module.css";

function searchRegions(query: string): Region[] {
  const needle = query.trim().toLowerCase();
  return regions.filter((region) => {
    const names = [region.name.ja, region.name.en];
    const pins = pinnedRules.filter((rule) => rule.region === region.id);
    pins.forEach((rule) => names.push(rule.pin.name.ja, rule.pin.name.en));
    return names.some((name) => name.toLowerCase().includes(needle));
  });
}

const isCategory = (value: string | undefined): value is Category =>
  categoryOrder.includes(value as Category);

/** Params that belong to the sheet; cleared together when it closes. */
const noSheet = { spot: undefined, region: undefined, sheet: undefined, tab: undefined };

/** Search and map. Every review state lives in the URL, so it can be opened without a backend. */
export function HomePage() {
  const [searchParams] = useSearchParams();
  const params: Params = Object.fromEntries(searchParams);
  const lang = readLang(params);
  const { state, q } = params;

  const results = q ? searchRegions(q) : [];
  const selected = pinnedRules.find((rule) => rule.id === params.spot);
  const isLoading = state === "loading";
  const isError = state === "error";
  const isEmpty = state === "empty" || (Boolean(q) && results.length === 0);

  // Sheet: a pin opens it at half height; the guide (full) can also open straight from search.
  const sheetRegion = findRegion(selected?.region ?? params.region);
  const sheetMode = selected && params.sheet !== "full" ? "half" : "full";
  const tab: Category = isCategory(params.tab) ? params.tab : (selected?.category ?? "manners");
  const sheetOpen = Boolean(sheetRegion) && !isLoading && !isError;
  const here = (patch: Params) => href("/", params, patch);

  const controls = (
    <>
      <span className={styles.wordmark} aria-hidden="true">
        {appName[lang]}
      </span>
      <LocationButton lang={lang} denied={state === "denied"} />
    </>
  );

  const canvasStyle = selected
    ? ({
        "--pan-x": `${50 - selected.pin.x}%`,
        "--pan-y": `${50 - selected.pin.y}%`,
      } as CSSProperties)
    : undefined;

  return (
    <main className={styles.shell} lang={lang} data-sheet={sheetOpen ? sheetMode : undefined}>
      <div className={styles.mapRegion} data-loading={isLoading || undefined}>
        {!isError && (
          <div
            className={styles.canvas}
            data-panned={selected ? "true" : undefined}
            style={canvasStyle}
          >
            <MapPlaceholder lang={lang} />
            {!isLoading &&
              pinnedRules.map((rule) => (
                <MapMarker
                  key={rule.id}
                  pin={rule.pin}
                  category={rule.category}
                  lang={lang}
                  to={here({ ...noSheet, spot: rule.id })}
                  selected={selected?.id === rule.id}
                  dimmed={isEmpty}
                />
              ))}
          </div>
        )}
      </div>

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
          {state === "denied" && (
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
                          {region.sample && <Tag tone="highlight">{t("sample", lang)}</Tag>}
                          {rules.filter((rule) => rule.region === region.id).length}{" "}
                          {t("rules", lang)}
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
        />
      ) : null}

      <div className={styles.dock}>
        <div className={styles.controls}>{controls}</div>
      </div>

      <div className={styles.nav}>
        <AppNav lang={lang} current="explore" />
      </div>
    </main>
  );
}
