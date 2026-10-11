import csv
import random
from datetime import date, timedelta
from pathlib import Path

import pytest

import renewal as R
from renewal import term_end, term_start, terms_ending_in_month, current_term

D = date.fromisoformat
ROOT = Path(__file__).resolve().parents[1]


# ---------------- 3ヶ月の境界・月末・閏年（civil 既定）
@pytest.mark.parametrize("start,k,expected", [
    ("2025-11-30", 1, "2026-02-28"),   # 応当日2/30なし → 月末
    ("2027-11-30", 1, "2028-02-29"),   # 閏年
    ("2027-11-29", 1, "2028-02-28"),   # 応当日2/29あり → 前日
    ("2025-08-31", 1, "2025-11-30"),   # 11/31なし → 月末
    ("2025-08-31", 2, "2026-02-28"),
    ("2025-08-31", 3, "2026-05-30"),   # 5/31あり → 前日
    ("2027-08-31", 2, "2028-02-29"),   # 閏年
    ("2026-01-01", 1, "2026-03-31"),   # 1日開始 → 前月末
    ("2026-04-01", 1, "2026-06-30"),
    ("2026-12-01", 1, "2027-02-28"),
    ("2027-12-01", 1, "2028-02-29"),
    ("2026-05-31", 1, "2026-08-30"),
    ("2026-08-12", 1, "2026-11-11"),   # 四半期非整合
    ("2026-02-15", 4, "2027-02-14"),
])
def test_three_month_boundaries(start, k, expected):
    assert term_end(D(start), 3, k) == D(expected)


@pytest.mark.parametrize("start,months,k,expected", [
    ("2026-01-31", 1, 1, "2026-02-28"),
    ("2028-01-31", 1, 1, "2028-02-29"),
    ("2026-01-31", 1, 2, "2026-03-30"),
    ("2026-01-31", 1, 3, "2026-04-30"),   # 4/31なし → 月末
    ("2026-03-30", 1, 1, "2026-04-29"),   # 30日開始
    ("2026-04-30", 1, 1, "2026-05-29"),
    ("2026-01-30", 1, 1, "2026-02-28"),
    ("2026-01-15", 1, 1, "2026-02-14"),
    ("2026-07-01", 1, 1, "2026-07-31"),
    ("2026-03-31", 6, 1, "2026-09-30"),
    ("2026-08-31", 6, 1, "2027-02-28"),
    ("2027-08-31", 6, 1, "2028-02-29"),
    ("2026-04-01", 6, 2, "2027-03-31"),
    ("2026-04-01", 12, 1, "2027-03-31"),
    ("2028-02-29", 12, 1, "2029-02-28"),  # 閏日開始 → 応当日なし → 月末
    ("2028-02-29", 12, 4, "2032-02-28"),  # 4年後は2/29が応当日 → 前日
    ("2024-02-29", 12, 1, "2025-02-28"),
    ("2026-10-16", 12, 1, "2027-10-15"),
])
def test_month_end_and_other_lengths(start, months, k, expected):
    assert term_end(D(start), months, k) == D(expected)


def test_conventions_differ_on_month_end():
    s = D("2027-11-30")
    assert term_end(s, 3, 1, "civil") == D("2028-02-29")
    assert term_end(s, 3, 1, "minus1") == D("2028-02-28")
    assert term_end(s, 3, 1, "calendar") == D("2028-01-31")
    s = D("2026-04-01")
    assert {term_end(s, 3, 1, c) for c in R.CONVENTIONS} == {D("2026-06-30")}
    with pytest.raises(ValueError):
        term_end(s, 3, 1, "bogus")


def test_no_drift_anchor_based():
    # 1/31開始1ヶ月: 連鎖計算だと 2/28→3/28→… とずれるが、起算日基準なので3月は3/30
    ends = [term_end(D("2026-01-31"), 1, k) for k in range(1, 13)]
    assert ends[1] == D("2026-03-30")
    assert ends[11] == D("2027-01-30")


