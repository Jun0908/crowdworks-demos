---
name: agency-review
description: Agency QAが最新版の成果物・出典を読み、依頼と工程の合格条件を検査して合格または修正を返す。
---

repoのCLIを共通AGENCY_ROOTで使う。`inspect <assignmentId>` で割当とhash検査を取得する。hashが一致しただけでは品質合格にしない。

割当のinputArtifactsをすべて開き、仕様、計算、リンク、実績表現、出力形式を該当する仕事に合わせて確認する。調査では出典ページを再確認し、推測と事実を分ける。表計算は実際に開いて行数・項目・計算を検査する。アプリは実行と操作を確かめる。必要なツールがない場合はblockedとする。

result.jsonはcontracts.schema.jsonのStepResult。工程条件は `criterion_1...`、依頼条件は `job_criterion_1...`。各検査のevidenceに、何を開き、何と照合し、何が一致したかを書く。さらに検査した各成果物に `artifactId` を付けたPASS/FAIL/NOT_CHECKEDチェックを最低1つ記録する。artifactIdsには検査対象のIDを入れる。全条件と全成果物が合格した場合だけsucceeded。修正箇所があればrevise、検査不能ならblocked。

レビュー本文をreview.mdに保存し `artifact` で登録する。`finish <assignmentId> --result <file>` を実行し、司令塔へ結果を返す。QAが制作工程を書き換えて合格を装わない。修正は司令塔が新しいattemptを割り当てる。
