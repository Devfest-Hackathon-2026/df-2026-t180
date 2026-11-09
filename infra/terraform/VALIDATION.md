# ローカル検証結果

実施日: 2026-11-09（Asia/Tokyo）

- `terraform fmt -check -recursive`: 成功
- `terraform init -backend=false -input=false`: 成功
  - Terraform 1.16.2 / windows_amd64
  - hashicorp/google 7.46.2を取得、`.terraform.lock.hcl` を生成
- `terraform validate`: 成功
- `git diff --check`: 成功
- state、tfvars、plan、`.terraform/` がGit除外対象であることを確認
- Dockerビルド: 未完了。ローカルのDocker Desktop Linux Engineのnamed pipeが存在せず接続失敗
  - 実行コマンド: `docker build --platform linux/amd64 -t hack26-fastapi:local backend/fastapi`
  - Docker DesktopのLinux Engineを起動後、同コマンドで再検証が必要
  - 依存パッケージのインストール・コンテナ起動・HTTP疎通は未検証

Terraform plan/apply、GCP API操作、イメージpush、Firestore書き込みは実施していない。
この検証はデプロイ成功やIAM実効権限を保証するものではない。
