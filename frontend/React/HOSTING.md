# Firebase Hosting準備（未デプロイ）

## 引き継ぎの開始点・作業境界（2026-11-10）

この4ファイルだけはPR #37に依存せずmainにマージできる。設定追加だけでは公開されない。
**本番HostingデプロイはPR #37の接続問題解消と、umeさん担当の位置情報フロント対応を
確認するまで保留する。** 未マージPRを独断でmerge・cherry-pickして公開しない。

| 対象             | 現状・担当者が守ること                                                                        |
| ---------------- | --------------------------------------------------------------------------------------------- |
| Cloud Run        | hack26-api、東京、一般公開済み。revision hack26-api-00002-fxf                                 |
| 管理者API        | ユーザー報告で実環境401・管理者200・非管理者403確認済み                                       |
| Firestore        | (default)、東京。ブラウザ直接アクセスはRules全拒否。FastAPIはIAMで操作                        |
| Hosting          | 既存site hack26-project、まだ未デプロイ                                                       |
| Terraform        | stateは元担当者のローカルのみ。他メンバーは新規stateでapplyしない                             |
| Reactのみの変更  | Hostingの再ビルド・再配信。通常Cloud Run・Terraform更新不要                                   |
| バックエンド変更 | 稼働OpenAPIとの差を確認し、別承認でCloud Run再デプロイ要否を判断                              |
| 機能B            | 自動候補生成のFirestore連携・CLI・Job/Schedulerは別途対応。投稿だけでは候補は自動生成されない |

元担当者不在でインフラ変更が必要なら、まずstateの安全な受け渡し・管理主体を確定する。
この手順書だけを根拠にTerraformを初期化して同名リソースを作らない。
API/認証テスト用のローカル未追跡スクリプトはこのPRに含めないので、以下の手順はそれに依存しない。

設定はReactディレクトリ内で完結し、Terraform・ローカルstateを変更しない。
Firebase CLIはこのディレクトリを作業ディレクトリにして使用する。

- `.firebaserc`: 既存project `hack26-project`。
- `firebase.json`: 既存site `hack26-project`、publicは `dist`。
- ViteはoutDir未指定。`npm run build`（tsc -b && vite build）の出力は `dist`。
- `/api/**` → Cloud Run `hack26-api` / `asia-northeast1` を最初に指定。
- 最後の `**` → `/index.html` はReact SPA用。Hosting以外のリソース設定は含めない。
- `.firebase/` と `dist/` はGit対象外。秘密情報・認証鍵をdistへコピーしない。

## ビルド時設定

Viteはビルド時に環境変数を埋め込む。既存 `.env` はGit除外のまま使用する。
`.env.production` やシェル環境変数がある場合はそちらの上書きにも注意する。

| 変数                      | 用途                                              |
| ------------------------- | ------------------------------------------------- |
| VITE_FIREBASE_API_KEY     | Firebase WebアプリのAPIキー                       |
| VITE_FIREBASE_AUTH_DOMAIN | hack26-project.firebaseapp.com                    |
| VITE_FIREBASE_PROJECT_ID  | hack26-project                                    |
| VITE_FIREBASE_APP_ID      | 既存hack26-webのアプリID                          |
| VITE_GOOGLE_MAPS_API_KEY  | Maps JavaScript API用Webキー                      |
| VITE_GOOGLE_MAP_ID        | 既存地図ID                                        |
| VITE_API_BASE_URL         | 未設定または空。同一オリジンの/apiを利用          |
| VITE_API_PROXY            | 開発用Vite proxyのみ。本番Hostingには利用されない |

Firebase Web設定・Maps Webキーはブラウザ配信を前提とする。サービスアカウント鍵、
パスワード、ID/access/refresh tokenをVITE変数に設定しない。
現在の管理者クライアントは空のAPI_BASE_URLで相対パスを使用する。
一般向けの投稿・ガイド接続はPR #37未マージのため、現mainではモック／サンプルが残る。
PR #37と地図・投稿位置のフロント対応がmainに揃うまで本番公開しない。

