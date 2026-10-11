#!/usr/bin/env python3
"""extracted.json と ground_truth.json を突き合わせ、ファイル×項目ごとに 正解/未取得/誤り を出す。
使い方: python evaluate.py output/extracted.json ground_truth.json [-o output/accuracy_report.md]
"""
import argparse, json, re, unicodedata
from pathlib import Path

def n(s):  # 比較用正規化: NFKC + 空白除去
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s))) if s is not None else None

FIELDS = [("invoice_date", "請求日"), ("total", "金額"), ("vendor", "取引先"), ("bank", "振込先"),
          ("due_date", "支払期日"), ("category", "勘定科目")]
BANK_KEYS = ["bank", "branch", "type", "number", "holder"]

def judge(field, got, exp):
    if field == "bank":
        got = got or {}
        if not any(got.values()): return "未取得", ""
        bad = [k for k in BANK_KEYS if n(got.get(k)) != n(exp[k])]
        if not bad: return "正解", ""
        miss = [k for k in bad if not got.get(k)]
        st = "未取得" if len(miss) == len(bad) else "誤り"
        return st, "; ".join(f"{k}: {got.get(k)!r}≠{exp[k]!r}" for k in bad)
    if field == "category" and got == "要確認": return "未取得", "要確認(判定不能)"
    if got is None: return "未取得", ""
    return ("正解", "") if n(got) == n(exp) else ("誤り", f"{got!r}≠{exp!r}")

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("extracted"); ap.add_argument("truth"); ap.add_argument("-o")
    a = ap.parse_args()
    ex = {r["file"]: r for r in json.load(open(a.extracted))}
    gt = json.load(open(a.truth))
    hdr = "| ファイル | 方式 | " + " | ".join(j for _, j in FIELDS) + " |"
    out = [hdr, "|" + "---|" * (len(FIELDS) + 2)]
    fails, tally = [], {j: [0, 0, 0] for _, j in FIELDS}
    mark = {"正解": "○", "未取得": "－", "誤り": "×"}
    for f, exp in gt.items():
        r = ex.get(f, {})
        cells = []
        for k, j in FIELDS:
            st, det = judge(k, r.get(k), exp[k])
            tally[j][["正解", "未取得", "誤り"].index(st)] += 1
            cells.append(mark[st] + st)
            if st != "正解": fails.append(f"- {f} / {j}: {st} {det}")
        out.append(f"| {f} | {'OCR' if 'OCR' in r.get('method', '') else 'text'} | " + " | ".join(cells) + " |")
    out += ["", "| 項目 | 正解 | 未取得 | 誤り | 正解率 |", "|---|---|---|---|---|"]
    tot = [0, 0, 0]
    for j, (o, m, x) in tally.items():
        out.append(f"| {j} | {o} | {m} | {x} | {o/(o+m+x):.0%} |"); tot = [tot[0]+o, tot[1]+m, tot[2]+x]
    out.append(f"| **全体** | {tot[0]} | {tot[1]} | {tot[2]} | {tot[0]/sum(tot):.0%} |")
    out += ["", "### 不一致の詳細"] + (fails or ["- なし"])
    txt = "\n".join(out); print(txt)
    if a.o: Path(a.o).write_text(txt + "\n")

if __name__ == "__main__": main()
