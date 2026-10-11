---
name: agency-orchestrate
description: Grok Bot内の司令塔が営業機会・依頼を案件化し、専門Botへ割り当て、調査から納品準備まで進める。
---

Grok BotのネイティブBot間メッセージで進行する。推論・Bot作成・メッセージ・RoutineはGrokが担当し、案件台帳にはリポジトリの `python -m agency_runtime` を使う。独自のLLMサーバーは不要。

## 実行環境

Grokの共有コンピュータ上のrepoを作業ディレクトリとし、各Botで同じ `AGENCY_ROOT` を設定する。既存の案件を保護するため初回のCLI台帳は `/workspace/agentic-agency/runtime-v1`。入力JSONはrepoの `docs/agentic-agency/contracts.schema.json` に従う。CLIのstdoutは `{ok,data}`、失敗はstderrと終了コード1。JSONのIDとパスを後続コマンドへ渡す。

## 司令塔の手順

1. `show` と `board.md` を確認する。進行中案件があればその案件を優先する。案件候補は、公開情報を実際に読んでから `opportunity --key <stable-source-key> --title ... --url ... --evidence-file ...` で重複を抑えて記録する。サンプルと実案件を分ける。
2. 依頼をbrief.jsonにまとめ、`create --brief <file> --mode live --request-key <stable-key>`。同じ依頼の再送は同じキーを使う。入力ファイルがあれば `input-import <jobId> --file ...` でコピーを保存してから計画する。
3. `plan <jobId> --file <plan.json>`。工程は役割、対応能力、依存関係、合格条件を含む。制作・調査・営業工程は必ずQAにつなぎ、納品準備はQAに依存させる。不明点を推測してblocking questionを消さない。
4. `next <jobId>` の返したASSIGNを `ownerBot` へGrokのメッセージ機能で渡す。全文を捏造せず、assignmentId、assignmentFile、returnToをそのまま送る。`waiting_connection` は未接続機能の報告に切り替える。
5. 担当Botの結果は `finish` で保存されて初めて確定する。メッセージだけの「完了」は採用しない。再送は同じassignmentId。別の割当を増やさない。
6. `blocked` が修正で解決できれば `revise <jobId> --step <stepId> --reason ...`。下流のQA・納品も無効化される。修正2回まで。入力不足・API不足はその理由を報告する。
7. 次工程を同じ方法で進める。`ready_for_review` で成果物をユーザーへ添付・リンクして返す。`accept` はユーザーが完成内容を受け入れた後にだけ使う。納品準備は外部送信の証拠ではない。

## 運用

既存のフウ＝coordinator、リサーチ担当＝sales/research、コード担当＝creator、Agency QA＝qa、Agency Delivery＝delivery。実在するBot名が違えば `bot <role> --name ...` を更新する。このコマンド自体はBotを作成しない。

`capability <id> --readiness ready --evidence ...` は対象Botで入出力を実際に検証した後に設定する。検証できないものはunverified／needs_connection。検索はGrokの利用可能ツールを使い、出典を記録する。23種類の仕事はcapabilities.jsonを参照し、担当ツールが足りない工程を飛ばさない。

外部APIは後付け。営業送信・公開・購入は今回の稼働範囲外。停止指示は `pause`、再開は `resume`、取消は `cancel`。Routineは単発完走後、ユーザー指定の時刻・対象で登録する。静かな状態では通知せず、完成・失敗・判断必要時だけ報告する。
