# 炭火焼肉店 営業リスト作成デモ（社内検証用）

CrowdWorks 案件 [13516755](https://crowdworks.jp/public/jobs/13516755)「関東の炭を使っている焼肉屋さんの営業リスト作成」を想定した**社内デモ**です。応募・外部送信・投稿は一切していません。

対象エリア（求人ページに書かれている 8 エリア。2026-10-11 に取得）:
**青梅・瑞穂・福生・羽村・昭島・所沢・飯能・入間**
（瑞穂 = 東京都西多摩郡瑞穂町、入間 = 埼玉県入間市。「入間郡」の三芳町などは対象外として判定しています）

## ファイル構成

| パス | 内容 |
| --- | --- |
| `yakiniku_leads.py` | 本番用スクリプト（Places API (New) Text Search + 任意で Place Details） |
| `make_mock.py` | モック JSON を作るスクリプト（**架空データ**） |
| `mock/` | Places API (New) `searchText` レスポンスと同じ形のモック JSON・`index.json`・`README_MOCK.md` |
| `osm_trial.py` | OpenStreetMap Overpass API での実データ試行（APIキー不要） |
| `output/mock_leads.csv / .xlsx` | モック実行の結果（架空データ） |
| `output/mock_leads_excluded.csv` | モック実行で除外した店舗と理由 |
| `output/mock_leads_summary.json` | モック実行の集計 |
| `output/osm_trial.csv / osm_trial_summary.json` | OSM 試行の結果（© OpenStreetMap contributors） |

## セットアップ

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install requests openpyxl
```

### API キー（環境変数）

Google Cloud で **Places API (New)** を有効化し、API キーを発行してください（API 制限で Places API (New) のみに絞ることを推奨）。
キーはコードに書かず、環境変数で渡します。

```bash
export GOOGLE_PLACES_API_KEY="（発行したキー）"
```

## 実行方法

```bash
# モック（API に一切アクセスしない・架空データ）
python3 yakiniku_leads.py --mock -v

# 本番：8エリア × 既定キーワード（炭火焼肉 / 焼肉 / 七輪 焼肉 / ホルモン）
python3 yakiniku_leads.py -v

# エリア・キーワードを指定
python3 yakiniku_leads.py --areas 青梅 所沢 --keywords 炭火焼肉 焼肉 ホルモン 七輪

# コスト節約モード：検索では口コミを取らず、店名で炭火確定できなかった店だけ Place Details で口コミ/概要を取得
python3 yakiniku_leads.py --review-source details

# OSM 試行（APIキー不要。1エリア1クエリ・待機あり）
python3 osm_trial.py
python3 osm_trial.py --reprocess   # 再取得せず判定だけ再適用
```

出力先は `output/`（`--out-dir` で変更可）。CSV は **UTF-8 BOM 付き**なので Excel でそのまま開けます。xlsx はシート「リスト / 除外 / 集計 / 注記」で、見出し固定・オートフィルタ・判定の色分け・URL リンク付きです。

## 処理の流れ

1. エリアごとに `「{キーワード} {市町名}」` で `places:searchText` を実行（`languageCode=ja`, `regionCode=JP`, `pageSize=20`, エリア中心の `locationBias`）。
2. `nextPageToken` で最大 3 ページ（1 クエリ最大 60 件）まで取得。
3. 429 / 5xx は指数バックオフでリトライ（最大 5 回）。リクエスト間隔は `--min-interval`（既定 0.2 秒）。
4. 重複排除：① `place_id` → ② 正規化した店名（NFKC・空白/記号除去）＋電話番号、または店名＋正規化住所。
5. 住所でエリアを判定（例：「東京都青梅市」「埼玉県入間市」）。8 エリア外・閉業（`CLOSED_PERMANENTLY`）・焼肉と関係ない店（例：「炭火焙煎珈琲」）は「除外」シートへ。
6. 炭火判定:
   - **確定**：店名か editorialSummary に「炭火・七輪・備長炭・炭焼」などの言葉がある
   - **可能性**：口コミ（最大 5 件）に炭火関連の言葉がある（「炭の香り」なども含む）
   - **不明**：根拠がない／口コミに「無煙ロースター」「ガス火」などガスをうかがわせる言葉が同じくらい以上ある
   - 根拠は「判定根拠」列に入ります（例：`店名に「炭火」`、`口コミに「七輪」(1/2件)`、`editorialSummaryに「炭火」`）

出力列: エリア, 店名, 住所, 電話, 評価, 口コミ件数, GoogleマップURL, 公式サイトURL, 炭火判定, 判定根拠, place_id, ヒット検索語, 備考

## FieldMask と料金の目安（※要確認）

| モード | FieldMask | 想定 SKU |
| --- | --- | --- |
| `--review-source search`（既定） | id, displayName, formattedAddress, googleMapsUri, types, primaryType, businessStatus, nationalPhoneNumber, rating, userRatingCount, websiteUri, editorialSummary, reviews, nextPageToken | Text Search **Enterprise + Atmosphere** |
| `--review-source details` | 検索は reviews/editorialSummary 抜き → 未確定店だけ Details で reviews, editorialSummary | Text Search Enterprise ＋ Place Details Enterprise + Atmosphere |
| `--review-source none` | 口コミ・概要なし | Text Search Enterprise |

**料金は Google 公式の料金表を直接は確認できていません。** 第三者サイトの料金計算ツール（2026-07 時点で Google の料金表と照合済みと書かれています）と公式ドキュメントの SKU 説明をもとにした目安です。発注前に必ず https://mapsplatform.google.com/pricing/ で確認してください。

- Text Search Enterprise + Atmosphere：約 $40 / 1,000 リクエスト（無料枠 約 1,000 回/月/SKU）
- Text Search Enterprise：約 $35 / 1,000 ／ Place Details Enterprise + Atmosphere：約 $25 / 1,000
- 2025年3月から「$200 の月額クレジット」が SKU ごとの無料枠に変わっています。
- 試算：8 エリア × 4 キーワード × 最大 3 ページ ＝ **最大 96 リクエスト** → 無料枠を超えても約 $4 程度（ページ数が少なければもっと減ります）。キーワードを 8 個に増やしても 200 回弱です。
- Google Cloud 側で **予算アラート・1 日あたりのクォータ上限**を設定しておくことをおすすめします。

## 注意点・制約

- **「炭火」を表す属性は Places API にありません。** 判定は店名・editorialSummary・口コミの言葉から推測したものです。「可能性」「不明」の店は、電話や公式サイトで確認する前提です。
- 口コミは **1 店舗につき最大 5 件** しか取れません（どの口コミが返るかは Google 次第）。editorialSummary が付いていない店も多いです。
- Text Search は **1 クエリ最大 60 件（20 件 × 3 ページ）** です。取りこぼしを減らすため、エリア × キーワードに分けて検索しています。所沢のような広いエリアでは、町名ごとにさらに分けることも検討してください。
- **利用規約（重要・要確認）**：Google Maps Platform の規約では、Places のコンテンツ（店名・住所・電話・評価など）は、原則として place_id 以外をキャッシュ・保存・Google マップ以外の用途に書き出すことが制限されています。表示するときは帰属表示も必要です。**取得結果を「静的な営業リスト（CSV/スプレッドシート）」として納品・保存し続ける使い方は、規約に抵触するおそれがあります。** 本番運用の前に、クライアントと一緒に最新の規約（Service Specific Terms / Places API Policies）を確認してください。代わりの方法としては、place_id だけを保存して使うたびに再取得する、OSM などライセンスが明確なデータを使う、手作業で確認する、などがあります。
- OSM（`osm_trial.py`）は ODbL です。使うときは **「© OpenStreetMap contributors」** の表示が必要で、加工したデータベースを配布する場合は同じライセンス（share-alike）の条件がかかります。Overpass は公共の共有サーバーなので、軽く使う程度にとどめてください。
- Google マップ・食べログ・ホットペッパーなどのスクレイピングは行いません（規約違反になるため）。

## モックデータについて

`mock/` と `output/mock_leads.*` はすべて**架空データ**です（店名に【架空】、電話は `0428-00-0001` のような実在しない形式、URL は example.com とダミーの cid）。「備考」列と xlsx の「注記」シートにも架空であることを書いています。わざと次のケースを入れています：エリアをまたいだ重複、place_id が違う同じ店（全角スペース・全角数字の表記ゆれ）、ページング（3 ページ）、ガスロースターの焼肉店、エリア外（狭山市・入間郡三芳町）、閉業、焼肉以外（炭火焙煎珈琲）。
