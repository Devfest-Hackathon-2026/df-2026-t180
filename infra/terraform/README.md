# GCPインフラ（MVP）

既存 `hack26-project` を利用し、東京 `asia-northeast1` にAPIを配置する。
このREADMEのapply・pushは**将来、GCP変更の事前承認を得た後に実行する手順**。
開発ルールに従い、API有効化を含む変更内容をDiscordで事前相談する。

2026-11-10時点で基盤・IAM・Security Rulesを適用済み、Cloud Runへ機能A・C・Dを
デプロイ済み。最新revisionは `hack26-api-00002-fxf`、`allow_public_api=false`。
OpenAPIの7エンドポイント、Firestoreのregions読み取り（HTTP 200）、Firebase未認証の
管理者API（401）、適用後planのNo changesを確認した。Firestore実書き込み成功は
今回の検証では確認していない。既存データを変更するテストは実施しない。
以下の初回手順・過去時点の調査結果は運用履歴として残す。

## 管理範囲

| 対象 | 定義 |
| --- | --- |
| 必要API | Artifact Registry / Cloud Run / IAM / Firestore / Firebase Rules。destroy時も無効化しない |
| Artifact Registry | 東京、Docker形式、`hack26-backend`、削除防止 |
| API実行SA | `hack26-api`、鍵ファイルなし、ADC |
| Firestore IAM | `hack26PostWriter`：entities.create/get/list/update、databases.get |
| Security Rules | `firestore.rules` → Ruleset → `cloud.firestore` Release |
| Cloud Run Service | `hack26-api`、0〜2インスタンス、1 CPU / 512 MiB、認証必須 |
| Cloud Run Job / Scheduler | **未定義・未作成**。後述の設計のみ |

既存Firestore `(default)` / `FIRESTORE_NATIVE` / 東京、およびFirebaseプロジェクト、
Webアプリ、Hosting、Authentication、データは管理・再作成しない。
Security Rulesのみ別リソースとして管理する。Firestore DB作成リソースは定義しない。
FirestoreへのIAM付与は既存ポリシーを上書きしないmember方式。
DB条件で `(default)` のみに限定するが、IAMでは `posts` コレクションだけに限定できない。
API用SAには機能Aの投稿作成と、機能Cのregions・rules取得用の読み取り権限を付ける。
機能D向けの更新・トランザクション権限も維持する。削除・Vertex AI権限は付けない。
IAM条件はDB単位なので、作成・読み取りの対象をコレクション単位には制限しない。
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

既にServiceと基盤を適用済みの場合、初回手順を繰り返さず末尾の再デプロイ手順を使う。

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
`allow_public_api` は既定falseで、設定例もfalseを維持する。
将来 `deploy_api=true` の状態で `allow_public_api=true` にすると、planに
`google_cloud_run_v2_service_iam_member.api_public_invoker` の追加
（`allUsers` / `roles/run.invoker`）が明示される。falseへ戻すとこの付与を削除する。
この変数はServiceへのHTTP呼び出しだけを許可し、Firestoreへの権限は一般ユーザーに付けない。
外部で追加された公開IAMはこの変数では除去しないため、適用前に既存設定も確認する。
機能Dの認証・管理者認可の検証完了まではtrueへ変更しない。
確認担当に対象Serviceの `roles/run.invoker` がある状態で、次のプロキシを利用できる。

```powershell
gcloud run services proxy hack26-api --project=hack26-project --region=asia-northeast1 --port=8080
```

`http://localhost:8080/docs` でAPI定義を確認する。投稿APIの実疎通確認はFirestoreに
データを書き込むため、承認後に行う。IAM反映には時間がかかる場合がある。
今回のfmt/init/validateは、GCPの権限・クォータ・実際の書き込み成功を検証しない。

Docker Engine起動後、ローカルコンテナのOpenAPIを別ターミナルで確認する。
これはFirestoreへアクセスしない。

```powershell
$spec = Invoke-RestMethod http://localhost:8080/openapi.json
if (-not $spec.paths.'/api/posts'.post) { throw 'POST /api/posts missing' }
if (-not $spec.paths.'/api/regions'.get) { throw 'GET /api/regions missing' }
if (-not $spec.paths.'/api/regions/{region_id}/rules'.get) { throw 'GET region rules missing' }
```

