# ローカル検証結果

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
