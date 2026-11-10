import { categories } from "@/content/copy";
import type { Category } from "@/content/types";
import { Icon } from "./Icon";

export function CategoryIcon({ category, size = 20 }: { category: Category; size?: number }) {
  return <Icon name={categories[category].icon} size={size} />;
}
