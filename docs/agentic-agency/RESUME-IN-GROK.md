# 使用量上限が解消した後の再開指示

Grok Botの「フウ」に以下を送る。これは再開用の指示であり、再開済みの証跡ではない。2026-10-11、調査と提案書の作成が報告された後、Grokの使用量上限で停止した。APIキーの入力やローカルテストを、Grokの利用枠の回復とは扱わない。

---

Agentic Agencyの実装を保存済みの状態から再開してください。GitHub `Jun0908/crowdworks-demos` のmainを取得し、まず `docs/agentic-agency/runtime-status.md` と `agency_runtime/README.md` を読んでください。既存のフウ・リサーチ担当・コード担当・Agency QA・Agency Deliveryを再利用し、重複作成しないでください。

1. `/workspace/agentic-agency/` にある既存案件のstate・plan・assignments・resultと実ファイルを照合してください。research.mdとproposal.mdの作成までは報告済みです。Agency QAの保存済み結果があれば検証し、未完了なら同じassignmentIdで進捗を確認してください。調査や提案書を最初から二重制作しないでください。
2. QAの出典確認・検査が終わったらAgency Deliveryへ納品準備を引き継ぎ、実際の調査メモ・提案書・QAと納品一式を会話へ添付してください。検査できていない内容を合格にしないでください。
3. クラウドのrepoで依存関係を導入し、`AGENCY_ROOT=/workspace/agentic-agency/runtime-v1` を全Botに共通設定してください。既存config/jobsを上書きせず、`python -m agency_runtime bootstrap --kit-out /workspace/agentic-agency/cli-skills` を実行してください。pytestがなければ検証用に導入し、`python -m pytest agency_runtime/tests web/tests -q` の実際の結果を保存してください。ローカルでは52テスト成功しています。
4. grok-kitのorchestrate・work・review・packageをGrokのSkillとして実際に保存し、担当Botへ割り当ててください。フォルダーへコピーしただけで登録済みとしないでください。
5. 元の案件の納品準備後、新しいCLI台帳に契約更新のsample案件を1件作り、Creator→QA→DeliveryをBot間メッセージで進めてください。対応能力は実検証後にreadyへ更新し、runの再送が同じ成果物を返すことと納品ZIPまで確認してください。
6. 実際のBot名、Skill参照、jobId、実行ログ、成果物、残る未接続機能を報告してください。個人情報・鍵・実顧客情報を含まない証跡が保存可能なら、この会話へ添付してください。

Grokの共有コンピュータで作業し、WindowsのローカルPCをターミナル操作しないでください。チーム内部の依頼と返答は許可済みです。外部営業送信・購入・公開とRoutine有効化は今回の再開に含めません。止まった箇所だけを具体的に報告し、それ以外の実装・検証は進めてください。
