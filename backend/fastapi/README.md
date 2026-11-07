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
API キーや認証情報、環境変数の設定は不要です。

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
