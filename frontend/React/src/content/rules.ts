import type { Region, Rule } from "./types";

/** Fictional sample data. Replaced by GET /api/regions/{id}/rules once the API is ready. */
export const regions: Region[] = [
  { id: "midorigawa", name: { ja: "緑川町", en: "Midorigawa" }, sample: true },
];

export const rules: Rule[] = [
  {
    id: "rule_001",
    region: "midorigawa",
    category: "manners",
    statement: {
      ja: "竹林の路地の奥は私道です。写真は入口から撮ってください。",
      en: "The bamboo alley is a private road. Please take photos from the entrance.",
    },
    updatedAt: "2026-11-06",
    pin: { name: { ja: "竹林の路地", en: "Bamboo Alley" }, x: 42, y: 34 },
  },
  {
    id: "rule_002",
    region: "midorigawa",
    category: "manners",
    statement: {
      ja: "夜9時以降は住宅街で静かにお願いします。",
      en: "Please keep quiet in residential streets after 9 pm.",
    },
    updatedAt: "2026-11-04",
  },
  {
    id: "rule_003",
    region: "midorigawa",
    category: "manners",
    statement: {
      ja: "川沿いの小道では自転車を押して歩いてください。",
      en: "Please walk your bike along the riverside lane.",
    },
    updatedAt: "2026-11-01",
    pin: { name: { ja: "川沿いの小道", en: "Riverside Lane" }, x: 38, y: 62 },
  },
  {
    id: "rule_004",
    region: "midorigawa",
    category: "manners",
    statement: {
      ja: "町にゴミ箱はほとんどありません。ゴミは持ち帰ってください。",
      en: "There are few bins in town. Please take your rubbish with you.",
    },
    updatedAt: "2026-10-28",
  },
  {
    id: "rule_005",
    region: "midorigawa",
    category: "transport",
    statement: {
      ja: "東通りのバスは、午後は1時間に1本です。",
      en: "Buses from East St. run once an hour in the afternoon.",
    },
    updatedAt: "2026-11-07",
    pin: { name: { ja: "東通りバス停", en: "East St. Bus Stop" }, x: 60, y: 40 },
  },
  {
    id: "rule_006",
    region: "midorigawa",
    category: "transport",
    statement: {
      ja: "バスは前のドアから乗ります。交通系ICカードが使えます。",
      en: "Board the bus at the front door. Transit IC cards work.",
    },
    updatedAt: "2026-11-02",
  },
  {
    id: "rule_007",
    region: "midorigawa",
    category: "transport",
    statement: {
      ja: "駅前の道路に車を停めないでください。",
      en: "Please don't park on the road outside the station.",
    },
    updatedAt: "2026-10-30",
  },
  {
    id: "rule_008",
    region: "midorigawa",
    category: "living",
    statement: {
      ja: "朝市は現金のみの店が多く、正午に閉まります。",
      en: "Most morning-market stalls are cash only and close at noon.",
    },
    updatedAt: "2026-11-05",
    pin: { name: { ja: "朝市通り", en: "Market Street" }, x: 50, y: 53 },
  },
  {
    id: "rule_009",
    region: "midorigawa",
    category: "living",
    statement: {
      ja: "古井戸の水は飲めません。",
      en: "The water in the old well is not safe to drink.",
    },
    updatedAt: "2026-11-03",
    pin: { name: { ja: "古井戸の広場", en: "Old Well Square" }, x: 62, y: 68 },
  },
  {
    id: "rule_010",
    region: "midorigawa",
    category: "living",
    statement: {
      ja: "商店の多くは水曜日が定休日です。",
      en: "Many shops are closed on Wednesdays.",
    },
    updatedAt: "2026-10-26",
  },
];

export const pinnedRules = rules.filter((rule): rule is Rule & { pin: NonNullable<Rule["pin"]> } =>
  Boolean(rule.pin),
);

export const findRegion = (id: string | undefined) => regions.find((region) => region.id === id);

/** Latest update across a region's rules, as YYYY-MM-DD. */
export const lastUpdated = (regionId: string) =>
  rules
    .filter((rule) => rule.region === regionId)
    .map((rule) => rule.updatedAt)
    .sort()
    .at(-1) ?? "";

/** 2026-11-07 → 2026.11.07 */
export const formatDate = (iso: string) => iso.replaceAll("-", ".");
