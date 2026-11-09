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

## 起動とチェック

```sh
npm install
npm run dev
```

チェック: `npm run lint`、`npm run format:check`、`npm run build`

ルールは静的なサンプルデータ(堺市)です。`.env` に `VITE_GOOGLE_MAPS_API_KEY` があれば Google マップを表示し、キーがない・使えない場合は代わりの静的な地図を表示します。画面の状態は URL で切り替えられます。一覧とデザインの方針は [docs/design/README.md](docs/design/README.md) にあります。

## デモ用の現在地

発表や録画のときは、アドレスに `?demo=1` を付けて開くと、現在地ボタンが位置情報の許可を求めずに堺市の中心付近(堺市役所のあたり)を現在地として表示します。

- オン: `http://localhost:5173/?demo=1`
- オフ: `http://localhost:5173/?demo=0`(タブを閉じてもオフに戻ります)
- 一度オンにすると、同じタブの中では画面を移動してもオンのままです
