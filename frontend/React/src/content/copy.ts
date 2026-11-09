import type { IconName } from "@/components/Icon";
import type { Category, Lang, Localised } from "./types";

/** Placeholder product name. */
export const appName: Localised = { ja: "マナビ", en: "Manabi" };

export const categoryOrder: Category[] = ["manners", "transport", "living"];

export const categories: Record<Category, { icon: IconName; label: Localised }> = {
  manners: { icon: "sign", label: { ja: "マナー", en: "Manners" } },
  transport: { icon: "bus", label: { ja: "交通", en: "Transport" } },
  living: { icon: "shop", label: { ja: "暮らし", en: "Living" } },
};

const strings = {
  search: { ja: "地域を検索", en: "Search an area" },
  searchLabel: { ja: "地域名", en: "Area name" },
  language: { ja: "言語", en: "Language" },
  explore: { ja: "探す", en: "Explore" },
  residents: { ja: "地元の方", en: "Residents" },
  primaryNav: { ja: "メイン", en: "Main" },
  results: { ja: "検索結果", en: "Results" },
  sample: { ja: "サンプル", en: "Sample" },
  rules: { ja: "件", en: "rules" },
  updated: { ja: "更新", en: "Updated" },
  openGuide: { ja: "ガイドを開く", en: "Open guide" },
  collapse: { ja: "小さくする", en: "Collapse" },
  showOnMap: { ja: "地図で見る", en: "Show on map" },
  backToMap: { ja: "地図に戻る", en: "Back to map" },
  close: { ja: "閉じる", en: "Close" },
  locate: { ja: "現在地を表示", en: "Show my location" },
  locateDenied: { ja: "位置情報はオフです", en: "Location is off" },
  deniedTitle: { ja: "位置情報がオフです", en: "Location is off" },
  deniedBody: { ja: "地域名で探せます", en: "Search by area instead" },
  emptyTitle: { ja: "見つかりませんでした", en: "Nothing found" },
  emptyBody: { ja: "別の地域名で試してください", en: "Try another area name" },
  errorTitle: { ja: "地図を表示できません", en: "Map unavailable" },
  retry: { ja: "もう一度", en: "Try again" },
  loading: { ja: "読み込み中", en: "Loading" },
  categoriesNav: { ja: "カテゴリ", en: "Categories" },
  pendingTitle: { ja: "準備中です", en: "Coming soon" },
} satisfies Record<string, Localised>;

export type CopyKey = keyof typeof strings;

export const t = (key: CopyKey, lang: Lang) => strings[key][lang];
