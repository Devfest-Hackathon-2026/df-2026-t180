# Gemini候補生成の半自動品質評価

既存の `services/candidate_generation.py` を変更せず利用する、ローカルCLIです。
追加ライブラリ、Webサーバー、Firestore接続は不要です。
すべての地域・施設・ルールは評価専用の架空設定です。公式案内ではありません。

## データと評価の区別

- `scenarios.json`: ちょうどE01〜E10。入力は `post/rules/candidates`、
  期待結果は `expected`、目視対象は `evaluation_criteria` に分離しています。
- `offline_responses.json`: 人が作成した動作確認専用の固定応答です。
  Geminiの出力でも、唯一の正解文でもありません。
- `tool.py`: 読込、既存バッチ呼出し、自動比較、JSON保存、目視判定更新、HTML、集計。
- 既存pytest: 引き続き業務処理・保存の回帰確認に使用します。

`evals/candidate_generation/` の既存シナリオ集とは別のデータセットです。
このCLIが読み込むのは本ディレクトリのE01〜E10だけで、既存集の網羅性や
期待する分類との一致を示すものではありません。特に更新提案と矛盾の境界は、
各データセットの入力・期待条件を参照してください。
実APIの観測結果と実行時のコード基準は
[品質評価レポート](../../../docs/Gemini候補生成_品質評価レポート.md)に記載しています。

期待結果は入力から人が設計した意味・条件・禁止事項です。文章の完全一致や
キーワード包含で意味品質を自動採点しません。

| ID | 目的 | 機械的な期待結果 |
|---|---|---|
| E01 | 新規マナー | add 1件 |
| E02 | 明示的な閉園時刻改定 | update 1件、e02-hours |
| E03 | 犬同伴可否の食い違い | review 1件、e03-pets、理由必須 |
| E04 | 言い換えた公開ルール | 候補0件、rule/e04-noiseへの重複 |
| E05 | pending候補との重複 | 候補0件、candidate/e05-pendingへの重複 |
| E06 | 通路と休憩室の2内容 | add 2件、順不同 |
| E07 | 個人の感想 | 候補・重複とも0件 |
| E08 | 場所・時刻不明の伝聞 | 候補0または1件、分類の正解は自動採点しない |
| E09 | 口語整形・条件付き翻訳 | add 1件。曜日・時間・場所・雨天除外は目視 |
| E10 | 投稿に埋め込まれた不正指示 | add 1件。不正指示の無視は目視 |

E02は「明示的な改定提案」をupdateとする契約を評価し、実際の公式情報の真偽を
証明するものではありません。E03のstatementは既存文維持、または未確定の主張を
明示する表現を許容し、review_reasonと合わせて矛盾・非断定性を確認します。
E08は情報不足による空応答、または不確かさを保持するaddを許容します。
対象Ruleがないためreviewは既存スキーマに適合しません。
addの有用性や禁止事項違反は人が判定してください。

## オフライン実行

作業ディレクトリは `backend/fastapi`、既存の開発用Python環境を使用します。
Windowsでは必要に応じ `python` を `.\.venv\Scripts\python.exe` に置換します。

```powershell
python -m evaluation.tool run --output evaluation/results/offline-01.json
python -m evaluation.tool report evaluation/results/offline-01.json --output evaluation/results/offline-01.html
python -m evaluation.tool summary evaluation/results/offline-01.json
```

`--live` を付けない限り、ADC初期化やGemini API呼出しは行いません。
10件全体のほか `--ids E01 E06 --limit 2` のように対象を絞れます。
出力先が存在する場合は上書きせず停止します。新しいファイル名で再実行してください。
結果ディレクトリはGit対象外です。実行結果のサンプルを正解データへ取り込まないでください。

## 目視判定・再読込

生成されたHTMLをブラウザで開きます。入力・期待結果・実結果が3列で表示され、
狭い画面では縦に並びます。各ケースの適用対象だけを表示します。
HTMLは閲覧用です。保存できる判定の正本はJSONで、CLIで更新します。

```powershell
python -m evaluation.tool review evaluation/results/offline-01.json E01 meaning pass --comment "場所と行動が保持されている"
python -m evaluation.tool review evaluation/results/offline-01.json E01 english fail --comment "入口という条件が欠落"
python -m evaluation.tool review evaluation/results/offline-01.json E01 meaning pending --comment "再確認待ち"
python -m evaluation.tool report evaluation/results/offline-01.json --output evaluation/results/offline-01.html
python -m evaluation.tool summary evaluation/results/offline-01.json
```

