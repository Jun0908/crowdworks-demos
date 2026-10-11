# 請求書 支払期日リスト化 デモ（社内検証用）

請求書PDF（テキストPDF／スキャン画像PDF）を一括で読み取り、
**請求日・支払金額(税込)・取引先・振込先・支払期日・勘定科目(推定)** を支払期日順の Excel にまとめるデモです。
サンプル請求書の会社名・口座はすべて架空です。

## 構成
| パス | 内容 |
|---|---|
| `extract_invoices.py` | 本体。フォルダ内のPDFを一括処理して xlsx を出力 |
| `evaluate.py` | 抽出結果(JSON)と正解データを突き合わせ、ファイル×項目の正誤表を出力 |
| `tools/generate_samples.py` | サンプル請求書5件＋`ground_truth.json` を生成（うち2件はスキャン風画像PDF） |
| `tools/generate_holdout.py` | 抽出ロジック確定後に作った「未見レイアウト」2件＋`ground_truth_holdout.json` |
| `samples/`, `samples_holdout/` | サンプルPDF |
| `output/` | 出力 Excel・抽出JSON・精度レポート |

## セットアップ（Debian/Ubuntu）
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-jpn fonts-ipafont-gothic fonts-ipafont-mincho
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## 実行
```bash
# サンプル生成（任意）
.venv/bin/python tools/generate_samples.py

# 抽出 → Excel
.venv/bin/python extract_invoices.py samples -o output/invoices.xlsx --today 2026-10-11 --json output/extracted.json

# 精度評価
.venv/bin/python evaluate.py output/extracted.json ground_truth.json -o output/accuracy_report.md
```
主なオプション
- `--today` 期日判定の基準日（省略時は Asia/Tokyo の今日）
- `--self-name` 自社名。宛名（御中・様の側）を取引先と誤認しないための除外に使用
- `--ocr-psm` tesseract のレイアウト解析モード（既定 6。3 にすると多段組に強い反面、単純な帳票で悪化することを確認済み）

## 処理の流れ
1. PDFにテキスト層が30文字以上あれば PyMuPDF で単語座標から行を復元、なければ 300dpi で画像化 → 簡易傾き補正 → tesseract(jpn) で OCR
2. NFKC 正規化（全角数字・￥・括弧など）と日本語文字間の空白除去
3. 正規表現＋近傍ルールで項目抽出
   - 日付: `2026年10月15日` / `2026/10/20` / `2026-09-25` / `2026.10.08` / `令和8年…` / `R8.11.30`
   - 支払期日: 「支払期日/支払期限/お支払期日/振込期限/入金期限…」ラベル、なければ「◯日まで」表現
   - 金額: 「差引ご請求額 > ご請求金額 > お支払総額 > 税込合計/合計金額 > 合計」の優先順。小計+消費税−源泉 と一致するか検算
   - 取引先: 法人格・屋号を含む文字列のうち、御中/様の行と自社名を除外し、登録番号(T+13桁)の近くを優先
   - 振込先: 「銀行/信用金庫…」を起点に6行の範囲から 銀行・支店・種別・7桁口座番号・カナ名義
   - 勘定科目: 明細のキーワード辞書で点数化（通信費/消耗品費/外注費/広告宣伝費/旅費交通費/地代家賃/支払手数料/水道光熱費）。該当なし・同点は「要確認」
4. Excel 出力: 支払期日の昇順、**期限超過=赤 / 7日以内=黄**、要確認フラグと理由、抽出方法、ソースファイル、検証用に抽出テキストのシート

## 制約（重要）
- ルールベースのため **ラベル辞書にない表記・英語併記・法人格のない屋号・ゆうちょの漢数字店名** などは取れません（ホールドアウト評価で確認済み、`output/accuracy_report_holdout.md`）。
- OCR（tesseract）は数字1桁の欠落や漢字の誤認識（架→梨 など）が起き、**誤った値を「取れた」ように出す**ことがあります。OCR行は常に「要確認」扱いです。
- 結果は必ず人が原本と照合してから支払処理に使ってください。
