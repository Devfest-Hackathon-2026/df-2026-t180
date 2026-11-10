export type Lang = "ja" | "en";
export type Category = "manners" | "transport" | "living";
/** A guide tab: every rule, or one category. */
export type GuideTab = "all" | Category;

export type Localised = Record<Lang, string>;

/** Optional location on a rule, as agreed with the backend: Post, Candidate and Rule get lat/lng. */
export type LatLng = { lat: number; lng: number };

/** One published rule. Mirrors the team's public JSON format (id, region, statement, updated_at). */
export type Rule = {
  id: string;
  region: string;
  /**
   * UI field, not yet in the backend schema: drives the Manners / Transport / Living tabs. Rules
   * from the API have none yet (see #22), so they appear under 「すべて」 only.
   */
  category?: Category;
  statement: Localised;
  updatedAt: string;
  /** Only rules with a location get a pin on the map; all rules appear in the regional guide. */
  location?: LatLng;
  /** UI field, not yet in the backend schema: the place name shown as the sheet title. */
  place?: Localised;
};

export type PinnedRule = Rule & { location: LatLng; place: Localised; category: Category };

/**
 * A rule that gets a pin. Rules from the API have a location (#15) but no place name or category
 * yet (#22), so those two are optional here; the sample rules have both.
 */
export type LocatedRule = Rule & { location: LatLng };

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
