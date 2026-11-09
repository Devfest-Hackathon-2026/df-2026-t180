import { Link } from "react-router";
import { categories } from "@/content/copy";
import type { Category, Lang, Pin } from "@/content/types";
import { CategoryIcon } from "./CategoryIcon";
import styles from "./MapMarker.module.css";

type Props = {
  pin: Pin;
  category: Category;
  lang: Lang;
  to: string;
  selected?: boolean;
  dimmed?: boolean;
};

export function MapMarker({ pin, category, lang, to, selected = false, dimmed = false }: Props) {
  return (
    <Link
      className={styles.marker}
      to={to}
      style={{ left: `${pin.x}%`, top: `${pin.y}%` }}
      data-category={category}
      data-selected={selected || undefined}
      data-dimmed={dimmed || undefined}
      aria-current={selected ? "true" : undefined}
      aria-label={`${pin.name[lang]}, ${categories[category].label[lang]}`}
      preventScrollReset
    >
      <span className={styles.pin}>
        <span className={styles.dot}>
          <CategoryIcon category={category} size={18} />
        </span>
        <span className={styles.name} aria-hidden="true">
          {pin.name[lang]}
        </span>
      </span>
    </Link>
  );
}
