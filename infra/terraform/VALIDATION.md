# ローカル検証結果

## 2026-11-10：Cloud Run再デプロイ・PR前検証

- Docker linux/amd64 build・Artifact Registry push成功。
- タグ: `admin-20261110002854-b574f67`
- digest: `sha256:89a47f21a0d318eb8d08316cdb9424221353b24fd8a1f32a45fdf78bdeab3645`
- push結果とArtifact Registryから取得したdigestの一致を確認。
- 保存planのJSON比較で既存Serviceのimage以外に差分なし。
- apply成功：0 added / 1 changed / 0 destroyed。IAM・Rules変更なし。
- revision `hack26-api-00002-fxf`: Ready、トラフィック100%。
- URL: https://hack26-api-b3ghqrsk3q-an.a.run.app
- Cloud Run IAM認証をX-Serverless-Authorizationに渡して確認：
  - GET /openapi.json: 200、A・C・Dの合計7エンドポイント登録。
  - GET /api/regions: 200（実Firestore読み取り）。
  - Firebase IDトークンなしのGET /api/admin/candidates: 401。
- 適用後terraform plan: No changes。allow_public_api=false。
- Firestoreへのテスト書き込みは未実施。実書き込み成功の証跡は今回の検証範囲にはない。
- 管理者実ユーザーでの成功・403、採否更新、Emulator結合テスト9件は後続確認。
- state・tfvars・バックアップ・plan・秘密情報はGit管理対象外。
- PR前にpytestを再実行：443 passed / 9 skipped。Ruff check・format、Terraform fmt・validate成功。

以下は過去の検証時点の記録。

## 2026-11-10：機能D取り込み後

- Terraform変更を4a31017へ保護後、origin/main a16945aをb574f67でmerge。競合なし。
- PR #31のmerge a4474e2を確認。アプリコードの独自変更なし。
- pytest: 443 passed / 9 skipped（Firestore Emulator未設定）。
- ruff check / format --check: 成功（35 files）。
- terraform fmt -check -recursive / validate、git diff --check: 成功。
- Docker linux/amd64 build: 成功、hack26-fastapi:local。
- 一時コンテナのHTTP OpenAPIでA/Cの3本とDの4本を確認。
- 未認証GET /api/admin/candidates、GET /api/admin/rulesは401。コンテナ停止済み。
- Firebase Admin SDK 7.7.0のissuer検証とアプリのauth_time有限数値・未来日時検証を確認。
  署名付きJWTテストで不正issuer/auth_time等を拒否。実Firebaseユーザーでの確認は未実施。
- IAM5権限とFIREBASE_PROJECT_IDは対応済み。allow_public_api=falseを維持。
- state・tfvarsの検証前後のSHA256は一致。
- GCP変更 / Docker push / Terraform plan・applyは未実施。

以下は過去時点の記録（現在のデプロイ状態を示すものではない）。

実施日: 2026-11-09（Asia/Tokyo）

## Security Rules統合後の検証

- fmt / init / validate: 成功。Google provider 7.46.2を継続使用。
- Rules GET: cloud.firestoreは404。releases.list / rulesets.listは成功・空。
- Hosting GET: 既存site hack26-project、releases.listは成功・空。
- 新規rules-review.tfplan: 5 add / 0 change / 0 destroy。
  カスタムロール、API用IAM member、Rules API管理、Ruleset、Releaseを作成予定。
- deploy_api=false / allow_public_api=false。Cloud Runは作成対象外。
- state listは既存6件のまま。検証前後のstate SHA256は同一：
  `64740E3E2B0FC2ECB2148725D4D4E034AA7347015ACF4D523FFA1014C4086544`
- 既存bootstrap.tfplanは変更前の計画のため流用禁止。新planも適用前に再取得・レビューする。
- terraform.tfvarsは値を変えずfmtのみ実施（Git除外対象）。
- import / apply / Rules公開 / IAM変更 / Git変更操作は未実施。
- Rulesの実コンパイル・クライアント拒否・サーバーSDK実疎通は未検証。

以下は前回のA・C対応時の検証記録。

- `terraform fmt -check -recursive`: 成功
- `terraform init -input=false`: 成功（Registry通信のため権限付きで再実行）
  - Terraform 1.16.2 / windows_amd64
  - hashicorp/google 7.46.2を取得、`.terraform.lock.hcl` を生成
- `terraform validate`: 成功
- `git diff --check`: 成功
- `pytest`: 286 passed（既存backend/fastapi/.venv、Python 3.12.3）
- `ruff check .`: 成功
- `ruff format --check .`: 成功（27 files already formatted）
- state、tfvars、plan、`.terraform/` がGit除外対象であることを確認
- Docker Engine: `docker info` でDocker Desktop Linux Engineのnamed pipeが存在せず接続失敗
  - 今回はビルド・コンテナ起動を実行していない
  - Docker DesktopのLinux Engineを起動後、READMEのbuild/run/OpenAPI取得を実行する
  - 依存パッケージのインストール・コンテナ起動・HTTP疎通は未検証
  - pytestではOpenAPIへのA・Cの3エンドポイント登録を検証済み（コンテナ検証とは別）

Git: Terraform初期構成を2604b2bにコミット後、origin/main（c9263db）を競合なしでmerge。
PR #31の管理者APIは取り込んでいない。今回のIAM・公開変数・文書修正は未コミット。
`allow_public_api=false`（既定）のため公開invokerは作成対象にならない。

Terraform plan/apply、GCP API操作、イメージpush、Firestore書き込みは実施していない。
この検証はデプロイ成功やIAM実効権限を保証するものではない。
