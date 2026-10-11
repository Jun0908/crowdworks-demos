#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OpenStreetMap Overpass API による実データ試行（APIキー不要・軽量利用）。
- 1エリア1クエリ（計8回）、クエリ間は数秒待機、User-Agent明示。
- データ: © OpenStreetMap contributors（ODbL 1.0）https://www.openstreetmap.org/copyright
"""
import csv
import json
import sys
import time
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent
OUT = BASE / "output"
ENDPOINT = "https://overpass-api.de/api/interpreter"
UA = "crowdworks-demo-yakiniku-leads/0.1 (internal demo; contact: none; low-volume)"
ATTR = "© OpenStreetMap contributors (ODbL)"
AREAS = [("青梅", "青梅市"), ("瑞穂", "瑞穂町"), ("福生", "福生市"), ("羽村", "羽村市"),
         ("昭島", "昭島市"), ("所沢", "所沢市"), ("飯能", "飯能市"), ("入間", "入間市")]
CHARCOAL = ["炭火", "七輪", "備長炭", "炭焼", "七厘", "charcoal", "sumibi"]

Q = """[out:json][timeout:90];
area["name"="{name}"]["boundary"="administrative"]["admin_level"="7"]->.a;
(
  nwr(area.a)["amenity"~"^(restaurant|fast_food|bar|pub|food_court)$"]["cuisine"~"yakiniku|barbecue|bbq|korean|horumon|jingisukan",i];
  nwr(area.a)["amenity"~"^(restaurant|fast_food|bar|pub|food_court)$"]["name"~"焼肉|焼き肉|やきにく|ホルモン|七輪|炭火|ジンギスカン"];
);
out center tags;"""


YAKINIKU_NAME = ["焼肉", "焼き肉", "やきにく", "ホルモン", "yakiniku", "ジンギスカン", "七輪"]
NON_YAKINIKU_NAME = ["やきとり", "焼鳥", "焼き鳥", "串", "居酒屋"]


def yakiniku_flag(name, cuisine):
    """焼肉関連性: ○=店名/cuisineで焼肉系 / △=韓国・BBQタグのみ / ×=焼鳥・居酒屋等"""
    n, c = name.lower(), cuisine.lower()
    if any(w in n for w in NON_YAKINIKU_NAME) and not any(w in n for w in YAKINIKU_NAME):
        return "×"
    if any(w in n for w in YAKINIKU_NAME) or "yakiniku" in c or "horumon" in c:
        return "○"
    return "△"


def finalize(rows):
    for r in rows:
        r["焼肉関連"] = yakiniku_flag(r["店名"], r["cuisine"])
        if r["焼肉関連"] == "×" and r["炭火判定"] == "確定":
            r["炭火判定"] = "対象外(焼肉以外)"
    return rows


def main():
    OUT.mkdir(exist_ok=True)
    rows, seen, log = [], set(), []
    s = requests.Session()
    s.headers["User-Agent"] = UA
    for disp, name in AREAS:
        els = None
        for attempt in (1, 2):  # 504/429 時は1回だけ30秒後に再試行（軽量利用）
            try:
                r = s.post(ENDPOINT, data={"data": Q.format(name=name)}, timeout=120)
                r.raise_for_status()
                els = r.json().get("elements", [])
                break
            except Exception as e:
                err = e
                print(f"{disp}: attempt{attempt} 失敗 {e}", file=sys.stderr)
                time.sleep(30)
        if els is None:
            log.append(f"{disp}: 失敗 {err}")
            continue
        n = 0
        for e in els:
            key = f"{e['type']}/{e['id']}"
            if key in seen:
                continue
            seen.add(key)
            t = e.get("tags", {})
            lat = e.get("lat") or e.get("center", {}).get("lat")
            lon = e.get("lon") or e.get("center", {}).get("lon")
            nm = t.get("name", "")
            hay = " ".join([nm, t.get("name:en", ""), t.get("cuisine", ""), t.get("description", "")]).lower()
            hit = [w for w in CHARCOAL if w.lower() in hay]
            addr = "".join(t.get(k, "") for k in ("addr:province", "addr:city", "addr:quarter",
                                                   "addr:neighbourhood", "addr:block_number", "addr:housenumber"))
            rows.append({
                "エリア": disp, "店名": nm, "住所(OSMタグ)": addr or t.get("addr:full", ""),
                "電話": t.get("phone", "") or t.get("contact:phone", ""),
                "公式サイトURL": t.get("website", "") or t.get("contact:website", ""),
                "cuisine": t.get("cuisine", ""), "amenity": t.get("amenity", ""),
                "炭火判定": "確定" if hit else "不明",
                "判定根拠": f"店名/タグに「{hit[0]}」" if hit else "",
                "緯度": lat, "経度": lon,
                "OSM_URL": f"https://www.openstreetmap.org/{key}",
                "出典": ATTR,
            })
            n += 1
        log.append(f"{disp}: {n}件")
        print(log[-1], file=sys.stderr)
        time.sleep(5)
    rows = finalize(rows)
    cols = ["エリア", "焼肉関連", "店名", "住所(OSMタグ)", "電話", "公式サイトURL", "cuisine", "amenity",
            "炭火判定", "判定根拠", "緯度", "経度", "OSM_URL", "出典"]
    with (OUT / "osm_trial.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
        f.write(f"# データ出典: {ATTR} https://www.openstreetmap.org/copyright\n")
    summ = {
        "total": len(rows),
        "yakiniku_flag": {k: sum(r["焼肉関連"] == k for r in rows) for k in "○△×"},
        "charcoal_confirmed_yakiniku": sum(r["炭火判定"] == "確定" for r in rows),
        "charcoal_but_not_yakiniku": sum(r["炭火判定"] == "対象外(焼肉以外)" for r in rows),
        "with_phone": sum(bool(r["電話"]) for r in rows),
        "with_website": sum(bool(r["公式サイトURL"]) for r in rows),
        "with_address": sum(bool(r["住所(OSMタグ)"]) for r in rows),
        "unnamed": sum(not r["店名"] for r in rows),
        "by_area": {d: sum(r["エリア"] == d for r in rows) for d, _ in AREAS},
        "log": log, "attribution": ATTR,
    }
    (OUT / "osm_trial_summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=2))


def reprocess():
    """API を再度叩かず、既存の osm_trial.csv に判定だけ再適用する。"""
    path = OUT / "osm_trial.csv"
    lines = [l for l in path.read_text(encoding="utf-8-sig").splitlines(True) if not l.startswith("#")]
    rows = list(csv.DictReader(lines))
    for r in rows:
        if r.get("炭火判定") == "対象外(焼肉以外)":
            r["炭火判定"] = "確定"
    rows = finalize(rows)
    cols = ["エリア", "焼肉関連"] + [c for c in rows[0] if c not in ("エリア", "焼肉関連")]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader(); w.writerows(rows)
        f.write(f"# データ出典: {ATTR} https://www.openstreetmap.org/copyright\n")
    sp = OUT / "osm_trial_summary.json"
    summ = json.loads(sp.read_text(encoding="utf-8"))
    summ.pop("charcoal_confirmed", None)
    summ["yakiniku_flag"] = {k: sum(r["焼肉関連"] == k for r in rows) for k in "○△×"}
    summ["charcoal_confirmed_yakiniku"] = sum(r["炭火判定"] == "確定" for r in rows)
    summ["charcoal_but_not_yakiniku"] = sum(r["炭火判定"] == "対象外(焼肉以外)" for r in rows)
    sp.write_text(json.dumps(summ, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summ, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    reprocess() if "--reprocess" in sys.argv else main()