2026-11-10の公開Cloud Run OpenAPIをGETしてPost・Candidate・Ruleにlocationがあることを確認。
PR #35のバックエンド対応は稼働イメージに含まれる。実データへの投稿テストは行っていない。

## 公開前チェック

1. 必要PRのmergeを再確認し、既存変更を保護して最新mainの実装を取得する。
2. `npm ci`、`npm run build`、`npm test` を実行する。
   現在のNode 24.13.0にはjsdom等のengine警告が出るため、Node 24.15以上の対応環境で再確認する。
3. APIキーの本番HTTPリファラー許可を担当者が確認する。必要な候補は
   `https://hack26-project.web.app`、`https://hack26-project.web.app/*`、
   `https://hack26-project.firebaseapp.com`、`https://hack26-project.firebaseapp.com/*`。
   実際の制限を無断で解除・変更しない。
4. Firebase Consoleの既存サイト・対象projectを確認する。承認後のみこのディレクトリで
   `firebase deploy --only hosting --project hack26-project` を実行する。
5. Hosting URLのHTML・静的アセット、SPA直接アクセス、`/api/regions` の200、
   管理者APIの未認証401・管理者200・非管理者403、地図表示を確認する。

Hosting rewriteは認証を追加するものではなく、FirebaseトークンはFastAPIで検証する。
Authorizationヘッダーの到達と管理者API応答も本番確認する。
同一オリジン接続によりブラウザCORS設定には依存しない。
今回デプロイは実施しておらず、Hosting上のrewrite・静的配信の実動作は未検証。

## PR #37のAPI契約調査・修正担当への引き継ぎ

調査対象: PR #37 head `e313d9ff0fbd11f1a8b9e9a5fb9421d5cf1ab47d`（OPEN）と
稼働中の `https://hack26-api-b3ghqrsk3q-an.a.run.app/openapi.json`。
PRが更新されたら再調査する。本PRでは機能コードを変更していない。

| 比較箇所                            | 確認結果・必要な対応                                                                                                                                                                     |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| src/api/posts.ts                    | POST /api/posts、text/region必須、reason任意、201の{id}はAPIと一致。URLや基本JSONの不一致は確認できない                                                                                  |
| posts.ts / pages/ContributePage.tsx | 地図選択locationを送らない。APIは既にlocation:{lat,lng}を受理。NewPost型・送信body・sendPost呼び出しへlocation引き継ぎが必要                                                             |
| hooks/useRegionRules.ts             | GET /api/regions/{region_id}/rulesの配列・statement・updated_atは一致。ただしApiRuleと変換処理がlocation・last_reviewed_atを取り込まない。位置情報を保持し、表示要件に応じ確認日時も扱う |
| pages/HomePage.tsx                  | apiLive時mapRules=[]で実データのピンが常に消える。取得した位置付きルールからピンを作る処理が必要                                                                                         |
| content/types.ts / content/rules.ts | PinnedRuleはplace・categoryも必須だがAPIのRuleは両方を持たない。推測でDB項目を足さず、位置だけある場合のピン表示名・分類のUIフォールバックを担当者と決める                               |
| HomePage.tsx / ContributePage.tsx   | regionsは固定サンプル。GET /api/regionsは{id,name:{ja,en}}のみ。地域IDが実DBと一致するか確認し、API地域一覧と地図center/zoom等のUIメタデータの結び付けを決める                           |
| api/adminAuth.tsのadminLive         | FirebaseキーとprojectIdがないと投稿・ガイドもサンプルへ切替。APIが正常でも「通信していない」状態になる。ビルド時設定とNetwork要求有無を確認                                              |
| VITE_API_BASE_URL / Vite proxy      | 空なら同一オリジン/api。本番ではserver.proxyは動かずHosting rewriteが必要。localhostや別ホストを埋め込まない                                                                             |
| useRegionRules.tsのcache            | セッション内で再取得しない。管理者更新後の画面は再読み込みする。必要なら更新・再取得方針をフロント担当が修正                                                                             |

