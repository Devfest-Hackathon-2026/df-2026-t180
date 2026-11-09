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
  areaWide: { ja: "地域全体", en: "Whole area" },
  byPlace: { ja: "場所ごと", en: "By place" },
  nearest: { ja: "近い順", en: "Nearest first" },
  here: { ja: "ここ", en: "Here" },
  newest: { ja: "新しい順", en: "Newest first" },
  backToMap: { ja: "地図に戻る", en: "Back to map" },
  close: { ja: "閉じる", en: "Close" },
  locate: { ja: "現在地を表示", en: "Show my location" },
  locateDenied: { ja: "位置情報はオフです", en: "Location is off" },
  locating: { ja: "現在地を探しています", en: "Finding your location" },
  youAreHere: { ja: "現在地", en: "You are here" },
  locateFailed: { ja: "現在地を取得できませんでした", en: "Couldn't find your location" },
  backTo: { ja: "に戻る", en: "Back to " },
  deniedTitle: { ja: "位置情報がオフです", en: "Location is off" },
  deniedBody: { ja: "地域名で探せます", en: "Search by area instead" },
  emptyTitle: { ja: "見つかりませんでした", en: "Nothing found" },
  emptyBody: { ja: "別の地域名で試してください", en: "Try another area name" },
  errorTitle: { ja: "地図を表示できません", en: "Map unavailable" },
  retry: { ja: "もう一度", en: "Try again" },
  loading: { ja: "読み込み中", en: "Loading" },
  categoriesNav: { ja: "カテゴリ", en: "Categories" },
  pendingTitle: { ja: "準備中です", en: "Coming soon" },
  formTitle: { ja: "地元のルールを教えてください", en: "Share a local rule" },
  fieldRegion: { ja: "地域", en: "Area" },
  fieldRegionPlaceholder: { ja: "選んでください", en: "Choose an area" },
  fieldText: { ja: "ルール・お願い", en: "Rule or request" },
  fieldTextPlaceholder: {
    ja: "例：夜9時以降は静かにしてほしい",
    en: "e.g. Please keep quiet after 9 pm",
  },
  fieldReason: { ja: "理由", en: "Why" },
  fieldReasonPlaceholder: {
    ja: "例：住宅街で声が響くため",
    en: "e.g. Voices carry in the narrow streets",
  },
  fieldPlace: { ja: "場所", en: "Place" },
  required: { ja: "必須", en: "Required" },
  pickPlace: { ja: "地図で場所を選ぶ", en: "Pick on the map" },
  pickHint: {
    ja: "地図を動かして、ピンを場所に合わせてください",
    en: "Move the map to put the pin on the place",
  },
  usePlace: { ja: "この場所にする", en: "Use this place" },
  placeChosen: { ja: "場所を選びました", en: "Place chosen" },
  removePlace: { ja: "場所を外す", en: "Remove place" },
  cancel: { ja: "やめる", en: "Cancel" },
  submit: { ja: "送信する", en: "Send" },
  errorRequired: { ja: "入力してください", en: "Please fill this in" },
  errorRegion: { ja: "地域を選んでください", en: "Please choose an area" },
  sendFailed: { ja: "送信できませんでした", en: "Could not send" },
  sendFailedBody: { ja: "時間をおいてもう一度お試しください", en: "Please try again in a moment" },
  thanksTitle: { ja: "ありがとうございます", en: "Thank you" },
  thanksBody: {
    ja: "管理者が確認したあと、地域のガイドに載ります",
    en: "Once an admin checks it, it will appear in the area guide",
  },
  postAnother: { ja: "もう1件送る", en: "Send another" },
  sampleNotSent: {
    ja: "サンプル表示のため、実際には送信されていません",
    en: "This is a sample run, so nothing was actually sent",
  },
} satisfies Record<string, Localised>;

export type CopyKey = keyof typeof strings;

export const t = (key: CopyKey, lang: Lang) => strings[key][lang];
