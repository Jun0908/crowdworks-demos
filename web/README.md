# Agentic Agency 紹介サイトと3つの操作デモ

**紹介サイト：[Agentic Agencyを知る](https://koushin-checker-jun0908.vercel.app/)**

**操作デモ：[Koushinを試す](https://koushin-checker-jun0908.vercel.app/demo/)**（ログイン不要）

**操作デモ：[請求書PDFを読み取る](https://koushin-checker-jun0908.vercel.app/invoices/) / [営業候補を整理する](https://koushin-checker-jun0908.vercel.app/leads/)**

サンプル250名またはCSVを読み込み、契約更新対象者の抽出からAM別の確認資料作成までをブラウザ内で行います。

請求書デモはテキストPDF3件を初期選択し、必要に応じてスキャンPDF2件も含めて実際に読み取ります。自分のPDFは最大5件・合計10MB・10ページです。PDF.js 6.4.299でテキスト取得・原本表示、Tesseract.js 7.0.0で日本語OCR、元のPythonルールで項目抽出・Excel生成を行います。基準日の変更、検索・確認状態の絞り込み、詳細・原本表示、Excel・CSV・JSON出力に対応します。OCRは常に要確認です。Python CLI版の精度評価をWeb版の精度としては扱いません。

営業リストデモは、元のモック検索結果26件を実際に重複排除し、対象エリア・閉業・焼肉関連性を確認して14件の候補を出力します。炭火判定は確定7件・可能性2件・不明5件（文言ルールによる分類）です。エリアと概要・口コミの利用を変更し、検索結果JSONのアップロード・編集、一覧検索・判定絞り込み、候補・除外CSVとExcel出力を試せます。Google Placesのライブ検索は行いません。

## 機能

- 対象月、先読み期間（0〜2ヶ月）、終了日規約（3種類）を変更して再計算。
- 対象者・旧方式で漏れる3ヶ月契約者・要確認データ・退職予定者の切り替え。
- 氏名／職員ID検索、担当AMによる絞り込み、ページ送り。
- AM別Excel、対象者CSV、確認依頼文ZIPのダウンロード。
- CSV入力：UTF-8／Shift-JIS、最大2MB・5,000行。
- 入力データはブラウザ内のみで処理。サーバー送信、永続保存、メール送信はありません。

## 構成

トップページ（`dist/index.html`・`intro.css`・`agency.css`・`gallery.css`）では、Agentic Agencyの依頼領域、3つの制作例、Botチームの構成設計、納品フロー、Skill再利用の構想を紹介します。3つの制作例は同じ大きさのカードに実画面・入力・操作・出力・サンプル結果を掲載し、冒頭にも直接リンクを用意しています。Botの稼働実績やGrok連携済みの機能としては扱いません。制作例から `/demo/`・`/invoices/`・`/leads/` に進め、各デモから紹介サイトに戻れます。トップページでは計算エンジンを読み込みません。

追加の2デモは `tools-worker.js` のPyodideで `work_bridge.py` を実行します。`web/build_tools.py` は元のPythonソースからブラウザで使う関数を生成し、同梱PDF・モックJSON・固定バージョンのPDF/OCRライブラリとライセンスを配布ディレクトリへコピーします。ネットワークAPIクライアントやネイティブPDF/OCR依存は生成したPythonコアに含めません。CSV・Excelへの文字列出力は数式として解釈されないよう処理しています。

静的HTML／CSS／JavaScriptと、Web Worker内で動作するPyodide 0.27.7を使っています。
`dist/python/renewal.py` と `extract_renewals.py` は元の契約更新デモからビルド時にコピーし、計算ルールを共有しています。
初回表示には生成済みのサンプル結果を使い、「更新対象を抽出」を押すとPythonで再計算します。両者は画面に区別して表示します。

`browser_bridge.py` がCSVの入力検証とファイル出力を担当します。CSV／Excelに出力する文字列は、数式として解釈されないように処理しています。ダウンロードの内容は一覧の検索条件に関係なく、抽出結果全体です。

## ローカル実行

リポジトリルートから実行してください。

```powershell
python -m pip install openpyxl==3.1.5 python-dateutil pytest
npm ci --prefix web
python -X utf8 web/build.py
python -X utf8 web/build_tools.py
python -m http.server 8765 --bind 127.0.0.1 --directory web/dist
```

ブラウザで `http://127.0.0.1:8765/` を開くと紹介ページ、`/demo/`・`/invoices/`・`/leads/` で各デモを表示します。ビルド時の依存・OCRモデル取得と、初回のPyodide起動にはインターネット接続が必要です。PDF/OCRライブラリと日本語モデルはサイトと同じ配信元から取得します。モデルはブラウザのIndexedDBにキャッシュしますが、入力PDF・抽出結果は永続保存しません。

```powershell
python -m pytest -q "3_契約更新抽出/tests" web/tests
```

元の62件＋契約更新Webアダプター12件＋追加デモ17件＝91テストを検証済みです。ブラウザ操作の確認範囲は [QA.md](QA.md) を参照してください。

## Vercelへの公開

`web/vercel.json` はビルド済みの `dist/` を静的ファイルとして配信します。計算処理を変更した場合は `web/build.py` とテストを実行してからデプロイしてください。

```powershell
vercel link --cwd web --project koushin-checker-jun0908 --scope jkawai0908-9469s-projects --yes
vercel deploy --cwd web --project koushin-checker-jun0908 --scope jkawai0908-9469s-projects --prod
```

## 配布ライブラリ

- Pythonの日時計算：python-dateutil（Pyodide配布パッケージ）。
- Excel出力：openpyxl 3.1.5、et_xmlfile 2.0.0（MITライセンス）。wheel内に各ライセンス文書を保持しています。
- Python実行環境：Pyodide 0.27.7（CDNから取得）。
- 書体：Google FontsのDM Sans／Noto Sans JP。読み込みできない場合は端末の標準書体を使用します。
- PDF.js 6.4.299（Apache-2.0）とTesseract.js 7.0.0／Tesseract.js-core（Apache-2.0）。配布ディレクトリにライセンスを保持しています。
- 日本語OCRモデル：`@tesseract.js-data/jpn@1.0.0/4.0.0`。Web版は画像の二値化・ノイズ除去・傾き補正後、PSM 6で読み取ります。

## 制約

同一期間で継続する契約を想定した業務デモです。実際の契約条件、途中の期間変更、再雇用、異動履歴は別途確認してください。雇止め予告期限・無期転換関連フラグは簡略化した参考値です。サンプルはすべて架空です。
