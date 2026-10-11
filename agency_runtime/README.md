# Grok Bot共有案件ランタイム

Grokの司令塔が専門Botへ仕事を振るための実装。SQLiteに案件・割当・結果を保存し、共有コンピュータへJSON、成果物、作業ボードを出力する。GrokのBot間メッセージ、検索、文章・コード生成と組み合わせる。外部のLLM呼び出しサーバーは起動しない。

## Grok共有コンピュータへ導入

Grokからリポジトリを取得し、repo内で実行する。Python 3.11以上。APIキーなしで初期化可能。

```bash
python -m pip install -r agency_runtime/requirements.txt
export AGENCY_ROOT=/workspace/agentic-agency/runtime-v1
python -m agency_runtime bootstrap --kit-out /workspace/agentic-agency/cli-skills
python -m agency_runtime show
```

既存の手書きconfig/jobsがある場所は上書きしない。runtime-v1は独立した台帳。Botが既に完了した案件の状態を自動移行したとは扱わない。

`docs/agentic-agency/grok-kit/` の4つのSKILL.mdをGrokのSkillとして保存し、司令塔・営業/調査/制作・QA・Deliveryへ割り当てる。コピーしただけではGrokへのSkill登録にならない。Botを実際に作成する操作とRoutineの実行はGrok側が担当する。

## 単発案件

```bash
python -m agency_runtime create --brief docs/agentic-agency/example-job.json --mode live --request-key first-restaurant-proposal
python -m agency_runtime plan JOB_ID --file plan.json
python -m agency_runtime next JOB_ID
```

返されたassignmentFileを担当Botへ送る。対応能力は、Grok側で実際に検証後に `capability market_research --readiness ready --evidence '検証した内容とファイル'` とする。未検証・API未接続なら割当はwaiting_connectionで止まる。

担当Botは成果物と出典を `artifact` / `source` へ登録し、`finish` で結果を確定する。詳細コマンドは `python -m agency_runtime --help` と各コマンドの `--help`。`inspect` はファイルの実在・hashを検査し、内容のQAはBotが行う。

QAのチェックIDは工程条件のcriterion_1...、依頼条件のjob_criterion_1...。各最新版成果物のartifactIdに検査根拠を結びつける。納品は `package` でZIPを作成し、全工程完了後はready_for_review。ユーザーの確認後に `accept JOB_ID`。取消後の結果や古い版の再提出は拒否する。

## APIキーなしの3処理

`run ASSIGNMENT_ID --payload payload.json` で、契約更新抽出・営業リスト整理・請求書抽出を呼べる。実データ処理をして成果物を登録するが、結果のfinish／QAは自動で合格にしない。

| capability | 入力JSON | 主な出力 |
|---|---|---|
| contract_extract | csv_text, month, lookahead, convention | renewals.xlsx / csv / zip |
| leads_clean | data（Places形式）, sample, areas, use_reviews | leads.xlsx / csv, excluded.csv |
| invoice_extract | documents=[{name,lines}], today, self_name | invoices.xlsx / csv / json |

請求書入力は抽出済みテキスト。PDFテキスト抽出・OCR自体はGrokのツールで行うか、今後接続する。入力のOCRフラグだけでOCRを実行済みとは表示しない。営業リストも外部検索は行わない。Grokの調査ツール・Google Places等で取得したJSONを渡す。

23種類の仕事はカタログにあり、文章・Web制作等はネイティブBotが作成したファイルを登録できる。すべての能力を実装済み・接続済みとみなさない。外部APIのキーは共有JSONやGitへ記録せず、Grokの接続設定に追加する。

## 検証

Windowsのローカル台帳で検証する例：

```powershell
python -m agency_runtime --root .demo-output/agency-check init
python -m pytest agency_runtime/tests web/tests -q
```

23のランタイムテストで、再送、同時割当、循環計画、停止/再開、取消後の結果、修正版のQA、hash改変、入力コピー、出典候補の重複、3処理の実ファイル生成、CLI再起動、処理の再送、既存作業の保護を検査する。Bot間通信の検証は別途Grokの実行証跡を確認する。

台帳は1つの共有ローカルファイルシステム向け。各Botが同じディレクトリを読み書きできることを先に検証する。複数ホスト間のネットワークファイル共有はこの版の対象外。計算/制作の実行途中に異常終了した場合、同じ割当のinspect/showから再開する。
