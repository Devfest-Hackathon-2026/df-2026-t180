import type { PinnedRule, Region, Rule } from "./types";

/**
 * Sample data for the demo region (Sakai, Osaka). The rules are illustrative, labelled as samples
 * in the UI, and positions are approximate. Replaced by GET /api/regions/{id}/rules.
 */
export const regions: Region[] = [
  {
    id: "sakai",
    name: { ja: "堺市", en: "Sakai" },
    parent: { ja: "大阪府", en: "Osaka" },
    sample: true,
    center: { lat: 34.5705, lng: 135.4765 },
    zoom: 14,
  },
];

export const rules: Rule[] = [
  {
    id: "rule_001",
    region: "sakai",
    category: "manners",
    statement: {
      ja: "拝所では静かにお参りしてください。柵の中には入れません。",
      en: "Please be quiet at the worship place. The fenced area is off limits.",
    },
    updatedAt: "2026-11-06",
    location: { lat: 34.5612, lng: 135.4873 },
    place: { ja: "仁徳天皇陵古墳 拝所", en: "Daisen Kofun worship place" },
  },
  {
    id: "rule_002",
    region: "sakai",
    category: "manners",
    statement: {
      ja: "夜9時以降は住宅街で静かにお願いします。",
      en: "Please keep quiet in residential streets after 9 pm.",
    },
    updatedAt: "2026-11-04",
  },
  {
    id: "rule_003",
    region: "sakai",
    category: "manners",
    statement: {
      ja: "芝生広場にゴミを残さないでください。",
      en: "Please leave no rubbish on the park lawns.",
    },
    updatedAt: "2026-11-01",
    location: { lat: 34.5566, lng: 135.4842 },
    place: { ja: "大仙公園", en: "Daisen Park" },
  },
  {
    id: "rule_004",
    region: "sakai",
    category: "manners",
    statement: {
      ja: "町にゴミ箱はほとんどありません。ゴミは持ち帰ってください。",
      en: "There are few bins in town. Please take your rubbish with you.",
    },
    updatedAt: "2026-10-28",
  },
  {
    id: "rule_005",
    region: "sakai",
    category: "transport",
    statement: {
      ja: "駅前のバス乗り場は行き先ごとに分かれています。乗る前に番号を確認してください。",
      en: "Bus stops outside the station are split by destination. Check the stop number first.",
    },
    updatedAt: "2026-11-07",
    location: { lat: 34.5753, lng: 135.4832 },
    place: { ja: "堺東駅 バス乗り場", en: "Sakai-higashi Sta. bus stops" },
  },
  {
    id: "rule_006",
    region: "sakai",
    category: "transport",
    statement: {
      ja: "路線バスでは交通系ICカードが使えます。",
      en: "Transit IC cards work on local buses.",
    },
    updatedAt: "2026-11-02",
  },
  {
    id: "rule_007",
    region: "sakai",
    category: "transport",
    statement: {
      ja: "駅前の道路に車を停めないでください。",
      en: "Please don't park on the road outside the station.",
    },
    updatedAt: "2026-10-30",
    location: { lat: 34.5813, lng: 135.465 },
    place: { ja: "堺駅前", en: "Outside Sakai Sta." },
  },
  {
    id: "rule_008",
    region: "sakai",
    category: "living",
    statement: {
      ja: "現金のみのお店もあります。",
      en: "Some shops take cash only.",
    },
    updatedAt: "2026-11-05",
    location: { lat: 34.5741, lng: 135.4756 },
    place: { ja: "山之口商店街", en: "Yamanokuchi shopping street" },
  },
  {
    id: "rule_009",
    region: "sakai",
    category: "living",
    statement: {
      ja: "夜間は公園の駐車場が閉まります。",
      en: "The park car park closes at night.",
    },
    updatedAt: "2026-11-03",
    location: { lat: 34.5779, lng: 135.4593 },
    place: { ja: "大浜公園", en: "Ohama Park" },
  },
  {
    id: "rule_010",
    region: "sakai",
    category: "living",
    statement: {
      ja: "ゴミは決められた日の朝に出してください。",
      en: "Put rubbish out on the morning of its collection day.",
    },
    updatedAt: "2026-10-26",
  },
];

export const pinnedRules = rules.filter((rule): rule is PinnedRule =>
  Boolean(rule.location && rule.place),
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