一般向けフロントの投稿・閲覧は最新mainでもモック／サンプルが残っているため、
画面からの実利用にはフロント担当によるAPI接続が別途必要。

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
Cloud Runには `GOOGLE_CLOUD_PROJECT` と `FIREBASE_PROJECT_ID` を明示する。
既定ではどちらも `hack26-project`。APIキー・認証鍵は不要。

## Security Rulesの管理と次回適用

2026-11-09時点の読み取り確認：

- 既存stateはAPI4件・Artifact Registry・API実行SAの計6件。
- Rules APIの `projects/hack26-project/releases/cloud.firestore` は404。
- Release一覧、Ruleset一覧はいずれも空（継続ページなし）。現在のRulesソースは存在せず取得対象なし。
- Hostingの既存サイトは `hack26-project`。公開Release一覧は空。
- 新規planは5 add / 0 change / 0 destroy：カスタムロール、IAM member、Rules API管理、Ruleset、Release。

`firestore_rules.tf` は独立した `firestore.rules` を `file()` で読み、全クライアントの
Firestore読み書きを拒否する。Firebaseログイン済み管理者も直接アクセス不可。
FastAPIのサーバーSDKはIAMで動作し、このルールによって禁止されない。
独立したルール構文のサーバー側コンパイル・実拒否動作は今回未検証。

既存Google provider 7.46.2のローカルスキーマでRuleset・Releaseを確認しvalidate済み。
Rulesetは不変のため更新時は新規作成し、Releaseの参照先を切り替える。
`create_before_destroy` と `deletion_policy=ABANDON` により旧RulesetをAPIから削除しない。
Releaseは `prevent_destroy` と `deletion_policy=PREVENT` で削除を防ぐ。
古いRulesetの整理は別途承認が必要。

**既存 `bootstrap.tfplan` は変更前の計画なので今後使わない。**
今回の `rules-review.tfplan` もレビュー用。適用直前に状態を再確認し、新しくplanを作る。
Rulesの適用は実アクセス制御の変更となるため、内容とplanの承認が必要。

安全な次回作業：

1. 現在のstateを安全な場所へバックアップ。同じstateを使い続け、削除・作り直しをしない。
2. Rules APIをGETし、ReleaseとRulesetの有無を再確認。403や取得失敗なら停止し、推測で上書きしない。
3. Releaseが新たに存在していれば、その `rulesetName` のソースを取得・保全・レビューする。
   下記importで既存Releaseを管理に取り込む。今回はimportしていない。
4. 新規deny-all Rulesetへの切り替え差分と、既存6件に置換・削除がないことをplanで確認する。
5. Rules公開を含む承認後に限り、その新規planを適用。権限不足なら停止し無断で権限を変更しない。
6. クライアント拒否と、FastAPI経由のIAMアクセスを確認する。DB実書き込みの検証も事前合意する。

```powershell
# 既存Releaseを確認できた場合だけ実行（stateを書き換えるため今回は未実施）
terraform -chdir=infra/terraform import google_firebaserules_release.firestore projects/hack26-project/releases/cloud.firestore
# 既存Ruleset自体を管理する場合のみ。IDは取得した実際の値を指定する。
# terraform -chdir=infra/terraform import google_firebaserules_ruleset.firestore projects/hack26-project/rulesets/RULESET_ID
terraform -chdir=infra/terraform plan '-out=rules-reviewed.tfplan'
```

旧Rulesetをimportする場合、ソースとの差分による置換を必ずレビューする。
Releaseだけimportして旧Rulesetを管理対象外で保存する方法も可能。

操作主体の権限（Cloud Run実行SAには付与しない）：

