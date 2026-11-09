# バックエンド

Python 3.12 を使用します。以下のコマンドは `backend/fastapi/` で実行してください。

## セットアップ

```sh
python -m venv .venv
```

仮想環境を有効化します。

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS / Linux:

```sh
source .venv/bin/activate
```

開発用依存関係をインストールします。

```sh
python -m pip install -r requirements-dev.txt
```

実行のみの場合は `requirements.txt` を使用してください。

## 起動

```sh
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

<http://127.0.0.1:8000/docs> で API ドキュメント、
<http://127.0.0.1:8000/openapi.json> で OpenAPI 定義を確認できます。

## Google Cloud の認証(Gemini を呼ぶとき)

Gemini は Agent Platform 経由で呼びます。API キーは使わず、各自の Google アカウントで認証します。

1. [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) をインストールする
2. プロジェクト `hack26-project` に招待された Google アカウントで、次を一度だけ実行する

```sh
gcloud auth login
gcloud config set project hack26-project
gcloud auth application-default login
gcloud auth application-default set-quota-project hack26-project
```

3. `.env.example` をコピーして `.env` を作る(`.env` は git に入れない)

```sh
cp .env.example .env
```

Cloud Run では、実行用のサービスアカウントに `roles/aiplatform.user`(Agent Platform User)を付けます。

## 管理者 API（機能D）

`/api/admin/*` は `Authorization: Bearer <Firebase ID トークン>` が必要です。
FastAPI が Firebase Admin SDK でトークンを検証し、`admins` コレクションに UID が登録されている場合だけ許可します。

| 状態 | ステータス |
| --- | --- |
| トークンがない・無効（署名・`iss`・`aud`・期限・`sub`・`auth_time` など） | 401（設定がなくても 401） |
| 有効だが `admins` に登録がない | 403 |
| `FIREBASE_PROJECT_ID`（未設定なら `GOOGLE_CLOUD_PROJECT`）がない | 503 |
| Google の公開鍵を取得できない（一時的な通信障害） | 503 |

公開鍵は `Cache-Control` の `max-age` に従ってキャッシュします。

管理者の追加は Firestore コンソールで行います。
`admins` にドキュメントID = Firebase UID のドキュメントを作り、`firebase_uid` と `employee_name` を入れます。
取り消すときは `admins` からそのドキュメントを削除します。次のリクエストから 403 になります。
Firebase Authentication 側の無効化・トークン失効は確認していません（`check_revoked=False`。理由は `services/firebase_auth.py`）。

| メソッド | パス | 内容 |
| --- | --- | --- |
| GET | `/api/admin/candidates` | 候補の一覧。`status`（既定 `pending`、`all` で全件）・`type`・`region` で絞り込み。元の投稿（`post`）と対象ルールの現在の内容（`current`。`version` を含む）を添える。候補の生成後にルールが変わっていれば `rule_changed_since_generated` が `true`（#39） |
| PATCH | `/api/admin/candidates/{id}` | `{"action": "approve" \| "reject", "statement"?: {ja, en}, "expected_version"?: string}` |
| GET | `/api/admin/rules` | 公開ルールの一覧（`region` で絞り込み）。新しく更新されたものから。各ルールに `version` を含む |
| PATCH | `/api/admin/rules/{id}` | `{"statement": {ja, en}, "expected_version": string}`。`updated_at` を更新 |

### 古い画面からの上書きを防ぐ（version）

既存のルールを書き換える操作（update・review の採用と、ルールの直接編集）では、画面で表示していたルールの `version` を `expected_version` に入れて送ります。
候補の採否では `current.version`、直接編集ではルール一覧の `version` です。

- その後ルールが変わっていれば 409 で、候補もルールも書き込みません。画面を読み直してからやり直します
- 成功したときの応答にも新しい `version` が入ります。続けて編集するときはこれを使います
- update・review の採用で `expected_version` がなければ 422。add の採用と却下では使いません
- 同時の変更が続いて確定できないときも 409 です

候補の `statement` は Gemini の提案文のまま残し、採用で実際に公開・確認した文は `decided_statement` に入ります（却下では空）。

`version` はルールの保存内容から計算する値で、管理者の書き込みでは必ず変わります（「問題なし」でも `last_reviewed_at` が進むため）。

### 採否のステータス

| 状態 | ステータス |
| --- | --- |
| 候補が見つからない | 404 |
| 判断済み | 409 |
| 対象ルールが存在しない・候補と地域が違う（採用時） | 409 |
| 対象ルールが存在しない候補の却下 | 200（不要な候補を片付けられる） |

採否の扱い（#24）と日時の役割は `services/admin_decisions.py` の先頭に書いています。
既存ドキュメントは変わったフィールドだけを更新するので、モデルにないフィールドも残ります。
一覧のページングをしない理由は `repositories/admin.py` の先頭に書いています。

## テスト・静的解析

```sh
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

### Firestore Emulator での結合テスト

`tests/test_admin_firestore.py` は、同時実行・再試行・コミット失敗を本物の Firestore（Emulator）で確かめます。
`FIRESTORE_EMULATOR_HOST` がないときはスキップします。Java と Node.js が必要です。

```sh
npx firebase-tools emulators:start --only firestore --project demo-admin
# 別のターミナルで
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 python -m pytest tests/test_admin_firestore.py
```

## 構成

- `main.py`: FastAPI アプリケーション
- `api/`: API ルート
- `schemas/`: データスキーマ
- `services/`: 業務処理（後続 PR で実装）
- `repositories/`: DB 操作
- `tests/`: テスト

Firestore、Firebase Authentication の連携は後続 PR で実装します。
Geminiによる候補生成は以下のバッチ関数から利用できます。

## 機能B：候補生成バッチ

`services/candidate_generation.py` の `run_candidate_batch` を呼び出します。
投稿APIから独立した処理です。毎週水曜日13:00（Asia/Tokyo）の起動設定は
Terraform側で別途実装します。公開バッチAPIは追加していません。

以下は実際のGemini APIを呼ぶ例です（課金が発生し得るため、実行前に確認してください）。
依存関係のインストール、上記ADC設定と `.env` の設定が必要です。
Google Gen AI SDKをAgent Platformモードで使用し、APIキーは使用しません。

```python
from schemas.post import Post
from services.candidate_generation import GeminiGenerator, run_candidate_batch

generator = GeminiGenerator.from_env()
try:
    result = run_candidate_batch(
        posts=[Post(text="夜間は静かにしてほしい", region="sakai")],
        post_ids=["existing_post_id"],  # 実際に保存された投稿のドキュメントID
        rules=[],  # 同じ地域を含む公開ルールの一覧
        candidates=[],  # 既存候補の一覧
        generator=generator,
    )
    # resultを呼び出し元で保存する。住民の投稿をログに出力しない。
finally:
    generator.close()
```

Geminiへの入力JSON例:

```json
{
  "post": {"text": "夜間は静かにしてほしい", "region": "sakai", "reason": null},
  "rules": [],
  "candidates": []
}
```

Geminiの出力JSON例（ID、地域、採否状態はバックエンドが設定）:

```json
{
  "candidates": [{
    "type": "add",
    "statement": {"ja": "夜間は静かにお過ごしください。", "en": "Please keep quiet at night."},
    "target_rule_id": null,
    "review_reason": null
  }],
  "duplicates": []
}
```

- `post_ids` に入力投稿と同じ順序で実在する投稿IDを渡します。
  件数不一致・空ID・同じバッチ内の重複IDは拒否します。
  `StoredPost` も入力でき、処理状態や保存日時は変更しません。
  `result.posts` は `post_index`・`post_id`・生成候補・重複理由を返します。
  投稿IDの実在確認と永続化は呼び出し元の責務です。
- Geminiは同じ地域の公開ルールと、却下済みを除く既存候補との意味比較を行います。
  同じバッチで先に生成した候補も後続投稿の比較に含めます。
  重複の場合は `duplicates` に `source`（`rule` / `candidate`）、`id`、`reason` を返します。
- `add` は対象ルールなし、`update` と `review` は対象ルール必須です。
  `review` は確認理由も必須で、対象の公開ルールがなければ生成しません。
  対象ルール・重複先が同じ地域の入力データに存在するかも検証します。
- 古さはGeminiの推測に依存せず、公開ルールの更新日から暦年で判定します。
  `STALE_RULE_YEARS` の既定値は3で、`stale_years` 引数で変更できます。
  2月29日の周年は、平年では2月28日とします。既定の当日はUTCの日付です。
  Ruleの `updated_at` と任意の `last_reviewed_at` は `UtcDatetime` で検証します。
  UTC以外の日時・naive datetime・日付のみの値は拒否し、サービス内では変換しません。
  日時の例は `"2026-11-09T00:00:00Z"` です。FirestoreではUTC Timestampで扱う方針です。
  該当ルールの更新・確認候補が既に `pending` なら追加の経年確認候補を作りません。
  投稿がなくても `result.stale_candidates` に経年確認の `Candidate` を返します。
  `source="stale_rule"`・`post_id=None`・`type="review"`・`status="pending"` とし、
  IDは `stale_{rule_id}_{確認期限日（YYYY-MM-DD）}` で決定します。
  期限は `updated_at` と `last_reviewed_at` の新しいUTC日時の日付から計算します。
  同一バッチ内の重複は防ぎますが、確認後の再生成防止には機能Dによる
  `last_reviewed_at` の更新が必要です。採用・却下状態から確認日時を推測しません。
  本バッチはDB保存・承認・Ruleの更新を行わず、架空の投稿IDも生成しません。
- 不正JSON、存在しない参照、不正な候補、API失敗は `CandidateGenerationError` として失敗し、
  部分結果は返しません。API呼び出しは投稿ごとに順番に行います。
  投稿に該当する内容がなければ、`candidates` と `duplicates` が両方空でも正常結果です。
- 入力モデルは変更せず、新規候補を `{post_id}_{連番}` のID・`pending`で返します。
  連番は各投稿の1から始め、`post_id` はGeminiに決めさせません。
  バッチをまたぐ投稿の重複処理防止、Firestore保存、公開反映、承認の二重実行防止は未実装です。
- モックテストはプロンプトと結果の取り扱いを検証します。
  Geminiによる翻訳・意味判断の実際の品質は、別途実接続で確認が必要です。
