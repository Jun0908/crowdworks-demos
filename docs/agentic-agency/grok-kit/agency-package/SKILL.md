---
name: agency-package
description: Agency DeliveryがQAを通った成果物を納品ZIPと台帳にまとめ、Grok会話へ完成物を返す。
---

同じrepoとAGENCY_ROOTで `inspect <assignmentId>` を実行し、deliveryの割当であることと、上流QAの結果を確認する。

`package <assignmentId>` は最新版の合格成果物をコピーし、SHA256・版番号付きmanifest.json、delivery.md、delivery.zipを作る。返されたartifact.idが納品ZIPのID。ZIPを実際に開き、同梱ファイルを依頼のdeliverablesと照合する。不足があれば成功とせずblockedを返す。

result.jsonはStepResultに合わせ、割当のrequiredCheckIdsをPASSと確認根拠付きで記録する。artifactIdsにZIPのIDを含め、`finish <assignmentId> --result <result.json>` が成功したら司令塔へパスを返す。ユーザーが開ける添付をGrokの会話に返す。クラウド内のパスだけを外部公開URLとして扱わない。

外部顧客への送信やWeb公開はこのSkillの実行に含めない。ユーザーの完成物確認は司令塔が扱う。
