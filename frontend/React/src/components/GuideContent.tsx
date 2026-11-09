import { Link } from "react-router";
import { categories, categoryOrder, t } from "@/content/copy";
import { formatDate, lastUpdated, rules } from "@/content/rules";
import type { Category, Lang, Region } from "@/content/types";
import type { Params } from "@/content/url";
import { CategoryIcon } from "./CategoryIcon";
import { Icon } from "./Icon";
import { Mascot } from "./Mascot";
import styles from "./GuideContent.module.css";

type Props = {
  region: Region;
  lang: Lang;
  tab: Category;
  focusedId?: string;
  /** Whether to repeat the region name; the sheet header already shows it when no pin is open. */
  showName: boolean;
  /** Builds a link to the current screen with some params changed. */
  linkTo: (patch: Params) => string;
};

/** A region's published rules as a readable document, split into category tabs. */
export function GuideContent({ region, lang, tab, focusedId, showName, linkTo }: Props) {
  const regionRules = rules.filter((rule) => rule.region === region.id);
  const shown = regionRules.filter((rule) => rule.category === tab);
  const updated = lastUpdated(region.id);

  return (
    <div className={styles.guide} data-category={tab}>
      <div className={styles.intro}>
        <div className={styles.introText}>
          {showName && <h3 className={styles.region}>{region.name[lang]}</h3>}
          <p className={styles.meta}>
            {regionRules.length} {t("rules", lang)}
            <span aria-hidden="true">·</span>
            {t("updated", lang)} <time dateTime={updated}>{formatDate(updated)}</time>
          </p>
        </div>
        <Mascot className={styles.mascot} size={96} />
      </div>

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

      <section className={styles.doc} aria-labelledby="tab-heading">
        <h3 className="sr-only" id="tab-heading">
          {categories[tab].label[lang]}
        </h3>
        <ol className={styles.rules}>
          {shown.map((rule, index) => (
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
                  {rule.pin && (
                    <Link
                      className={styles.pinLink}
                      to={linkTo({ spot: rule.id, region: undefined, sheet: undefined })}
                      aria-label={`${t("showOnMap", lang)}: ${rule.pin.name[lang]}`}
                      preventScrollReset
                    >
                      <Icon name="pin" size={16} />
                      {rule.pin.name[lang]}
                    </Link>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
