import type { Lang, Localised } from "./types";

/**
 * Admin (機能D) sample data. Mirrors the backend schemas: Candidate (with #23's `source`) and Rule
 * (with `last_reviewed_at`). Replaced by GET /api/admin/candidates once the API is ready.
 */
export type CandidateType = "add" | "update" | "review";
export type CandidateStatus = "pending" | "approved" | "rejected";

export type Candidate = {
  id: string;
  source: "post" | "stale_rule";
  postId?: string;
  region: string;
  type: CandidateType;
  status: CandidateStatus;
  /** Gemini's tidied, translated text (for review candidates: the rule as it stands). */
  statement: Localised;
  targetRuleId?: string;
  reviewReason?: string;
  /** The resident's original post, for candidates that came from a post. */
  post?: { text: string; reason?: string; place?: string; createdAt: string };
  /** The published rule this candidate would change or re-check. */
  current?: { statement: Localised; updatedAt: string; lastReviewedAt?: string };
};

export const sampleCandidates: Candidate[] = [
  {
    id: "post_101_1",
    source: "post",
    postId: "post_101",
    region: "sakai",
    type: "add",
    status: "pending",
    statement: {
      ja: "大仙公園の芝生広場ではバーベキューをしないでください。",
      en: "Please don't barbecue on the lawns in Daisen Park.",
    },
    post: {
      text: "公園の芝生でバーベキューする人がいて煙がすごい。やめてほしい。",
      reason: "近くに住宅があり、洗濯物に匂いがつくため",
      place: "大仙公園",
      createdAt: "2026-11-08T09:12:00Z",
    },
  },
  {
    id: "post_102_1",
    source: "post",
    postId: "post_102",
    region: "sakai",
    type: "add",
    status: "pending",
    statement: {
      ja: "商店街では歩きながら食べないでください。",
      en: "Please don't eat while walking in the shopping street.",
    },
    post: {
      text: "食べ歩きで店先が汚れることが多いです",
      place: "山之口商店街",
      createdAt: "2026-11-08T11:40:00Z",
    },
  },
  {
    id: "post_103_1",
    source: "post",
    postId: "post_103",
    region: "sakai",
    type: "update",
    status: "pending",
    targetRuleId: "rule_006",
    statement: {
      ja: "路線バスでは交通系ICカードが使えます。降りるときにタッチしてください。",
      en: "Transit IC cards work on local buses. Tap again when you get off.",
    },
    current: {
      statement: {
        ja: "路線バスでは交通系ICカードが使えます。",
        en: "Transit IC cards work on local buses.",
      },
      updatedAt: "2026-11-02T00:00:00Z",
    },
    post: {
      text: "降りるときもタッチが必要なのを知らない観光客が多い",
      createdAt: "2026-11-08T13:05:00Z",
    },
  },
  {
    id: "stale_rule_009_2026-11-03",
    source: "stale_rule",
    region: "sakai",
    type: "review",
    status: "pending",
    targetRuleId: "rule_009",
    reviewReason: "最終確認から3年が経過しました",
    statement: {
      ja: "夜間は公園の駐車場が閉まります。",
      en: "The park car park closes at night.",
    },
    current: {
      statement: {
        ja: "夜間は公園の駐車場が閉まります。",
        en: "The park car park closes at night.",
      },
      updatedAt: "2023-11-03T00:00:00Z",
    },
  },
  {
    id: "post_104_1",
    source: "post",
    postId: "post_104",
    region: "sakai",
    type: "review",
    status: "pending",
    targetRuleId: "rule_008",
    reviewReason: "新しい投稿と内容が食い違っています",
    statement: {
      ja: "現金のみのお店もあります。",
      en: "Some shops take cash only.",
    },
    current: {
      statement: { ja: "現金のみのお店もあります。", en: "Some shops take cash only." },
      updatedAt: "2026-11-05T00:00:00Z",
    },
    post: {
      text: "最近はほとんどのお店でカードやQR決済が使える",
      place: "山之口商店街",
      createdAt: "2026-11-08T15:20:00Z",
    },
  },
];

const strings = {
  admin: { ja: "管理者ページ", en: "Admin area" },
  adminOnly: { ja: "管理者専用！", en: "Admin only!" },
  loginTitle: { ja: "管理者ログイン", en: "Admin sign-in" },
  email: { ja: "メールアドレス", en: "Email" },
  password: { ja: "パスワード", en: "Password" },
  signIn: { ja: "ログイン", en: "Sign in" },
  signInFailed: {
    ja: "メールアドレスかパスワードが違います",
    en: "The email or password is incorrect",
  },
  signOut: { ja: "ログアウト", en: "Sign out" },
  candidates: { ja: "候補", en: "Candidates" },
  publishedRules: { ja: "公開ルール", en: "Published rules" },
  adminNav: { ja: "管理メニュー", en: "Admin menu" },
  typeAdd: { ja: "新規", en: "New" },
  typeUpdate: { ja: "更新", en: "Update" },
  typeReview: { ja: "経年確認", en: "Re-check" },
  resident: { ja: "住民", en: "Resident" },
  proposed: { ja: "公開案", en: "Draft" },
  liveNow: { ja: "公開中", en: "Live now" },
  approve: { ja: "採用", en: "Approve" },
  stillCorrect: { ja: "問題なし", en: "Still OK" },
  edit: { ja: "修正", en: "Edit" },
  reject: { ja: "却下", en: "Reject" },
  save: { ja: "保存", en: "Save" },
  cancel: { ja: "やめる", en: "Cancel" },
  undo: { ja: "元に戻す", en: "Undo" },
  approved: { ja: "採用しました", en: "Approved" },
  rejected: { ja: "却下しました", en: "Rejected" },
  confirmedOk: { ja: "確認済みにしました", en: "Marked as checked" },
  noneLeft: { ja: "確認待ちの候補はありません", en: "Nothing waiting for review" },
  editRule: { ja: "編集", en: "Edit" },
  savedRule: { ja: "保存しました", en: "Saved" },
  japanese: { ja: "日本語", en: "Japanese" },
  english: { ja: "英語", en: "English" },
  updatedAt: { ja: "更新", en: "Updated" },
} satisfies Record<string, Localised>;

export type AdminCopyKey = keyof typeof strings;

export const ta = (key: AdminCopyKey, lang: Lang) => strings[key][lang];

/** 2026-11-08T09:12:00Z → 2026.11.08 (shown in Japan time). */
export const formatJst = (iso: string) => {
  const d = new Date(new Date(iso).getTime() + 9 * 3600 * 1000);
  return d.toISOString().slice(0, 10).replaceAll("-", ".");
};
