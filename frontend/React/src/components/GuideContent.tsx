import { Link } from "react-router";
import { categories, categoryOrder, t } from "@/content/copy";
import { formatDate, rules } from "@/content/rules";
import type { Category, Lang, LatLng, Region, Rule } from "@/content/types";
import type { Params } from "@/content/url";
import { distanceKm } from "@/hooks/useMyLocation";
import { CategoryIcon } from "./CategoryIcon";
import { Icon } from "./Icon";
import styles from "./GuideContent.module.css";

type Props = {
  region: Region;
  lang: Lang;
  tab: Category;
  focusedId?: string;
  /** Builds a link to the current screen with some params changed. */
  linkTo: (patch: Params) => string;
  /** Reference point for "nearest first": the tapped pin, or the visitor when location is on. */
  origin?: LatLng;
};

/** 0.12 km → "120 m", 1.24 km → "1.2 km". */
const formatDistance = (km: number) =>
  km < 1 ? `${Math.max(10, Math.round((km * 1000) / 10) * 10)} m` : `${km.toFixed(1)} km`;

type TabsProps = Pick<Props, "region" | "lang" | "tab" | "linkTo">;

/**
 * The Manners / Transport / Living tabs with each category's count. Rendered by the sheet in its
 * fixed header, outside the scroll area, so they never move while the rules scroll.
 */
export function GuideTabs({ region, lang, tab, linkTo }: TabsProps) {
  const regionRules = rules.filter((rule) => rule.region === region.id);
  return (
    <nav className={styles.tabs} aria-label={t("categoriesNav", lang)}>
      {categoryOrder.map((category) => (
        <Link
          key={category}
          className={styles.tab}
          data-category={category}
          to={linkTo({ tab: category })}
          aria-current={category === tab ? "page" : undefined}
          replace
          preventScrollReset
        >
          <CategoryIcon category={category} size={18} />
          <span>{categories[category].label[lang]}</span>
          <span className={styles.count}>
            {regionRules.filter((rule) => rule.category === category).length}
          </span>
        </Link>
      ))}
    </nav>
  );
}

/** A region's published rules for one category tab, as a readable document. */
export function GuideContent(props: Props) {
  const { region, lang, tab, focusedId, linkTo, origin } = props;
  const regionRules = rules.filter((rule) => rule.region === region.id);
  const shown = regionRules.filter((rule) => rule.category === tab);
  // Rules without a place apply to the whole area: a short fixed list first.
  const areaWide = shown.filter((rule) => !rule.location);
  // Place rules: nearest first from the pin or the visitor, otherwise newest first.
  const distance = (rule: Rule) =>
    origin && rule.location ? distanceKm(origin, rule.location) : undefined;
  const byPlace = shown
    .filter((rule) => rule.location)
    .sort((a, b) =>
      origin ? distance(a)! - distance(b)! : b.updatedAt.localeCompare(a.updatedAt),
    );

  const item = (rule: Rule, index: number) => {
    const km = distance(rule);
    return (
      <li
        key={rule.id}
        id={rule.id}
        className={styles.rule}
        data-focused={rule.id === focusedId || undefined}
      >
        <span className={styles.number} aria-hidden="true">
          {String(index + 1).padStart(2, "0")}
        </span>
        <div className={styles.body}>
          <p className={styles.statement}>{rule.statement[lang]}</p>
          <div className={styles.ruleMeta}>
            <time dateTime={rule.updatedAt}>{formatDate(rule.updatedAt)}</time>
            {rule.location && rule.place && (
              <Link
                className={styles.pinLink}
                to={linkTo({ spot: rule.id, region: undefined, sheet: undefined })}
                aria-label={`${t("showOnMap", lang)}: ${rule.place[lang]}`}
                preventScrollReset
              >
                <Icon name="pin" size={16} />
                {rule.place[lang]}
              </Link>
            )}
            {km !== undefined && (
              <span className={styles.distance}>
                {km < 0.02 ? t("here", lang) : formatDistance(km)}
              </span>
            )}
          </div>
        </div>
      </li>
    );
  };

  return (
    <div className={styles.guide} data-category={tab}>
      <section className={styles.doc} aria-labelledby="tab-heading">
        <h3 className="sr-only" id="tab-heading">
          {categories[tab].label[lang]}
        </h3>
        {areaWide.length > 0 && (
          <div className={styles.group}>
            <h4 className={styles.groupLabel}>{t("areaWide", lang)}</h4>
            <ol className={styles.rules}>{areaWide.map((rule, i) => item(rule, i))}</ol>
          </div>
        )}
        {byPlace.length > 0 && (
          <div className={styles.group}>
            <h4 className={styles.groupLabel}>
              {t("byPlace", lang)}
              <span className={styles.sortNote}>{t(origin ? "nearest" : "newest", lang)}</span>
            </h4>
            <ol className={styles.rules}>
              {byPlace.map((rule, i) => item(rule, areaWide.length + i))}
            </ol>
          </div>
        )}
      </section>
    </div>
  );
}
