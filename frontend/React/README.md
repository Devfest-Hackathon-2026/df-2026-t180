# フロントエンド

React で作ります。以下は地図と Firebase を使うための設定です。

## 環境変数

1. `.env.example` をコピーして `.env` を作る(`.env` は git に入れない)

```sh
cp .env.example .env
```

2. `.env` の空欄2つに、API キーの値を入れる

| 変数 | 値を見る場所 |
| --- | --- |
| `VITE_GOOGLE_MAPS_API_KEY` | Google Cloud コンソール →「API とサービス → 認証情報」→「Maps Platform API Key」→「キーを表示」 |
| `VITE_FIREBASE_API_KEY` | Firebase コンソール →「プロジェクトの設定 → マイアプリ → hack26-web」の `apiKey` |

## 開発サーバーのポート

地図のキーは `http://localhost:3000` と `http://localhost:5173` からしか使えません。開発サーバーはこのどちらかのポートで起動してください。

## Firebase Authentication

- ログイン方法はメール・パスワードです
- 新規登録の画面は作りません。テスト用のアカウントは、Firebase コンソールの「Authentication → ユーザー → ユーザーを追加」で作ります

## 地図

- マーカーは `AdvancedMarkerElement` を使います。地図を作るときに `mapId` に `VITE_GOOGLE_MAP_ID` を渡してください
