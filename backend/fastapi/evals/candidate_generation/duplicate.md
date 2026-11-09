# duplicate:重複と該当なし

投稿が、既存のルールやまだ公開されていない候補と同じ意味のとき。AI は候補を作らず、同じ意味の相手を重複(`duplicates`)として返す。最後の1件は、ルールにならない投稿。

## duplicate-01 言い換え

- ルール:`rule_004`「町にゴミ箱はほとんどありません。ゴミは持ち帰ってください。」
- 投稿:「ゴミ箱が少ないので、出たゴミは自分で持って帰ってください。」
- 期待:同じ意味なので、候補を作らず重複として返す。言い方を変えても同じだと分かるか。

```json
{
  "post": {"text": "ゴミ箱が少ないので、出たゴミは自分で持って帰ってください。", "region": "sakai"},
  "expected": {"candidates": [], "duplicates": [{"source": "rule", "id": "rule_004"}]}
}
```

## duplicate-02 くだけた言い方

- ルール:`rule_002`「夜9時以降は住宅街で静かにお願いします。」
- 投稿:「夜9時すぎたら住宅街で騒がないで。」
- 期待:同じ意味なので、候補を作らず重複として返す。くだけた言い方でも同じだと分かるか。

```json
{
  "post": {"text": "夜9時すぎたら住宅街で騒がないで。", "region": "sakai"},
  "expected": {"candidates": [], "duplicates": [{"source": "rule", "id": "rule_002"}]}
}
```

## duplicate-03 理由つきの言い換え

- ルール:`rule_008`「現金のみのお店もあります。」
- 投稿:「現金しか使えない店があるので、少し現金を持っておくと安心です。」
- 期待:同じ意味なので、候補を作らず重複として返す。助言が付いていても新しい内容とみなさないか。

```json
{
  "post": {"text": "現金しか使えない店があるので、少し現金を持っておくと安心です。", "region": "sakai"},
  "expected": {"candidates": [], "duplicates": [{"source": "rule", "id": "rule_008"}]}
}
```

## duplicate-04 英語の投稿

- ルール:`rule_003`「芝生広場にゴミを残さないでください。」
- 投稿:「Don't leave your trash on the grass in the park.」
- 期待:同じ意味なので、候補を作らず重複として返す。英語の投稿でも同じだと分かるか。

```json
{
  "post": {"text": "Don't leave your trash on the grass in the park.", "region": "sakai"},
  "expected": {"candidates": [], "duplicates": [{"source": "rule", "id": "rule_003"}]}
}
```

## duplicate-05 ほぼ同じ文

- ルール:`rule_007`「駅前の道路に車を停めないでください。」
- 投稿:「駅前の道路に駐車しないでください。」
- 期待:ほぼ同じ文なので、候補を作らず重複として返す。

```json
{
  "post": {"text": "駅前の道路に駐車しないでください。", "region": "sakai"},
  "expected": {"candidates": [], "duplicates": [{"source": "rule", "id": "rule_007"}]}
}
```

## duplicate-06 既存の候補と同じ

- 既存の候補:`post_a_1`「商店街の中では自転車を降りて押して歩いてください。」
- 投稿:「商店街では自転車を降りて押してください。」
- 期待:まだ公開されていない既存の候補と同じ意味なので、重複として返す。

```json
{
  "post": {"text": "商店街では自転車を降りて押してください。", "region": "sakai"},
  "expected": {"candidates": [], "duplicates": [{"source": "candidate", "id": "post_a_1"}]}
}
```

## duplicate-07 既存の候補と同じ(言い換え)

- 既存の候補:`post_b_1`「大仙公園の芝生広場ではバーベキューをしないでください。」
- 投稿:「大仙公園の芝生でバーベキューはやめてほしい。」
- 期待:既存の候補と同じ意味なので、言い換えでも重複として返す。

```json
{
  "post": {"text": "大仙公園の芝生でバーベキューはやめてほしい。", "region": "sakai"},
  "expected": {"candidates": [], "duplicates": [{"source": "candidate", "id": "post_b_1"}]}
}
```

## duplicate-08 くだけた言い換え

- ルール:`rule_001`「住宅街の細い路地では、広がらずに歩いてください。」
- 投稿:「住宅街の狭い路地では、横に並ばずに歩いてね。」
- 期待:同じ意味なので、候補を作らず重複として返す。短く言い換えても同じだと分かるか。

```json
{
  "post": {"text": "住宅街の狭い路地では、横に並ばずに歩いてね。", "region": "sakai"},
  "expected": {
    "candidates": [],
    "duplicates": [
      {"source": "rule", "id": "rule_001"}
    ]
  }
}
```

## duplicate-09 2つのルールに同時に重複

- ルール:`rule_003`「芝生広場にゴミを残さないでください。」
- ルール:`rule_004`「町にゴミ箱はほとんどありません。ゴミは持ち帰ってください。」
- 投稿:「芝生広場にゴミを残さず、ゴミは持ち帰ってください。」
- 期待:2つのルールと同じ意味なので、候補を作らず両方を重複として返す。

```json
{
  "post": {"text": "芝生広場にゴミを残さず、ゴミは持ち帰ってください。", "region": "sakai"},
  "expected": {
    "candidates": [],
    "duplicates": [
      {"source": "rule", "id": "rule_003"},
      {"source": "rule", "id": "rule_004"}
    ]
  }
}
```

## duplicate-10 該当なし

- ルール:関係するものはない
- 投稿:「今日は天気が良くて古墳がきれいでした。」
- 期待:ルールになる内容がないので、候補も重複も返さない。

```json
{
  "post": {"text": "今日は天気が良くて古墳がきれいでした。", "region": "sakai"},
  "expected": {"candidates": [], "duplicates": []}
}
```