# ---------------- 連続性・重複なしの性質テスト
def _sample_starts(n=400, seed=1):
    rng = random.Random(seed)
    base = [D("2025-08-31"), D("2025-11-30"), D("2027-11-30"), D("2024-02-29"), D("2028-02-29"),
            D("2026-01-31"), D("2026-01-01"), D("2026-05-31"), D("2026-03-30")]
    out = list(base)
    while len(out) < n:
        out.append(D("2020-01-01") + timedelta(days=rng.randint(0, 365 * 8)))
    return out


@pytest.mark.parametrize("convention", R.CONVENTIONS)
@pytest.mark.parametrize("months", R.ALLOWED_PERIODS)
def test_terms_are_contiguous(months, convention):
    for s in _sample_starts():
        prev = None
        for k in range(1, 30):
            st, en = term_start(s, months, k, convention), term_end(s, months, k, convention)
            assert st <= en
            if prev is not None:
                assert st == prev + timedelta(days=1)
            prev = en


@pytest.mark.parametrize("convention", ["civil", "minus1"])
@pytest.mark.parametrize("months", R.ALLOWED_PERIODS)
def test_every_cycle_appears_exactly_once_over_24_months(months, convention):
    """24ヶ月間の各月で抽出し、各人が N ヶ月おきに必ず1回だけ現れ、抜けがないこと。"""
    for s in _sample_starts():
        y0, m0 = R.add_months_ym(s.year, s.month, 1)
        hit_months = []
        for i in range(24):
            y, m = R.add_months_ym(y0, m0, i)
            hits = terms_ending_in_month(s, months, y, m, convention)
            assert len(hits) <= 1, (s, y, m, hits)
            if hits:
                hit_months.append((i, hits[0][0]))
        ks = [k for _, k in hit_months]
        assert ks == list(range(ks[0], ks[0] + len(ks))), (s, ks)        # 期の抜けなし
        gaps = {b[0] - a[0] for a, b in zip(hit_months, hit_months[1:])}
        assert gaps <= {months}, (s, gaps)                               # 必ずNヶ月間隔
        assert abs(len(hit_months) - 24 / months) <= 1                   # 期待回数どおり


def test_three_month_every_three_months_strict():
    for s in _sample_starts(seed=3):
        months_hit = []
        y0, m0 = s.year, s.month
        for i in range(1, 25):
            y, m = R.add_months_ym(y0, m0, i)
            if terms_ending_in_month(s, 3, y, m):
                months_hit.append(i)
        assert len(months_hit) == 8, (s, months_hit)
        assert all(b - a == 3 for a, b in zip(months_hit, months_hit[1:]))


def test_current_term_consistency():
    for s in _sample_starts(100):
        for months in R.ALLOWED_PERIODS:
            for off in (0, 1, 27, 59, 200, 731, 1500):
                d = s + timedelta(days=off)
                k, st, en = current_term(s, months, d)
                assert st <= d <= en
                assert st == term_start(s, months, k) and en == term_end(s, months, k)
    assert current_term(D("2026-01-01"), 3, D("2025-12-31")) is None


# ---------------- 抽出ロジック
def _row(i, start, months, end="", status="在籍", am="AM1"):
    return {"職員ID": f"T{i}", "氏名": f"テスト{i}", "エリア": "A", "エリアマネージャー": am,
            "契約開始日": start, "契約期間(月)": str(months), "契約終了日": end, "在籍状態": status}


