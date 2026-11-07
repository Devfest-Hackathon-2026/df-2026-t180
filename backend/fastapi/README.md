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
今回は起動用の最小構成のみで、業務 API は未実装です。

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

## テスト・静的解析

```sh
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

## 構成

- `main.py`: FastAPI アプリケーション
- `api/`: API ルート（後続 PR で実装）
- `schemas/`: データスキーマ（後続 PR で実装）
- `services/`: 業務処理（後続 PR で実装）
- `repositories/`: DB 操作（後続 PR で実装）
- `tests/`: 起動確認テスト

Firestore、Gemini、Firebase Authentication の連携は後続 PR で実装します。
