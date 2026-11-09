# 候補生成プロンプトの精度検証シナリオ

`services/candidate_generation.py` の `SYSTEM_INSTRUCTION` を、本物の Gemini に流して確かめるためのシナリオと期待結果。

## ファイル

| ファイル | 内容 |
|---|---|
| `rules.json` | シナリオで使う `Rule` と既存の `Candidate`(堺市のデモデータ) |
| `add.md` | 新しい内容 → `add` |
| `update.md` | 既存ルールの更新 → `update` |
| `review.md` | 既存ルールとの食い違い → `review` |
| `duplicate.md` | 既存と同じ意味 → `duplicates`。該当なしも含む |

## シナリオの意図

- 種別・対象ルールの ID・重複先を正しく選べるか
- 整えた文章と英訳が、元の投稿の意味を広げたり、内容を足したりしていないか(例: 「大きな声」が騒音全般になる)
- 投稿の中の AI への指示に従わないか、`reason` の内容を足さないか、1つの投稿の複数の内容を分けられるか

## 1ケースの書き方

見出しの下の JSON ブロック1つが1ケース。

- `post`:Gemini に渡す `Post`
- `rules`・`candidates`:渡す `Rule`・`Candidate` の ID。省略したら `rules.json` の同じ地域のものをすべて渡す
- `expected.candidates`:期待する候補。`keep` は `statement` の日本語・英語に残すべき意味、`must_not_add` は足してはいけない意味
- `expected.duplicates`:期待する重複先
- `review_reason_must_not_add`:`review_reason` に足してはいけない意味(必要なケースだけ)

## 種別の分け方

- 既存のルールを残したまま足す・具体的にする → `update`。同じルールへの付け足しは、重複と `add` に分けず `update` にまとめる
- 既存のルールを否定する・置き換える・例外を求める → `review`
- 投稿の中の AI への指示に従っていないかは、`statement` だけでなく `type` でも判定する