updated_atはUTC日時であり、PRのJST日付変換自体は契約に合う。locationがない投稿も合法なので、
送信からlocationが落ちる問題は必ずしも422にはならず「保存に成功したがピンがない」形で現れる。
これらの静的解析だけでは、報告された接続失敗の唯一の原因を断定できない。
APIへ直接正しいGETが通るのに画面が失敗する場合は次の順で切り分ける。

1. DevTools Networkで実際のRequest URL・method・statusを確認。トークン・メール・投稿本文を共有ログに貼らない。
2. 要求なし: apiLive用のビルド設定を確認。HTML応答: /apiがSPAへ落ちていないか確認。
3. 404: URLやregion/rulesパスを確認。200空配列: region IDと実データの一致を確認。
4. 422: OpenAPIとbodyを比較。text/regionは空白不可、reasonは空文字を送らず省略、locationはlat[-90,90]/lng[-180,180]。
5. CORS/接続拒否: 別ホスト・localhost指定を確認。本番は相対パスへ戻し、無断でCORSを緩めない。
6. 500: Cloud Runログを権限のある担当者が確認。IAM・実DBのスキーマ不整合も候補。勝手にデータ修正しない。

フロント担当が追加すべきテスト（本PRでは機能実装・テストを追加しない）:

- fetchモックで投稿bodyのlocation保持、未選択時省略、201成功、422/500/通信失敗時の入力保持を確認。
- GETのlocationあり/null、UTC日付、空配列・エラー、地域切替を検証。
- 実ルールのピン生成、place/categoryなしの表示、選択ピンとガイドの一致を確認。
- Firebase設定あり/なしとAPI_BASE_URL空の要求先を確認。後述の本番投稿確認は別途データ書込承認が必要。

## 他メンバーの準備・必要権限

Nodeは依存がサポートする24.15以上の24系等、npmとFirebase CLIを用意する。
Firebase CLIはチームで使用バージョンを揃える。必要なら `npm install -g firebase-tools`。
これはローカルツールの準備であり、firebase initで既存設定を上書きしない。

| 作業               | 必要な権限・準備                                                                                                                                                                |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Hosting配信        | プロジェクト参加、Firebase Hosting Admin（roles/firebasehosting.admin）とFirebase CLI用API Keys Viewer（roles/serviceusage.apiKeysViewer）を基準に管理者が承認。Owner全体は不要 |
| Cloud Runの参照    | 必要に応じCloud Run Viewer。公開APIのGET自体にGoogle IAMトークンは不要                                                                                                          |
| Mapsキー制限編集   | apikeys.keys.get/update等を持つ担当者。API Keys Adminは広いため担当者側で最小化。Hosting担当に自動付与しない                                                                    |
| Firebase認証テスト | 既存管理者・非管理者のメール/パスワード。管理者追加・権限変更は管理担当が別途承認                                                                                               |
| データの確認       | 必要に応じ読み取り権限をDB担当へ依頼。ブラウザSDK直接読取を許可しない                                                                                                           |
| Cloud Run再配信    | Hosting権限とは別。Artifact Registry push、Cloud Run更新、実行SA actAsと既存state管理者との調整が必要                                                                           |