- 読み取り：`firebaserules.releases.get/list`、`firebaserules.rulesets.get/list`。
- 公開：`firebaserules.rulesets.create`、`firebaserules.releases.create/update` と上記読み取り。
- API有効化：`serviceusage.services.enable/get/list` 等。カスタムロール作成とプロジェクトIAM変更の権限も別途必要。
- `roles/firebaserules.admin` は既定ロール候補だが広い。必要なら管理者がカスタムロールを検討する。
  今回はどの操作権限も追加していない。plan成功はcreate/update権限の保有証明ではない。

## Hosting rewrite案（未実装）

Google providerには `google_firebase_hosting_version` のrewrites/runと
`google_firebase_hosting_release` があり、既存site IDを参照して構成可能。
ただしHostingはバージョン全体を公開する仕組みで、rewriteだけの独立更新ではない。
静的ファイル・SPA rewrite・ヘッダー設定の欠落を防ぐため、フロント担当と公開の管理主体を統一する。
今回はsite/Webアプリ/version/releaseを作成・変更せず、Firebase CLIによる既存サイトへの
フロント配信と `firebase.json` の管理をMVP案とする。

```json
{
  "source": "/api/**",
  "run": { "serviceId": "hack26-api", "region": "asia-northeast1" }
}
```

このrewriteをSPAの `**` より先に置く。同一オリジンの `/api/...` を利用してCORSに依存しない。
Firebase IDトークンを `Authorization: Bearer ...` で送り、Cloud Run到達時のヘッダーと
401/403/正常管理者アクセスを実環境で確認する。トークン自体をログ出力しない。
Firebase Hosting rewriteだけではCloud Run IAM認証をFirebase認証で満たせない。
一般公開はDのトークン・管理者検証完了後の別承認とし、今は `allow_public_api=false` を維持する。

## 機能D取り込み後の再デプロイ（承認後のみ）

2026-11-10、PR #31のmerge（a4474e2）を含むorigin/main（a16945a）を取り込み済み。
管理者APIはGET/PATCHの `/api/admin/candidates`・`/api/admin/rules` 系4本。
Firebase Admin SDK 7.7.0で署名・issuer・audience・期限等を検証し、アプリで
auth_timeの有限数値・未来日時を確認、毎回admins/{uid}の存在で管理者認可する。
check_revokedは無効。アカウント無効化だけで即拒否する運用ではなく、管理者解除は
adminsからのUID削除で行う。実ユーザーによる401/403/成功確認は公開前に必要。

現行の5権限で読み取り・作成・差分更新・トランザクションに対応する。
Firebaseのトークン検証のために実行SAへRules管理権限やFirebase管理権限を追加しない。
FIREBASE_PROJECT_ID / GOOGLE_CLOUD_PROJECTはともにhack26-projectを維持する。

以下は次回以降の再デプロイ手順。2026-11-10に同じ流れで再デプロイ済み。

```powershell
# リポジトリルート。検証済みコードから新しい一意タグを作る。
$revision = git rev-parse --short HEAD
$imageTag = "asia-northeast1-docker.pkg.dev/hack26-project/hack26-backend/fastapi:admin-$revision"
docker tag hack26-fastapi:local $imageTag
# 事前承認後のみ実行
docker push $imageTag
gcloud artifacts docker images describe $imageTag --project=hack26-project --format='value(image_summary.digest)'
```

取得したdigestでローカルterraform.tfvarsのapi_imageだけを更新する。
deploy_api=true / allow_public_api=falseを維持し、stateを保全する。
旧bootstrap.tfplan・rules-review.tfplanを使わず、新規計画を作る。

```powershell
terraform -chdir=infra/terraform fmt -check -recursive
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan '-out=admin-redeploy.tfplan'
```

想定はServiceのimage更新。公開IAM追加やDB再作成・Rules変更など別の差分が出た場合は停止して確認する。
計画を承認してからのみ、その計画をapplyする。Terraform外のgcloud run deployで上書きしない。
適用後は新revision・digest・環境変数を確認し、OpenAPIと管理者認可を検証する。
private ServiceのCloud Run IAM用トークンとアプリ用Firebase IDトークンは別物なので、
Firebaseトークンだけで呼び出せると解釈しない。実ユーザー検証の経路を準備してから実施する。
採否APIはexpected_versionによる競合検出もあるため、対応した最新フロントと組み合わせる。
