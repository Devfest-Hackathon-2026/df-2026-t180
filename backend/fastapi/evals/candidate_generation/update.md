# update:既存ルールの更新

投稿が、既存のルールをはっきり変えたり付け足したりする提案のとき。AI はそのルールの更新の候補(`update`)を作る。

## update-01 静かにする時間を足す

- ルール:`rule_002`「夜9時以降は住宅街で静かにお願いします。」
- 投稿:「住宅街で静かにしてほしいのは、夜9時以降だけでなく朝7時前もです。」
- 期待:既存の時間を残したまま時間を足す提案なので、更新の候補(update)を作る。英訳で時間を一日中(all day)に、「静か」を騒音全般(noise)に広げない。

```json
{
  "post": {"text": "住宅街で静かにしてほしいのは、夜9時以降だけでなく朝7時前もです。", "region": "sakai"},
  "expected": {
    "candidates": [
      {"type": "update", "target_rule_id": "rule_002", "keep": ["住宅街", "静か", "夜9時以降", "朝7時前"], "must_not_add": ["一日中(all day)", "騒音全般(noise)"]}
    ],
    "duplicates": []
  }
}
```

## update-02 駐車場の閉まる時間

- ルール:`rule_009`「夜間は公園の駐車場が閉まります。」
- 投稿:「公園の駐車場は夜10時に閉まります。」
- 期待:閉まる時刻を具体的にする提案なので、更新の候補(update)を作る。

```json
{
  "post": {"text": "公園の駐車場は夜10時に閉まります。", "region": "sakai"},
  "expected": {
    "candidates": [
      {"type": "update", "target_rule_id": "rule_009", "keep": ["公園の駐車場", "夜10時に閉まる"], "must_not_add": ["開く時間", "料金"]}
    ],
    "duplicates": []
  }
}
```

## update-03 座り込まない場所を広げる

