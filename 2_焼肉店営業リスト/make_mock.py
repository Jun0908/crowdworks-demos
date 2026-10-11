#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""モック JSON 生成（すべて架空データ）。Places API (New) searchText レスポンスと同じ形。
店名は【架空】付き、電話は 0428-00-0001 のような架空形式、URL は example.com / ダミー cid。"""
import json
from pathlib import Path

D = Path(__file__).resolve().parent / "mock"
D.mkdir(exist_ok=True)


def rv(text):
    return {"name": "places/MOCK/reviews/x", "rating": 4, "text": {"text": text, "languageCode": "ja"},
            "originalText": {"text": text, "languageCode": "ja"},
            "authorAttribution": {"displayName": "架空レビュアー"}}


def place(pid, name, addr, phone=None, rating=None, cnt=None, web=None, summary=None,
          reviews=None, types=None, status="OPERATIONAL"):
    p = {"id": pid, "displayName": {"text": name, "languageCode": "ja"},
         "formattedAddress": addr,
         "googleMapsUri": f"https://maps.google.com/?cid=000000000000{pid[-4:]}",
         "types": types or ["yakiniku_restaurant", "restaurant", "food", "point_of_interest", "establishment"],
         "primaryType": (types or ["yakiniku_restaurant"])[0], "businessStatus": status}
    if phone: p["nationalPhoneNumber"] = phone
    if rating is not None: p["rating"] = rating
    if cnt is not None: p["userRatingCount"] = cnt
    if web: p["websiteUri"] = web
    if summary: p["editorialSummary"] = {"text": summary, "languageCode": "ja"}
    if reviews: p["reviews"] = [rv(t) for t in reviews]
    return p


P = {
 "ome1": place("MOCK_PLACE_0001", "【架空】炭火焼肉 サンプル亭 青梅店", "日本、〒198-0000 東京都青梅市サンプル町1-1-1",
              "0428-00-0001", 4.2, 123, "https://example.com/sample-tei",
              reviews=["炭火で焼くカルビが香ばしい（架空）", "店内は少し煙たいです（架空）"]),
 "ome2": place("MOCK_PLACE_0002", "【架空】焼肉 テスト苑", "日本、〒198-0000 東京都青梅市テスト町2-2",
              "0428-00-0002", 3.9, 45, reviews=["七輪で出てくるのが良い（架空）", "タンが美味しい（架空）"]),
 "mizuho1": place("MOCK_PLACE_0003", "【架空】ホルモン サンプル横丁", "日本、〒190-1200 東京都西多摩郡瑞穂町ダミー3-3",
              "042-000-0003", 4.0, 67, summary="炭火で焼くホルモンが名物の大衆店（架空）"),
 "fussa1": place("MOCK_PLACE_0004", "【架空】焼肉 ダミー館 福生店", "日本、〒197-0000 東京都福生市モック4-4",
              "042-000-0004", 3.5, 210, "https://example.com/dummy-kan",
              reviews=["無煙ロースターで服が臭くならない（架空）", "ガス火なので炭火の香りはない（架空）"]),
 "hamura1": place("MOCK_PLACE_0005", "【架空】七輪焼肉 モック家", "日本、〒205-0000 東京都羽村市サンプル5-5",
              "0428-00-0005", 4.4, 88),
 "aki1": place("MOCK_PLACE_0006", "【架空】炭火焼肉 架空園 昭島店", "日本、〒196-0000 東京都昭島市テスト6-6",
              "042-000-0006", 4.1, 150),
 # 同一店舗だが place_id が異なる（全角スペース・表記ゆれ）→ 店名+電話で重複排除される想定
 "aki1b": place("MOCK_PLACE_0006B", "【架空】炭火焼肉　架空園　昭島店", "日本、〒196-0000 東京都昭島市テスト６－６",
              "042-000-0006", None, None),
 "aki2": place("MOCK_PLACE_0007", "【架空】焼肉 サンプル苑 昭島", "日本、〒196-0000 東京都昭島市ダミー7-7",
              "042-000-0007", 3.8, 30, status="CLOSED_PERMANENTLY"),
 "toko1": place("MOCK_PLACE_0008", "【架空】焼肉 ダミー亭 所沢本店", "日本、〒359-0000 埼玉県所沢市サンプル8-8",
              "04-0000-0008", 4.0, 300, reviews=["炭の香りがして最高（架空）"]),
 "toko2": place("MOCK_PLACE_0009", "【架空】炭焼き焼肉 テスト所沢", "日本、〒359-0000 埼玉県所沢市テスト9-9",
              "04-0000-0009", 4.3, 95),
 "toko3": place("MOCK_PLACE_0010", "【架空】焼肉 モック苑 所沢", "日本、〒359-0000 埼玉県所沢市モック10-10",
              "04-0000-0010", 3.6, 12),
 "toko4": place("MOCK_PLACE_0011", "【架空】韓国焼肉 サンプル", "日本、〒359-0000 埼玉県所沢市ダミー11-11",
              "04-0000-0011", 4.1, 77, types=["korean_restaurant", "restaurant"],
              reviews=["サムギョプサルが美味しい（架空）"]),
 "toko5": place("MOCK_PLACE_0012", "【架空】炭火焼肉 所沢サンプル館", "日本、〒359-0000 埼玉県所沢市サンプル12-12",
              "04-0000-0012", 4.5, 410, "https://example.com/tokorozawa-sample"),
 "toko6": place("MOCK_PLACE_0013", "【架空】焼肉 テスト庵 所沢", "日本、〒359-0000 埼玉県所沢市テスト13-13",
              None, 3.2, 5),
 "hanno1": place("MOCK_PLACE_0014", "【架空】備長炭焼肉 テスト家 飯能", "日本、〒357-0000 埼玉県飯能市サンプル14-14",
              "042-000-0014", 4.6, 58),
 "iruma1": place("MOCK_PLACE_0015", "【架空】焼肉 サンプル食堂 入間", "日本、〒358-0000 埼玉県入間市ダミー15-15",
              "04-0000-0015", 3.7, 20),
 # エリア外（狭山市）
 "out1": place("MOCK_PLACE_0016", "【架空】炭火焼肉 圏外亭 狭山", "日本、〒350-1300 埼玉県狭山市圏外16-16",
              "04-0000-0016", 4.0, 40),
 # 「入間郡」トラップ（入間市ではない）
 "out2": place("MOCK_PLACE_0017", "【架空】焼肉 サンプル 三芳", "日本、〒354-0000 埼玉県入間郡三芳町ダミー17-17",
              "049-000-0017", 3.9, 22),
 # 焼肉ではない（店名に「炭火」を含むがカフェ）
 "cafe": place("MOCK_PLACE_0018", "【架空】炭火焙煎珈琲 サンプル", "日本、〒198-0000 東京都青梅市カフェ18-18",
              "0428-00-0018", 4.3, 60, types=["cafe", "food"]),
}

def resp(keys, token=None):
    r = {"places": [P[k] for k in keys]}
    if token:
        r["nextPageToken"] = token
    return r

files = {
 "ome_sumibi.json": resp(["ome1", "cafe"]),
 "ome_yakiniku.json": resp(["ome1", "ome2"]),               # ome1 は同一エリア内重複
 "mizuho_horumon.json": resp(["mizuho1"]),
 "fussa_yakiniku.json": resp(["fussa1"]),
 "hamura_yakiniku.json": resp(["hamura1", "ome1"]),         # 青梅の店が羽村検索でもヒット（エリア跨ぎ重複）
 "hamura_shichirin.json": resp(["hamura1"]),
 "akishima_sumibi.json": resp(["aki1", "aki1b"]),
 "akishima_yakiniku.json": resp(["aki1", "aki2"]),
 "tokorozawa_yakiniku_p1.json": resp(["toko1", "toko2", "toko3"], "MOCK_TOKEN_TOKO_P2"),
 "tokorozawa_yakiniku_p2.json": resp(["toko4", "toko5"], "MOCK_TOKEN_TOKO_P3"),
 "tokorozawa_yakiniku_p3.json": resp(["toko6"]),
 "tokorozawa_sumibi.json": resp(["toko2", "toko5"]),
 "hanno_sumibi.json": resp(["hanno1"]),
 "iruma_yakiniku.json": resp(["iruma1", "out1", "out2", "hanno1"]),  # エリア外2件 + 飯能店の跨ぎ重複
}
for f, data in files.items():
    (D / f).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

index = {
 "_note": "【架空データ】すべての店舗・住所・電話番号・URLは架空です。実在しません。",
 "queries": {
  "炭火焼肉 青梅市": "ome_sumibi.json", "焼肉 青梅市": "ome_yakiniku.json",
  "ホルモン 瑞穂町": "mizuho_horumon.json", "焼肉 福生市": "fussa_yakiniku.json",
  "焼肉 羽村市": "hamura_yakiniku.json", "七輪 焼肉 羽村市": "hamura_shichirin.json",
  "炭火焼肉 昭島市": "akishima_sumibi.json", "焼肉 昭島市": "akishima_yakiniku.json",
  "焼肉 所沢市": "tokorozawa_yakiniku_p1.json", "炭火焼肉 所沢市": "tokorozawa_sumibi.json",
  "炭火焼肉 飯能市": "hanno_sumibi.json", "焼肉 入間市": "iruma_yakiniku.json",
 },
 "pages": {"MOCK_TOKEN_TOKO_P2": "tokorozawa_yakiniku_p2.json",
           "MOCK_TOKEN_TOKO_P3": "tokorozawa_yakiniku_p3.json"},
 "details": {},
}
(D / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
(D / "README_MOCK.md").write_text("# モックデータについて\n\nこのフォルダの JSON はすべて**架空データ**です。店名には【架空】を付け、電話番号は 0428-00-0001 のような架空形式、URL は example.com とダミーの cid を使っています。実在の店舗とは一切関係ありません。\n\n形式は Places API (New) `places:searchText` のレスポンス（`places[]`, `nextPageToken`）と同じです。`index.json` で検索クエリ・pageToken とファイルを対応付けています。\n", encoding="utf-8")
print("mock files:", len(files), "places:", len(P))
