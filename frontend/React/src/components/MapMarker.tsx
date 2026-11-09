import { Link } from "react-router";
import { categories } from "@/content/copy";
import type { Category, Lang } from "@/content/types";
import { CategoryIcon } from "./CategoryIcon";
import styles from "./MapMarker.module.css";

type Props = {
  name: string;
  category: Category;
  lang: Lang;
  to: string;
  selected?: boolean;
  dimmed?: boolean;
  /** Position on the placeholder map, in percent. Omit when Google Maps positions the marker. */
  position?: { x: number; y: number };
  /**
   * On Google Maps the marker element itself takes the tap and keyboard focus, so the pin is
   * drawn as plain content there instead of a nested link.
   */
  asContent?: boolean;
};

export function MapMarker(props: Props) {
  const { name, category, lang, to, selected = false, dimmed = false, position, asContent } = props;
  const pin = (
    <span className={styles.pin}>
      <span className={styles.dot}>
        <CategoryIcon category={category} size={18} />
      </span>
      <span className={styles.name} aria-hidden="true">
        {name}
      </span>
    </span>
  );

  if (asContent) {
    return (
      <span
        className={styles.marker}
        data-category={category}
        data-selected={selected || undefined}
        data-dimmed={dimmed || undefined}
      >
        {pin}
      </span>
    );
  }

  return (
    <Link
      className={styles.marker}
      to={to}
      style={position ? { left: `${position.x}%`, top: `${position.y}%` } : undefined}
      data-placed={position ? "" : undefined}
      data-category={category}
      data-selected={selected || undefined}
      data-dimmed={dimmed || undefined}
      aria-current={selected ? "true" : undefined}
      aria-label={`${name}, ${categories[category].label[lang]}`}
      preventScrollReset
    >
      {pin}
    </Link>
  );
}
