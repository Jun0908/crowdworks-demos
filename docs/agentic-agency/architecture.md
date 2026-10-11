# Grok Botオーケストレーション仕様

## 1. 実行環境と会話

Grok Botの既存機能を実行基盤として使う。Directorが所有者、専門Botは担当工程の所有者。全体進捗や承認の窓口はDirectorの個別会話。グループ「Agentic Agency」は進捗・引き継ぎの共有に使う。

公式資料ではBot間の非同期メッセージと共有ファイルが使える。グループでのBotからの引き継ぎは現在テキストのみで、承認・秘密情報入力はグループに出ない。画像確認が必要ならQAへ直接画像を渡すか、共有ファイルを開いてもらう。[共同作業](https://docs.x.ai/grok-bot/chat-and-collaboration)

各Botは同じクラウドコンピュータと認証情報を共有する。別のBot名は権限分離ではない。今回のローカルWindowsのパスはGrok Botから直接見えるものとせず、必要なソース・入力をGrok側へ渡す。[コンピュータとアプリ](https://docs.x.ai/grok-bot/computer-and-apps)

## 2. ファイルを正本にする

ルート：`/workspace/agentic-agency/`。セットアップ時にこの場所が使えることを確認する。

```text
agentic-agency/
  config/company-policy.json      # 対象業種、提供仕事、上限、停止状態
  config/bot-registry.json         # 作成したBot名・参照・担当
  config/connections.json          # 接続有無のみ。APIキーは入れない
  config/capabilities.json         # 接続・試行を確認した仕事だけreadyにする
  skills/                         # 保存した手順の控えと版
  opportunities/index.json        # URL/ソースIDで重複管理
  jobs/<job-uuid>/
    brief.json                    # contracts.schema.jsonのJobBrief
    plan.json                     # 同Plan
    state.json                    # Directorだけが更新
    assignments/<assignment-id>.json
    inputs/                       # 元ファイル、上書きしない
    steps/<step-id>/attempt-1/     # 担当Botだけが書く
      result.json                 # 同StepResult
      artifacts.json              # id・ファイル・hash・版のmanifest
      sources.json                # id・出典URL・確認日・取得事実
      files/
    reviews/                      # QAの検証結果
    delivery/                     # 納品準備一式
    approvals/                    # 承認対象の版・宛先・判断
    events.jsonl                  # Directorが追記する活動記録
  board.md                        # 保存状態から生成する仕事一覧
  evidence/setup.md               # 実際のBot/Skill/Routineの参照
```

重要な完成物は会話にも添付する。共有フォルダーだけを唯一のバックアップと考えない。通常の更新で保持される設計でも、復旧・リセットでは直近作業の喪失があり得る。[ファイルと成果物](https://docs.x.ai/grok-bot/files-and-results)

`state.json`、候補index、boardはDirectorだけが更新する。専門Botは専用attemptフォルダーに結果を書き、結果パスをDirectorへ返す。同一ファイルを複数Botが同時編集しない。

## 3. 割り当てメッセージ

Directorが次を保存してから担当へ送る。本文だけでなく `assignmentFile` の実ファイルを読み直すことを必須にする。

```json
{
  "type": "ASSIGN",
  "jobId": "00000000-0000-4000-8000-000000000001",
  "assignmentId": "step_research_attempt_1",
  "stepId": "step_research",
  "attempt": 1,
  "ownerBot": "Agency Scout",
  "assignmentFile": "/workspace/agentic-agency/jobs/00000000-0000-4000-8000-000000000001/assignments/step_research_attempt_1.json",
  "briefFile": "/workspace/agentic-agency/jobs/00000000-0000-4000-8000-000000000001/brief.json",
  "outputDir": "/workspace/agentic-agency/jobs/00000000-0000-4000-8000-000000000001/steps/step_research/attempt-1",
  "returnTo": "Agency Director"
}
```

専門Botは受領時にACK、完了時にRESULTをDirectorへ送る。結果にはjobId、assignmentId、resultFile、outcome、要確認事項を含める。存在するファイルとmanifestのIDだけを返す。出典URLを生成しただけでsource登録しない。

重複ASSIGNを受信したら、同じassignmentIdの作業中・結果ファイルを確認して既存結果を返す。未完了なら進捗を返し、別の作業を立ち上げない。Directorも同じ結果を二度取り込まない。Botの言語指示だけでは厳密なexactly-onceを保証できないため、初版は1案件・1アクティブ割当を既定値とし、再開時は実ファイルを照合する。

## 4. 状態と再開

状態：`draft / queued / running / waiting_input / waiting_connection / waiting_approval / paused / ready_for_review / completed / blocked / cancelled`。
工程：`scope / research / plan / create / validate / package / deliver`。

`state.json` にjobId、version、mode、status、stage、activeAssignmentId、completedAssignmentIds、updatedAt、blockersを保存する。modeは `sample` または `live`。sampleは架空入力、liveは実際の対象情報を使うという区別で、Bot自体の実行を擬似アニメーションにしない。

| 出来事 | Directorの処理 |
|---|---|
| 依頼受付 | 必須条件を確認しbriefを保存。不明項目が制作を妨げる時だけ質問 |
| 計画確定 | 登録済みcapability、依存関係、完成条件を検証してqueued |
| 作業開始 | 割当ファイル保存→担当へ送信→running |
| 担当が完了 | 実ファイル・ID・版を確認し結果を取り込み、次工程へ |
| QAがREVISE | 指摘対象だけ新attemptでMakerへ戻す。最大2回 |
| API等が不足 | waiting_connection。必要な接続と止まる工程だけ通知 |
| 外部送信が必要 | 宛先・本文・添付版を固定し、Directorとの個別会話で確認 |
| 納品準備完了 | ready_for_review。利用者が受領したらcompleted |
| 中断・再訪 | state・割当・結果ファイルを照合。完了済みを再制作しない |
| 返答が長時間ない | 同じassignmentIdで状態確認。担当が動作中なら新担当へ再割当しない |
| Stop | 新規割当を止め、担当へ停止を伝える。既に完了した操作は取り消されたと報告しない |

毎工程終了時にstate、events、boardを更新する。チャットの記憶だけを状態管理に使わない。計画の循環参照、未知の能力、出力形式の不一致は制作開始前に止める。

## 5. 機能の有効化

`capabilities.json` は仕事内容の設計カタログ。導入後のconfigには `readiness=unverified/ready/needs_connection/unavailable` とlastCheckedAt、testEvidenceを追記する。利用可能なツールで実物を作って確認した仕事だけreadyにする。

3つの既存処理はMakerがGrokのコンピュータでPython CLIを実行できれば再利用できる。リポジトリへのアクセスと依存環境を確認する。私有リポジトリのため、URLだけでcloneできるとは仮定しない。

| 機能 | ソース | 完成確認 |
|---|---|---|
| contract_extract | `3_契約更新抽出/` | サンプル250名から80対象・37三ヶ月・19漏れ・7要確認、Excel/CSVを開く |
| leads_clean | `2_焼肉店営業リスト/` | モック26→14候補、除外理由、CSV/Excelを開く |
| invoice_extract | `1_請求書読み取り/` | PDF/OCR環境を確認し原本と照合。未知帳票の既知の低精度を踏まえ、自動確定しない |

元READMEの実行手順を参照し、生成物をジョブフォルダーに保存する。公開デモの画面を見るだけでは新しい依頼の制作完了にしない。Windowsの `.venv/Scripts/` パスはGrok側のOSに合わせる。

## 6. 検証と成果物

全ファイルにID、relativePath、version、sha256、mimeType、sourceIdsを持つmanifestを作成する。パスはジョブ配下、元入力は上書き禁止。QAは実ファイルを開き、必須条件ごとにPASS/FAIL/NOT_CHECKEDと根拠を記録する。

調査は主要主張と出典、提案は範囲と前提、データは件数と合計、Webはビルドと操作、資料はレンダリングと見切れを確認。Botの自己申告だけでPASSにしない。画像は直接渡すか共有ファイルを開く。

納品準備と外部送信は別。初版はファイルと説明を利用者へ返すところまで。実際の送信・公開には宛先・本文・ファイル版の固定と個別確認を設け、結果が不明な送信を自動で繰り返さない。

## 7. Routine

Routineの所有者はDirectorだけ。成功した単発手順を保存してから登録する。専門Botごとに同じ定期処理を設定しない。日時・タイムゾーン・対象・上限・停止条件を設定する。

発火時に既存active jobと `routineId + scheduledTime` の実行記録を確認。既に進行中ならその状態を確認し、同じ仕事を新規作成しない。新着なし・変化なしでは通知せず、成果物完成・失敗・判断が必要な場合だけ報告する。

Grok Botの実行利用量は、利用できる計測手段で記録する。料金APIがない場合に正確なドル額を作らない。案件数・工程数・修正数・追加の有料API呼び出し上限を実際に守れる制約として使う。

## 8. 根拠と未実証事項

公式機能：[Bot作成・役割](https://docs.x.ai/grok-bot/bots)、[共同作業](https://docs.x.ai/grok-bot/chat-and-collaboration)、[共有コンピュータ](https://docs.x.ai/grok-bot/computer-and-apps)、[Skill・Routine](https://docs.x.ai/grok-bot/skills-routines-and-automations)。確認日2026-10-11。

このプロジェクトのBot作成、Skill保存、Routine登録、API認証、無人での完走は未実証。起動時に実際の機能とアクセス権を確認し、結果を `evidence/setup.md` に記録する。
