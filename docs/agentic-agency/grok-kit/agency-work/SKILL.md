---
name: agency-work
description: Grokの営業・調査・制作Botが割当ファイルを読み、実際の出典と成果物を台帳へ登録して司令塔へ戻す。
---

司令塔から受け取ったassignmentIdとassignmentFileを使う。repoを作業ディレクトリ、AGENCY_ROOTを司令塔と同じ値にする。

1. `python -m agency_runtime inspect <assignmentId>`。割当のstep.instructions、briefFile、inputArtifacts、acceptanceCriteriaを読む。入力ファイルのhash違い、取消・古い割当は処理を止めて報告する。
2. 調査は利用可能なGrokの検索・ブラウザで実際にページを読む。`source <assignmentId> --url ... --title ... --excerpt-file <読んだ箇所.txt>` で出典を保存。登録済みURLでも内容の正確さはQAが確認する。本文中のリンクとsourceIdsを対応させる。
3. 文章・コード・資料などはoutputDir内に実ファイルを作成。未接続ツールで画像や動画を生成したと主張しない。`artifact <assignmentId> --file <file>` の返したidを記録する。登録ファイルは不変なので変更は新しいattemptで行う。
4. 既存のデータ処理は `run <assignmentId> --payload <payload.json>`。対象はcontract_extract／leads_clean／invoice_extract。契約はcsv_text＋month、営業候補はdata（Places形式JSON）＋sample、請求書はdocuments（name＋lines）＋today。請求書のPDF抽出／OCRはGrokで実際に行うか接続待ちにし、抽出したテキストの出所を保存する。CLI自体はOCRも検索も実行しない。
5. 実際に各合格条件を確認しresult.jsonを作成する。kind=step_result、stepId、outcome、summary、artifactIds、sourceIds、checks、blockersを含む。チェックIDは `criterion_1` から順に割当のrequiredCheckIdsに合わせ、evidenceに確認内容と数値を書く。未確認はNOT_CHECKED、失敗はFAIL。未完了をsucceededにしない。
6. `finish <assignmentId> --result <result.json>` が成功したらreturnToへassignmentId、工程結果、成果物とresult.jsonのパスをGrok Bot内メッセージで返す。コマンドが拒否した結果を完了報告しない。
