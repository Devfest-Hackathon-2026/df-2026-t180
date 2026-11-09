export type Lang = "ja" | "en";
export type Category = "manners" | "transport" | "living";

export type Localised = Record<Lang, string>;

/** Optional location on a rule, as agreed with the backend: Post, Candidate and Rule get lat/lng. */
export type LatLng = { lat: number; lng: number };

/** One published rule. Mirrors the team's public JSON format (id, region, statement, updated_at). */
export type Rule = {
  id: string;
  region: string;
  /** UI field, not yet in the backend schema: drives the Manners / Transport / Living tabs. */
  category: Category;
  statement: Localised;
  updatedAt: string;
  /** Only rules with a location get a pin on the map; all rules appear in the regional guide. */
  location?: LatLng;
  /** UI field, not yet in the backend schema: the place name shown as the sheet title. */
  place?: Localised;
};

export type PinnedRule = Rule & { location: LatLng; place: Localised };

export type Region = {
  id: string;
  name: Localised;
  /** The prefecture it belongs to, shown under the title (e.g. 大阪府 / Osaka). */
  parent: Localised;
  /** Sample data is always labelled as such in the UI. */
  sample: boolean;
  center: LatLng;
  zoom: number;
};
