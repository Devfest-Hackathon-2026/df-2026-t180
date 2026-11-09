# GCPインフラ（MVP）

既存 `hack26-project` を利用し、東京 `asia-northeast1` にAPIを配置する。
このREADMEのapply・pushは**将来、GCP変更の事前承認を得た後に実行する手順**。
開発ルールに従い、API有効化を含む変更内容をDiscordで事前相談する。

## 管理範囲

| 対象 | 定義 |
| --- | --- |
| 必要API | Artifact Registry / Cloud Run / IAM / Firestore。destroy時も無効化しない |
| Artifact Registry | 東京、Docker形式、`hack26-backend`、削除防止 |
| API実行SA | `hack26-api`、鍵ファイルなし、ADC |
| Firestore IAM | カスタムロール `hack26PostWriter`、`datastore.entities.create` のみ |
| Cloud Run Service | `hack26-api`、0〜2インスタンス、1 CPU / 512 MiB、認証必須 |
| Cloud Run Job / Scheduler | **未定義・未作成**。後述の設計のみ |

既存Firestore `(default)` / `FIRESTORE_NATIVE` / 東京、およびFirebaseプロジェクト、
Webアプリ、Hosting、Authentication、Security Rules、データは管理・再作成しない。
FirestoreへのIAM付与は既存ポリシーを上書きしないmember方式。
DB条件で `(default)` のみに限定するが、IAMでは `posts` コレクションだけに限定できない。
API用SAには読み取り・更新・削除・Vertex AI権限を付けない。
現行の投稿追加に合わせた権限なので、機能C/D追加時に別途見直す。
根拠: [Firestore IAM](https://firebase.google.com/docs/firestore/security/iam)、
[DB単位のIAM条件](https://firebase.google.com/docs/firestore/manage-databases#configure_per-database_access_permissions)。

## ローカル検証（GCP変更なし）

リポジトリルートで実行する。Terraform 1.16.2以上、Docker Engineが必要。

```powershell
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform init -backend=false -input=false
terraform -chdir=infra/terraform validate
docker build --platform linux/amd64 -t hack26-fastapi:local backend/fastapi
docker run --rm -p 8080:8080 hack26-fastapi:local
```

別ターミナルで `http://localhost:8080/openapi.json` を確認できる。
コンテナには認証情報を含めないため、この状態でFirestoreへの書き込み成功は保証しない。
アプリのDockerビルドコンテキストは必ず `backend/fastapi` とする。

## stateと認証

初期状態はローカルbackend。`init -backend=false` は検証専用で、GCP認証不要。
apply時はローカルにstateが生成されるため、同じ作業ディレクトリのstateを継続使用し、
同時applyをしない。別PCで空のstateから同じリソースを作らない。
チーム運用開始前に、承認済みのアクセス制限されたGCS backendへstateを移行する。
既存backendの有無・バケット名は未確定なので、この構成ではバケットを作成しない。

`.terraform/`、state・backup、`*.tfvars`、plan、認証鍵は `.gitignore` で除外。
`.terraform.lock.hcl` と `terraform.tfvars.example` は管理対象。秘密値をtfvarsへ書かない。
TerraformとDockerにAPIキーやサービスアカウント鍵を渡さない。

デプロイ実行者はADCと、API有効化、Artifact Registry管理、サービスアカウント作成、
カスタムロール作成、IAMポリシー変更、Cloud Run管理、実行SAのactAs権限が必要。
Docker pushには対象リポジトリへの書き込み権限が必要。
実行SAにこれらの管理権限は付けない。

## 初回デプロイ（事前承認後のみ）

空のArtifact Registryにはまだイメージが存在しないため、二段階でapplyする。
`-target` や仮のサンプルイメージは使わない。

### 1. 認証・設定

```powershell
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project hack26-project
Copy-Item infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
terraform -chdir=infra/terraform init
```

`terraform.tfvars` は初回 `deploy_api = false` / `api_image = ""` のまま。
API有効化・SA・カスタムロール・IAM・リポジトリのみが作成対象になる。
既存APIの管理を取り込む場合は、必要に応じて既存設定を確認しimportする。

### 2. 基盤作成

```powershell
terraform -chdir=infra/terraform plan -out=bootstrap.tfplan
terraform -chdir=infra/terraform apply bootstrap.tfplan
```

planを確認し、Firestore DBやFirebaseの作成・置換・削除がないことを確認する。
API有効化直後は反映待ちで失敗する場合がある。その場合もstateを保持して再planする。

### 3. イメージ作成・登録

```powershell
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
$imageTag = 'asia-northeast1-docker.pkg.dev/hack26-project/hack26-backend/fastapi:mvp-001'
docker build --platform linux/amd64 -t $imageTag backend/fastapi
docker push $imageTag
gcloud artifacts docker images describe $imageTag --project=hack26-project --format='value(image_summary.digest)'
```

pushされた `sha256:...` を取得し、`terraform.tfvars` を次の形に更新する。
以下の山括弧の部分は実際の64桁のdigestに置換する。

```hcl
project_id = "hack26-project"
region     = "asia-northeast1"
deploy_api = true
api_image  = "asia-northeast1-docker.pkg.dev/hack26-project/hack26-backend/fastapi@sha256:<実際のdigest>"
```

### 4. API作成

```powershell
terraform -chdir=infra/terraform plan -out=api.tfplan
terraform -chdir=infra/terraform apply api.tfplan
terraform -chdir=infra/terraform output api_url
```

通常の更新は新イメージpush → digest更新 → plan確認 → 承認済みapply。
稼働後に `deploy_api=false` へ戻すとService削除の計画になるため戻さない。
Serviceのdeletion protectionとリポジトリのprevent_destroyを解除する変更は別途レビューする。

## デプロイ後の確認とフロント接続

Serviceは公開invokerを付与せず、認証必須のまま作成する。
確認担当に対象Serviceの `roles/run.invoker` がある状態で、次のプロキシを利用できる。

```powershell
gcloud run services proxy hack26-api --project=hack26-project --region=asia-northeast1 --port=8080
```

`http://localhost:8080/docs` でAPI定義を確認する。投稿APIの実疎通確認はFirestoreに
データを書き込むため、承認後に行う。IAM反映には時間がかかる場合がある。
今回のfmt/init/validateは、GCPの権限・クォータ・実際の書き込み成功を検証しない。

ブラウザ向け公開方式は未実装。Firebase Hosting rewrite、またはAPI公開とCORS設定を
フロント担当と調整する。Firebase IDトークンはCloud RunのIAM認証とは別であり、
管理者APIにはFastAPI内でのトークン・管理者権限検証が必要。
Hosting・Authentication・フロント設定はこのTerraformの対象外。

## 機能B：Job / Schedulerの設計（未実装）

分岐元の `origin/main` には機能Bの候補生成関数が既に含まれている。
元の機能Bブランチ独自のコミットは取り込まず、既存の機能A〜Dのコードも変更しない。
Firestore取得・永続化・処理状態遷移・排他・CLIが未完成なので、JobもSchedulerも
Terraformリソースとして定義しない。起動可能なバッチはまだ存在しない。

完成後は同じイメージのcommandをCLIに切り替え、次の構成を別変更で追加する。

```text
Scheduler（初期paused=true）
  → OAuthでCloud Run Jobs API :run
    → Cloud Run Job（専用SA）
      → 既存Firestore / Vertex AI
```

- Job: 東京、task_count=1、parallelism=1、初期max_retries=0。
  CLIは成功0・失敗非0で終了し、件数制限・実行時間の測定後にtimeoutを決める。
- Job実行SA: API用と分離。Firestore処理に必要な権限と `roles/aiplatform.user`。
  `GOOGLE_CLOUD_PROJECT=hack26-project`、`GOOGLE_CLOUD_LOCATION=global`、
  `GEMINI_MODEL` は動作確認済みモデルを設定。APIキー・鍵ファイルは使わない。
- Scheduler: 水曜13時、cron `0 13 * * 3`、time_zone `Asia/Tokyo`。
  専用呼び出しSAに対象Job限定で `roles/run.invoker` を付与。
  POST先は `https://run.googleapis.com/v2/projects/hack26-project/locations/asia-northeast1/jobs/JOB_NAME:run`。
  OAuth scopeは `https://www.googleapis.com/auth/cloud-platform`。OIDCではない。
- 必要APIとして `cloudscheduler.googleapis.com` と `aiplatform.googleapis.com` を管理に追加。
  既存有効化状態を確認し、destroy時に無効化しない。
- 排他: Firestoreの `locks/candidate_batch` をtransactionで取得し、期限と所有run_idで
  更新・解放する。単一task設定だけでは別実行の重複を防げない。
- 投稿claim・候補保存・processedへの遷移、期限切れprocessingの復旧、決定的IDに
  よる再実行の冪等性を実装する。Gemini呼び出しはFirestore transactionの外で行う。
- Schedulerの起動成功はJobの完了成功ではないため、Jobの失敗監視も確認する。

有効化条件はCLI実装、実DBへの保存、並行実行排他、障害復旧、再実行での重複防止、
機能Dとの `last_reviewed_at` 更新責務の確認。その後もまず手動実行で検証し、
Schedulerの停止解除を別途承認する。

根拠: [Cloud Run Jobのスケジュール実行](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule)。
