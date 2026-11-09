export type Lang = "ja" | "en";
export type Category = "manners" | "transport" | "living";

export type Localised = Record<Lang, string>;

/** A place on the map that a rule is about. */
export type Pin = {
  name: Localised;
  /** Position on the placeholder map, as a percentage of its width and height. */
  x: number;
  y: number;
};

/** One published rule. Mirrors the team's public JSON format (id, region, statement, updated_at). */
export type Rule = {
  id: string;
  region: string;
  category: Category;
  statement: Localised;
  updatedAt: string;
  pin?: Pin;
};

export type Region = {
  id: string;
  name: Localised;
  /** Fictional sample data is always labelled as such in the UI. */
  sample: boolean;
};
