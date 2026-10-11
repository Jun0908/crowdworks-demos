# Koushin — 契約更新チェッカー Web版

**紹介サイト：[Koushinを知る](https://koushin-checker-jun0908.vercel.app/)**

**操作デモ：[Koushinを試す](https://koushin-checker-jun0908.vercel.app/demo/)**（ログイン不要）

サンプル250名またはCSVを読み込み、契約更新対象者の抽出からAM別の確認資料作成までをブラウザ内で行います。

## 機能

- 対象月、先読み期間（0〜2ヶ月）、終了日規約（3種類）を変更して再計算。
- 対象者・旧方式で漏れる3ヶ月契約者・要確認データ・退職予定者の切り替え。
- 氏名／職員ID検索、担当AMによる絞り込み、ページ送り。
- AM別Excel、対象者CSV、確認依頼文ZIPのダウンロード。
- CSV入力：UTF-8／Shift-JIS、最大2MB・5,000行。
- 入力データはブラウザ内のみで処理。サーバー送信、永続保存、メール送信はありません。

## 構成

トップページ（`dist/index.html`・`intro.css`）では、解決する課題、機能、サンプルの比較結果、操作画面、使い方、FAQを紹介します。各CTAから `dist/demo/index.html` の操作デモへ進み、デモの「製品紹介」リンクからトップに戻れます。トップページでは計算エンジンを読み込みません。

静的HTML／CSS／JavaScriptと、Web Worker内で動作するPyodide 0.27.7を使っています。
`dist/python/renewal.py` と `extract_renewals.py` は元の契約更新デモからビルド時にコピーし、計算ルールを共有しています。
初回表示には生成済みのサンプル結果を使い、「更新対象を抽出」を押すとPythonで再計算します。両者は画面に区別して表示します。

`browser_bridge.py` がCSVの入力検証とファイル出力を担当します。CSV／Excelに出力する文字列は、数式として解釈されないように処理しています。ダウンロードの内容は一覧の検索条件に関係なく、抽出結果全体です。

## ローカル実行

リポジトリルートから実行してください。

```powershell
python -m pip install openpyxl==3.1.5 python-dateutil pytest
python -X utf8 web/build.py
python -m http.server 8765 --bind 127.0.0.1 --directory web/dist
```

ブラウザで `http://127.0.0.1:8765/` を開くと紹介ページ、`http://127.0.0.1:8765/demo/` で操作デモを表示します。Python実行環境はjsDelivrから読み込むため、初回の計算エンジン起動にはインターネット接続が必要です。失敗時は画面上の再読み込みボタンから再試行できます。

```powershell
python -m pytest -q "3_契約更新抽出/tests" web/tests
```

元の62件＋Webアダプター12件＝74テストを検証済みです。ブラウザ操作の確認範囲は [QA.md](QA.md) を参照してください。

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

## 制約

同一期間で継続する契約を想定した業務デモです。実際の契約条件、途中の期間変更、再雇用、異動履歴は別途確認してください。雇止め予告期限・無期転換関連フラグは簡略化した参考値です。サンプルはすべて架空です。