権限不足は管理者へ依頼し、この手順を使って勝手にIAMを追加しない。
公式: [Firebaseの配信権限](https://firebase.google.com/docs/projects/iam/roles-predefined-product)、
[Cloud Run rewrite](https://firebase.google.com/docs/hosting/cloud-run)。

## 実行手順：問題修正後のHostingデプロイ

以下は**条件成立後の引き継ぎ用**。今回実行するデプロイコマンドではない。

1. PR #37と位置情報の担当PRについて、修正内容・レビュー・mainへのmergeを確認する。
   既存作業を安全に保護したcheckoutで取得し、未マージheadを本番に使わない。
2. Reactディレクトリで既存Firebase Web設定とMapsキーを.envへ設定する。
   値はFirebase Consoleの既存hack26-web設定、MapsキーはGCP認証情報から権限のある担当者が取得。
   envはチャット・ソースへ貼らず、VITE_API_BASE_URLは空にする。
3. Maps担当が前述の2つのHostingドメイン（ルートと/*）をWebリファラー許可へ追加する。
   既存localhost制限・API制限を維持し、Maps JavaScript APIとmapIdの互換性を確認する。
4. Firebase AuthenticationのAuthorized domainsに利用するHostingドメインがあるか管理担当が確認する。
   不足時は別承認で修正し、ログイン方式や管理者ユーザーを勝手に変更しない。

```powershell
cd frontend/React
npm ci
npm run build
npm test
firebase login
firebase projects:list
firebase hosting:sites:list --project hack26-project
```

対象siteとprojectが合うこと、dist/index.htmlとassetsが存在することを確認する。
firebase.jsonにはhostingだけがある。API rewriteが先、SPAが最後であることを再確認する。
ビルドしたcommit・CLI/Nodeバージョン・日時を記録し、秘密情報は記録しない。
担当者が公開条件を確認・承認してからのみ実行する。

```powershell
firebase deploy --only hosting --project hack26-project
```

React更新だけならこれで完結する。Cloud Runの再配信・Terraform applyは実施しない。
バックエンド変更も必要なら先にDB/API契約の互換性を担当者と確認し、既存stateの管理者が
Cloud Runの再配信を別作業で行う。新しいstateでapplyしない。

## 結合テストと完了基準

配信後、以下の読み取り確認は認証ヘッダーなしで実行する。本文は表示しない。

```powershell
$base = 'https://hack26-project.web.app'
foreach ($path in @('/', '/api/regions', '/api/admin/candidates', '/api/admin/rules')) {
  try { $r = Invoke-WebRequest ($base + $path) -UseBasicParsing; $status = [int]$r.StatusCode }
  catch { if (-not $_.Exception.Response) { throw }; $status = [int]$_.Exception.Response.StatusCode }
  Write-Host "$path HTTP $status"
}
```

- `/` は200でHTML。HTMLが参照するJS/CSS/fontのNetworkが200、Consoleエラーなし。
- 実際のSPAルート `/admin`（ログイン）と `/contribute` へ直接アクセスし、React画面になること。
- `/api/regions` は200かつJSON。実在する地域IDで `/api/regions/{id}/rules` も200かつJSON配列。
- Cloud Runの `/openapi.json` でAPI契約を確認する。Hosting直下の `/openapi.json` はAPIへrewriteされない。
- 管理者GET2本は未認証401。管理画面で既存管理者を対話ログインし200、既存非管理者で403。
  Authorizationの到達を確認するがトークンをコピー・出力・永続化しない。Firebaseキー未設定のサンプルモードを成功と誤認しない。
- PATCH2本の未認証/非管理者拒否はbackendのモックテストで確認する。本番の既存IDへPATCHしない。
- 地図タイル・AdvancedMarker・位置付き公開ルールのピン/ガイドを確認。位置なしルールも一覧に残ること。
- 投稿→候補→管理者採用→公開ルール反映の一連の確認はデータ作成・更新を伴う。
  DB担当が専用テストデータ・環境・書込許可を用意した後のみ行い、既存データを無断で変更/削除しない。
  機能Bは未稼働なので投稿から候補が自動生成される前提にしない。別途バッチ担当と調整する。
- 問題があれば公開完了とせず、NetworkのURL・status・再現手順（秘密情報除外）を担当者へ共有。
  Hostingへ既存の正常リリースがある場合のみConsoleのロールバックを承認後に利用する。
  初回配信には正常な旧版がない可能性があるため、存在を確認せずロールバック成功を想定しない。

## この設定PRでの検証範囲

HostingのJSON構造、rewrite順、実ビルド出力dist、型チェック・Vite build、既存Vitestを確認する。
これは現在のmain相当の検証であり、PR #37の接続機能の検証成功を意味しない。
Cloud Run・Terraform・state・tfvarsは変更せず、Hosting deployも行わない。