def test_extract_basic_and_exclusions():
    rows = [
        _row(1, "2025-08-31", 3),                  # 2026-11-30
        _row(2, "2026-08-12", 3),                  # 2026-11-11
        _row(3, "2026-09-01", 3),                  # 2026-11-30
        _row(4, "2025-08-01", 3),                  # 10/31 → 11月対象外
        _row(5, "2025-11-05", 3, status="退職予定"),
        _row(6, "2026-05-20", 3, am=""),           # AM未設定でも対象・フラグ
        _row(7, "2025-02-30", 3),                  # 不正日付
        _row(8, "2025-05-10", 2),                  # 想定外期間
        _row(9, "2026-10-31", 1),                  # 11/30
        _row(10, "2026-08-25", 3, end="2026-12-31"),  # 周期不一致
        _row(11, "2025-11-15", 12, status="退職済"),
        _row(1, "2025-08-31", 3),                  # ID重複
    ]
    res = R.extract(rows, 2026, 11)
    ids = [t.row["職員ID"] for t in res.targets]
    assert sorted(ids) == sorted(["T1", "T2", "T3", "T6", "T9", "T10"])
    assert len(ids) == len(set(ids))
    assert [t.row["職員ID"] for t in res.excluded] == ["T5"]
    kinds = " ".join(i["内容"] for i in res.issues)
    assert "不正" in kinds and "想定外" in kinds and "重複" in kinds and "不一致" in kinds and "空欄" in kinds
    t6 = next(t for t in res.targets if t.row["職員ID"] == "T6")
    assert "AM未設定" in t6.flags


def test_extract_lookahead_one_row_per_person():
    rows = [_row(1, "2026-10-31", 1), _row(2, "2026-09-16", 3)]   # 1ヶ月: 11/30,12/30 ／ 3ヶ月: 12/15
    res = R.extract(rows, 2026, 11, lookahead=1)
    assert len(res.targets) == 2
    t1 = next(t for t in res.targets if t.row["職員ID"] == "T1")
    assert t1.end == D("2026-11-30") and any("2回満了" in f for f in t1.flags)
    assert R.extract(rows, 2026, 11).targets[0].row["職員ID"] == "T1"


def test_stale_end_column_still_extracted_and_flagged():
    # 前回更新が給与ファイル未反映（終了日列=1期前）でも、起算日から計算するので漏れない
    rows = [_row(1, "2025-08-12", 3, end="2026-08-11")]
    res = R.extract(rows, 2026, 11)
    assert res.targets[0].end == D("2026-11-11")
    assert any("未反映" in f for f in res.targets[0].flags)
    assert R.naive_end_column(rows, 2026, 11) == set()   # 旧方式Aでは漏れる


def test_naive_methods_miss_three_month_people():
    rows = [_row(1, "2026-08-12", 3), _row(2, "2025-08-01", 3), _row(3, "2025-12-01", 3)]
    correct = {t.row["職員ID"] for t in R.extract(rows, 2026, 11).targets}
    assert correct == {"T1", "T3"}
    assert R.naive_quarter(rows, 2026, 11) == set()            # 11月は四半期末でない → 全員漏れ
    c = R.naive_start_month(rows, 2026, 11)                    # 開始月だけで判定
    assert "T3" not in c and "T2" in c                         # 1日開始がずれる


def test_mukitenkan_and_notice_flags():
    rows = [_row(1, "2021-12-01", 12), _row(2, "2026-08-12", 3)]
    res = {t.row["職員ID"]: t for t in R.extract(rows, 2026, 11).targets}
    assert res["T1"].mukitenkan and res["T1"].notice_required
    assert res["T1"].notice_deadline == D("2026-10-31")
    assert not res["T2"].mukitenkan and not res["T2"].notice_required


# ---------------- 生成データ全体の健全性
def test_generated_dataset_each_person_once_per_cycle():
    path = ROOT / "data" / "staff.csv"
    if not path.exists():
        pytest.skip("data/staff.csv がありません（generate_staff.py を実行）")
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    assert 240 <= len(rows) <= 260
    counts = {}
    for i in range(24):
        y, m = R.add_months_ym(2026, 1, i)
        res = R.extract(rows, y, m)
        ids = [t.row["職員ID"] for t in res.targets + res.excluded]
        assert len(ids) == len(set(ids))
        for sid in ids:
            counts.setdefault(sid, []).append(i)
    by_id = {r["職員ID"]: r for r in rows}
    for sid, ms in counts.items():
        n = int(by_id[sid]["契約期間(月)"])
        assert all(b - a == n for a, b in zip(ms, ms[1:])), (sid, n, ms)
