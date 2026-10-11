"""架空の有期契約職員CSVを生成する（実在の人物・組織とは無関係）。

使い方: python generate_staff.py [--n 250] [--seed 20261011] [--as-of 2026-10-11] [--out data/staff.csv]

「契約終了日」列は実務の給与ファイルを模して、以下を意図的に混在させる:
  - 正しい現行期の終了日
  - 空欄（計算で補う前提）
  - 1期前の終了日（前回更新が給与ファイルに未反映 = 3ヶ月契約で起きやすい）
"""
import argparse
import csv
import random
from datetime import date, timedelta

from renewal import current_term, term_end

AREAS = {  # エリア: [エリアマネージャー（架空）]
    "北海道": ["架空 北斗AM"],
    "東北": ["架空 青葉AM"],
    "関東A": ["架空 武蔵AM", "架空 相模AM"],
    "関東B": ["架空 常陸AM"],
    "中部": ["架空 尾張AM", "架空 三河AM"],
    "関西": ["架空 難波AM", "架空 播磨AM"],
    "中国四国": ["架空 吉備AM"],
    "九州": ["架空 筑紫AM", "架空 薩摩AM"],
}
SURNAMES = ["仮野", "試田", "例川", "見本", "模擬", "架山", "想原", "虚木", "仮谷", "試村", "例野", "見原"]
GIVEN = ["一郎", "花子", "二郎", "桜", "三郎", "葵", "四郎", "楓", "五郎", "栞", "六実", "七海"]
HEADER = ["職員ID", "氏名", "エリア", "エリアマネージャー", "契約開始日", "契約期間(月)",
          "契約終了日", "更新回数(反映済)", "在籍状態", "備考"]

# (開始日, 期間, 備考, 上書きフィールド)
EDGE_CASES = [
    ("2025-08-31", 3, "エッジ: 8/31開始3ヶ月→11/30, 2/28, 5/30, 8/30, 11/30…", {}),
    ("2024-11-30", 3, "エッジ: 11/30開始3ヶ月→2/28満了（応当日なし→月末）", {}),
    ("2023-11-30", 3, "エッジ: 11/30開始3ヶ月→2024/2/29（閏年）", {}),
    ("2025-01-31", 1, "エッジ: 31日開始1ヶ月→2/28, 3/30, 4/30…", {}),
    ("2026-05-31", 6, "エッジ: 5/31開始6ヶ月→11/30（応当日なし→月末）", {}),
    ("2025-10-31", 1, "エッジ: 31日開始1ヶ月（毎月満了）", {}),
    ("2024-02-29", 12, "エッジ: 閏日開始12ヶ月→2025/2/28, 2026/2/28, 2028/2/28", {}),
    ("2026-09-01", 3, "エッジ: 1日開始3ヶ月→11/30（前月末満了）", {}),
    ("2025-12-01", 3, "エッジ: 1日開始3ヶ月→2/28, 5/31, 8/31, 11/30", {}),
    ("2025-08-01", 3, "エッジ: 1日開始3ヶ月→10/31満了（開始月ベースだと11月と誤判定）", {}),
    ("2026-08-12", 3, "エッジ: 四半期非整合3ヶ月→11/11満了（初回更新）", {}),
    ("2025-05-20", 3, "エッジ: 四半期非整合3ヶ月→11/19満了", {}),
    ("2024-02-15", 3, "エッジ: 四半期非整合3ヶ月→11/14満了（更新10回目）", {}),
    ("2026-02-28", 3, "エッジ: 2/28開始3ヶ月→5/27, 8/27, 11/27", {}),
    ("2021-12-01", 12, "エッジ: 通算5年到達見込（無期転換）11/30満了", {}),
    ("2025-11-15", 12, "エッジ: 12ヶ月 初回満了11/14", {}),
    ("2026-05-16", 6, "エッジ: 6ヶ月 初回満了11/15", {}),
    ("2025-08-20", 3, "データ不備: AM未設定", {"エリアマネージャー": ""}),
    ("2026-02-10", 3, "データ不備: AM未設定", {"エリアマネージャー": ""}),
    ("2025-02-30", 3, "データ不備: 存在しない日付", {}),
    ("2025/13/01", 6, "データ不備: 月が13", {}),
    ("", 3, "データ不備: 開始日空欄", {}),
    ("2025-05-10", 2, "データ不備: 想定外の契約期間", {}),
    ("2025-08-25", 3, "データ不備: 終了日列が周期と不一致（期間変更?）", {"契約終了日": "2026-12-31"}),
    ("2025-11-05", 3, "退職予定（本来11/4満了だが除外）", {"在籍状態": "退職予定"}),
    ("2026-05-25", 6, "退職予定（本来11/24満了だが除外）", {"在籍状態": "退職予定"}),
]


def rand_start(rng: random.Random) -> date:
    y = rng.choice([2021, 2022, 2023, 2024, 2024, 2025, 2025, 2025, 2026, 2026])
    m = rng.randint(1, 9 if y == 2026 else 12)
    r = rng.random()
    if r < 0.35:
        d = 1
    elif r < 0.45:
        d = 16
    elif r < 0.50:
        d = 31 if m in (1, 3, 5, 7, 8, 10, 12) else 30
    else:
        d = rng.randint(2, 28)
    return date(y, m, d)


def end_column(rng, start, months, as_of):
    """給与ファイル上の「契約終了日」列と反映済更新回数を作る。"""
    cur = current_term(start, months, as_of)
    if cur is None:
        return "", 0
    k, _, e = cur
    r = rng.random()
    stale_rate = 0.40 if months == 3 else 0.10
    if r < 0.15:
        return "", ""
    if r < 0.15 + stale_rate and k >= 2:
        return term_end(start, months, k - 1).isoformat(), k - 2
    return e.isoformat(), k - 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=250)
    ap.add_argument("--seed", type=int, default=20261011)
    ap.add_argument("--as-of", default="2026-10-11")
    ap.add_argument("--out", default="data/staff.csv")
    a = ap.parse_args()
    rng = random.Random(a.seed)
    as_of = date.fromisoformat(a.as_of)
    pairs = [(area, am) for area, ams in AREAS.items() for am in ams]
    rows = []

    def new_row(i, start_s, months, note, override):
        area, am = rng.choice(pairs)
        row = {"職員ID": f"DEMO-{i:04d}",
               "氏名": f"{rng.choice(SURNAMES)} {rng.choice(GIVEN)}（架空{i:03d}）",
               "エリア": area, "エリアマネージャー": am,
               "契約開始日": start_s, "契約期間(月)": str(months),
               "契約終了日": "", "更新回数(反映済)": "", "在籍状態": "在籍", "備考": note}
        try:
            s = date.fromisoformat(start_s)
            if months in (1, 3, 6, 12):
                row["契約終了日"], row["更新回数(反映済)"] = end_column(rng, s, months, as_of)
        except ValueError:
            pass
        row.update(override)
        return row

    i = 1
    for start_s, months, note, ov in EDGE_CASES:
        rows.append(new_row(i, start_s, months, note, ov)); i += 1
    while len(rows) < a.n:
        months = rng.choices([1, 3, 6, 12], weights=[10, 40, 25, 25])[0]
        s = rand_start(rng)
        st = rng.choices(["在籍", "退職予定", "休職中", "退職済"], weights=[92, 5, 2, 1])[0]
        rows.append(new_row(i, s.isoformat(), months, "", {"在籍状態": st})); i += 1
    rng.shuffle(rows)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader(); w.writerows(rows)
    print(f"wrote {len(rows)} rows -> {a.out}")


if __name__ == "__main__":
    main()