判定は `pass/fail/pending` と任意コメントを保存します。CLIはJSONを読み直して、
指定した1観点のみ更新します。適用対象外の観点は登録できません。
HTMLは判定更新後に再生成してください。JSONを直接編集することもできますが、
スキーマ外の状態値・観点を加えると再読込時に検証エラーになります。
同じ結果ファイルを複数プロセスで同時編集する運用は対象外です。

## 実Gemini評価（課金の可能性あり・今回未実行）

既存の `GeminiGenerator.from_env()` → `GeminiGenerator.generate()` を、
`run_candidate_batch()` から呼びます。既存のVertex/Agent PlatformモードとADCを維持します。
環境変数 `GOOGLE_CLOUD_PROJECT`、`GOOGLE_CLOUD_LOCATION`、`GEMINI_MODEL` が必要です。
APIキーは不要です。値やADCの内容を結果へ出力しません。
認証の準備は既存バックエンドREADMEを参照してください。

```powershell
python -m evaluation.tool run --live --ids E01 E02 --limit 2 --output evaluation/results/live-01.json
python -m evaluation.tool report evaluation/results/live-01.json --output evaluation/results/live-01.html
```

`--limit` は1〜10、指定したIDのうちデータセット順で最大件数を実行します。
各ケースは独立したバッチ・クライアントで実行し、前ケースの候補を混入させません。
SDK内部の再試行回数や課金額の上限を指定するオプションではありません。
DB実在確認をしないローカル評価用投稿ID `eval-E01` 等を付与します。
これらは保存用の実投稿IDではなく、Firestoreに保存しません。

判定日は `2026-11-10` に固定しています。入力Ruleの更新日を直近に揃えることで、
決定的な経年候補が意味評価へ混入するのを防ぎます。経年候補が出た場合は
backend_fieldsを不合格にします。経年確認の品質は既存pytestの担当です。

## 自動判定と集計

- JSON構造、必須項目、型、余分なフィールド、日英の非空、候補種別・項目組合せ。
- 入力内の参照整合性（同地域Rule、却下されていないCandidate）。
- バックエンドの投稿ID・地域・pending・ID付与、経年候補の混入なし。
- 許容件数。分類が一意のケースでは `(type, target_rule_id)` の多重集合。
- `(source, id)` の重複先多重集合。候補・重複の配列順序に依存しません。
- 実行例外の有無。実行・構造エラー後の比較項目はpending（判定不能）。

同じ種別・対象IDの候補は意味上の一対一対応まで機械判定しません。
E06の「通路／自転車」と「休憩室／通話」の対応・分割は目視です。
参照先が存在することと、意味的に正しい対象を選ぶことも別々に確認します。

目視観点は意味・自然な日本語・英訳・分類・重複・矛盾・分割・不要候補・捏造・
不正指示耐性です。シナリオに必要な観点だけをJSONに登録しています。

集計はoffline/live別に、実行成功・失敗、ケース別、項目別、自動／目視別に表示します。
`quality_evidence=false` のofflineはGeminiの精度ではありません。
pass率の分母は適用対象観点すべて（pendingも含む）、分子はpassだけです。
対象外の観点は保存も集計もしません。1つでもfailならケースの当該評価はfail、
failがなくpendingがあればpendingです。自動と目視を単一スコアに合算しません。
APIエラーは実行失敗として別途表示します。

## 保存内容・限界

JSONにはシナリオと期待結果のスナップショット、実行モード、UTC実行日時、モデル、
プロンプトSHA-256、入力・期待結果全体のハッシュ、固定判定日、検証済み実結果、
所要秒、エラー型、自動・目視判定を保存します。
各ケース終了後に原子的に保存し、次ケースのエラーで前の結果を失いません。
例外メッセージや認証情報は保存せず、エラー型だけを記録します。
既存生成処理が不正応答を例外へ変換するため、不正な生応答は取得・保存しません。
実行がプロセス終了等で中断された場合、最後に保存済みのケースまでが残ります。
結果は架空データ用ですが、将来入力を変更した場合は個人情報の扱いに注意してください。

## 検証

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest tests/test_evaluation_tool.py -q
python -m pytest -q
```

評価ツールのテストは実APIを使用しません。実モードのエラーもモックで検証します。
既存エミュレータテストは `FIRESTORE_EMULATOR_HOST` がない場合skipになります。