- ルール:`rule_010`「商店街のお店の前に座り込まないでください。」
- 投稿:「商店街のお店の前だけでなく、アーケードの柱のまわりにも座り込まないでください。」
- 期待:座り込まない場所を足す提案なので、更新の候補(update)を作る。「座り込まない」を英訳で「立ち止まらない(don't stop)」「うろつかない(loitering)」に広げない。

```json
{
  "post": {"text": "商店街のお店の前だけでなく、アーケードの柱のまわりにも座り込まないでください。", "region": "sakai"},
  "expected": {
    "candidates": [{"type": "update", "target_rule_id": "rule_010", "keep": ["お店の前", "アーケードの柱のまわり", "座り込まない"], "must_not_add": ["立ち止まらない(don't stop)", "うろつかない(loitering)", "飲食", "罰則"]}],
    "duplicates": []
  }
}
```

## update-04 ゴミを残さない場所を広げる

- ルール:`rule_003`「芝生広場にゴミを残さないでください。」
- 投稿:「大仙公園の芝生広場だけでなく、園内の池のまわりにもゴミを残さないでください。」
- 期待:ゴミを残さない場所を足す提案なので、更新の候補(update)を作る。英訳で公園全体(the whole park)に広げない。

```json
{
  "post": {"text": "大仙公園の芝生広場だけでなく、園内の池のまわりにもゴミを残さないでください。", "region": "sakai"},
  "expected": {
    "candidates": [{"type": "update", "target_rule_id": "rule_003", "keep": ["芝生広場", "池のまわり", "ゴミを残さない"], "must_not_add": ["公園全体(the whole park)", "罰金"]}],
    "duplicates": []
  }
}
```

## update-05 乗り場の番号の場所

- ルール:`rule_005`「駅前のバス乗り場は行き先ごとに分かれています。乗る前に番号を確認してください。」
- 投稿:「堺東駅のバス乗り場の番号は、乗り場の柱の上に書いてあります。」
- 期待:番号がどこにあるかを足す提案なので、更新の候補(update)を作る。

```json
{
  "post": {"text": "堺東駅のバス乗り場の番号は、乗り場の柱の上に書いてあります。", "region": "sakai"},
  "expected": {
    "candidates": [
      {"type": "update", "target_rule_id": "rule_005", "keep": ["バス乗り場の番号", "柱の上"], "must_not_add": ["アプリ", "時刻表"]}
    ],
    "duplicates": []
  }
}
```

## update-06 停めてはいけない場所を広げる

- ルール:`rule_007`「駅前の道路に車を停めないでください。」
- 投稿:「駅前の道路だけでなく、商店街の入口にも車を停めないでください。」
- 期待:停めない場所を足す提案なので、更新の候補(update)を作る。「車を停めない(don't park)」を英訳で「停車も禁止(no stopping)」に強めない。

```json
{
  "post": {"text": "駅前の道路だけでなく、商店街の入口にも車を停めないでください。", "region": "sakai"},
  "expected": {
    "candidates": [{"type": "update", "target_rule_id": "rule_007", "keep": ["駅前の道路", "商店街の入口", "車を停めない"], "must_not_add": ["停車も禁止(no stopping)", "自転車", "罰金", "レッカー"]}],
    "duplicates": []
  }
}
```

## update-07 広がらずに歩く場所を広げる

- ルール:`rule_001`「住宅街の細い路地では、広がらずに歩いてください。」
- 投稿:「住宅街の細い路地だけでなく、商店街の中でも広がらずに歩いてください。」
- 期待:広がらずに歩く場所を足す提案なので、更新の候補(update)を作る。「広がらずに歩く」を英訳で「立ち止まらない(don't stop)」に広げない。

```json
{
  "post": {"text": "住宅街の細い路地だけでなく、商店街の中でも広がらずに歩いてください。", "region": "sakai"},
  "expected": {
    "candidates": [{"type": "update", "target_rule_id": "rule_001", "keep": ["細い路地", "商店街の中", "広がらずに歩く"], "must_not_add": ["立ち止まらない(don't stop)", "走らない"]}],
    "duplicates": []
  }
}
```

## update-08 長話をしない

- ルール:`rule_001`「住宅街の細い路地では、広がらずに歩いてください。」
- 投稿:「住宅街の細い路地では、広がらずに歩くのに加えて、立ち止まって長話をしないでください。」
- 期待:既存の内容に行動を足す提案なので、更新の候補(update)を作る。「長話をしない」を英訳で「立ち止まらない」「うろつかない(loitering)」に広げない。

```json
{
  "post": {"text": "住宅街の細い路地では、広がらずに歩くのに加えて、立ち止まって長話をしないでください。", "region": "sakai"},
  "expected": {
    "candidates": [
      {"type": "update", "target_rule_id": "rule_001", "keep": ["細い路地", "広がらずに歩く", "立ち止まって長話をしない"], "must_not_add": ["立ち止まらない", "うろつかない(loitering)"]}
    ],
    "duplicates": []
  }
}
```

## update-09 ゴミ箱がある場所

- ルール:`rule_004`「町にゴミ箱はほとんどありません。ゴミは持ち帰ってください。」
- 投稿:「町にゴミ箱はほとんどありませんが、駅の改札内にはあります。」
- 期待:ゴミ箱がある場所を足す提案なので、更新の候補(update)を作る。「どこでも捨ててよい」に広げない。

```json
{
  "post": {"text": "町にゴミ箱はほとんどありませんが、駅の改札内にはあります。", "region": "sakai"},
  "expected": {
    "candidates": [{"type": "update", "target_rule_id": "rule_004", "keep": ["ゴミ箱はほとんどない", "駅の改札内にはある"], "must_not_add": ["どこでも捨ててよい", "コンビニ"]}],
    "duplicates": []
  }
}
```

## update-10 英語の投稿

- ルール:`rule_006`「路線バスでは交通系ICカードが使えます。」
- 投稿:「IC cards work on local buses, but you can also pay in cash. Have small change ready.」
- 期待:英語の投稿。現金も使えることを足す提案なので、更新の候補(update)を作る。

```json
{
  "post": {"text": "IC cards work on local buses, but you can also pay in cash. Have small change ready.", "region": "sakai"},
  "expected": {
    "candidates": [{"type": "update", "target_rule_id": "rule_006", "keep": ["ICカード", "現金", "小銭を用意"], "must_not_add": ["両替", "クレジットカード"]}],
    "duplicates": []
  }
}
```
