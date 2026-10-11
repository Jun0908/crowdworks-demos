"""契約更新対象者抽出のコアロジック（デモ用・架空データ前提）

用語
- 起算日 (anchor): 当初の契約開始日。更新は毎回同じ期間 N ヶ月で自動更新される前提。
- 第k期 (k>=1): 起算日から数えて k 回目の契約期間。第1期 = 当初契約。
- 各期の終了日は「起算日 + k*N ヶ月」から直接計算する（前期の終了日から連鎖計算しない）。
  連鎖計算すると月末の切り詰め（1/31 → 2/28 → 3/28 …）が累積して日付がずれるため。

終了日の規約 (convention)
- "civil"  (既定): 民法143条型。応当日の前日に満了。応当日が存在しない月（2/30 等）は
           その月の末日に満了。1日起算は前月末日満了（= 応当日の前日と同じ結果）。
           例: 11/30 開始 3ヶ月 → 2/28（閏年は 2/29）、1/31 開始 1ヶ月 → 2/28
- "minus1": 単純に「開始日 + Nヶ月 − 1日」(relativedelta は月末で切り詰め)。
           例: 11/30 開始 3ヶ月 → 2/27（2/28 − 1日）
- "calendar": 月末締め。開始月を1ヶ月目と数え、N*kヶ月目の末日に満了。
           例: 9/15 開始 3ヶ月 → 11/30
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta

CONVENTIONS = ("civil", "minus1", "calendar")
ALLOWED_PERIODS = (1, 3, 6, 12)
ONE_DAY = timedelta(days=1)


# ---------------------------------------------------------------- 日付計算
def term_end(anchor: date, months: int, k: int, convention: str = "civil") -> date:
    """第k期（1始まり）の契約終了日。"""
    if k < 1:
        raise ValueError("k must be >= 1")
    if months < 1:
        raise ValueError("months must be >= 1")
    if convention not in CONVENTIONS:
        raise ValueError(f"unknown convention: {convention}")
    total = months * k
    if convention == "calendar":
        first = date(anchor.year, anchor.month, 1) + relativedelta(months=total)
        return first - ONE_DAY
    target = anchor + relativedelta(months=total)  # 存在しない日は月末に切り詰め
    if convention == "minus1":
        return target - ONE_DAY
    # civil
    if anchor.day != 1 and target.day != anchor.day:
        return target  # 応当日なし → その月の末日に満了
    return target - ONE_DAY


def term_start(anchor: date, months: int, k: int, convention: str = "civil") -> date:
    if k == 1:
        return anchor
    return term_end(anchor, months, k - 1, convention) + ONE_DAY


def _month_index(d: date) -> int:
    return d.year * 12 + d.month - 1


def terms_ending_in_month(anchor: date, months: int, year: int, month: int,
                          convention: str = "civil") -> list[tuple[int, date]]:
    """指定年月に終了する (k, 終了日) のリスト。通常 0 件か 1 件。"""
    diff = (year * 12 + month - 1) - _month_index(anchor)
    if diff < 0:
        return []
    k0 = diff // months
    out = []
    for k in range(max(1, k0 - 1), k0 + 3):
        e = term_end(anchor, months, k, convention)
        if e.year == year and e.month == month:
            out.append((k, e))
    return out


def current_term(anchor: date, months: int, on: date, convention: str = "civil") -> tuple[int, date, date] | None:
    """指定日を含む期 (k, 開始日, 終了日)。起算日前なら None。"""
    if on < anchor:
        return None
    k = max(1, (_month_index(on) - _month_index(anchor)) // months - 1)
    while True:
        e = term_end(anchor, months, k, convention)
        if on <= e:
            s = term_start(anchor, months, k, convention)
            if on >= s:
                return k, s, e
            k -= 1
        else:
            k += 1


def is_term_end(anchor: date, months: int, d: date, convention: str = "civil") -> int | None:
    """d がいずれかの期の終了日なら k を返す。"""
    hits = terms_ending_in_month(anchor, months, d.year, d.month, convention)
    for k, e in hits:
        if e == d:
            return k
    return None


def month_last_day(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def parse_ym(s: str) -> tuple[int, int]:
    dt = datetime.strptime(s.strip(), "%Y-%m")
    return dt.year, dt.month


def add_months_ym(year: int, month: int, n: int) -> tuple[int, int]:
    i = year * 12 + month - 1 + n
    return i // 12, i % 12 + 1


def parse_date(s) -> date | None:
    """厳密な日付パース。空欄は None、不正値は ValueError。"""
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"日付として解釈できません: {s!r}")


# ---------------------------------------------------------------- 抽出
COL_ID, COL_NAME, COL_AREA, COL_AM = "職員ID", "氏名", "エリア", "エリアマネージャー"
COL_START, COL_PERIOD, COL_END, COL_STATUS = "契約開始日", "契約期間(月)", "契約終了日", "在籍状態"
STATUS_RETIRING = "退職予定"
STATUS_RETIRED = "退職済"
AM_MISSING_LABEL = "（AM未設定・要確認）"


@dataclass
class Target:
    row: dict
    k: int
    start: date
    end: date
    anchor: date
    months: int
    flags: list[str] = field(default_factory=list)

    @property
    def renewals_so_far(self) -> int:
        return self.k - 1

    @property
    def notice_required(self) -> bool:
        """雇止め予告（30日前）の対象目安: 更新3回以上 or 通算1年超（厚労省告示の基準）。"""
        return self.renewals_so_far >= 3 or (self.end - self.anchor).days >= 365

    @property
    def notice_deadline(self) -> date:
        return self.end - timedelta(days=30)

    @property
    def mukitenkan(self) -> bool:
        """次期を含め通算5年超となる見込み（無期転換申込権の目安。クーリング等は未考慮）。"""
        next_end = self.end + relativedelta(months=self.months)
        return next_end > self.anchor + relativedelta(years=5) - ONE_DAY


@dataclass
class ExtractResult:
    year: int
    month: int
    end_year: int
    end_month: int
    convention: str
    targets: list[Target]
    excluded: list[Target]       # 退職予定で除外
    issues: list[dict]           # 計算不能・要確認データ


def _issue(row, kind, detail):
    return {COL_ID: row.get(COL_ID, ""), COL_NAME: row.get(COL_NAME, ""),
            COL_AREA: row.get(COL_AREA, ""), COL_AM: row.get(COL_AM, ""),
            "区分": kind, "内容": detail}


def extract(rows: list[dict], year: int, month: int, lookahead: int = 0,
            convention: str = "civil") -> ExtractResult:
    """対象月 (year, month) から lookahead ヶ月先の月末までに期間満了する職員を抽出。

    1人につき1行（期間内に複数回満了する1ヶ月契約者は最も早い満了日で1行、
    フラグ「期間内に複数回満了」を付与）。
    """
    months_list = [add_months_ym(year, month, i) for i in range(lookahead + 1)]
    targets, excluded, issues = [], [], []
    seen_ids = set()
    for row in rows:
        sid = (row.get(COL_ID) or "").strip()
        if not sid:
            issues.append(_issue(row, "エラー", "職員IDが空欄"))
            continue
        if sid in seen_ids:
            issues.append(_issue(row, "エラー", "職員IDが重複（2行目以降を無視）"))
            continue
        seen_ids.add(sid)
        status = (row.get(COL_STATUS) or "").strip()
        if status == STATUS_RETIRED:
            continue
        try:
            anchor = parse_date(row.get(COL_START))
        except ValueError as e:
            issues.append(_issue(row, "エラー", f"契約開始日が不正: {e}"))
            continue
        if anchor is None:
            issues.append(_issue(row, "エラー", "契約開始日が空欄"))
            continue
        try:
            months = int(str(row.get(COL_PERIOD, "")).strip())
        except ValueError:
            issues.append(_issue(row, "エラー", f"契約期間が不正: {row.get(COL_PERIOD)!r}"))
            continue
        if months not in ALLOWED_PERIODS:
            issues.append(_issue(row, "エラー", f"想定外の契約期間: {months}ヶ月"))
            continue
        flags = []
        try:
            stated_end = parse_date(row.get(COL_END))
        except ValueError as e:
            stated_end = None
            issues.append(_issue(row, "警告", f"契約終了日列が不正（計算値で続行）: {e}"))
            flags.append("終了日列不正")
        if stated_end is not None and is_term_end(anchor, months, stated_end, convention) is None:
            issues.append(_issue(row, "警告",
                                 f"契約終了日列 {stated_end} が更新周期と不一致（期間変更の可能性・要確認）"))
            flags.append("終了日列が周期と不一致")
        hits = []
        for (y, m) in months_list:
            hits.extend(terms_ending_in_month(anchor, months, y, m, convention))
        if not hits:
            continue
        k, end = min(hits, key=lambda t: t[1])
        if len(hits) > 1:
            flags.append(f"期間内に{len(hits)}回満了")
        am = (row.get(COL_AM) or "").strip()
        if not am:
            flags.append("AM未設定")
            issues.append(_issue(row, "警告", "エリアマネージャーが空欄（要確認シートに振分け）"))
        if stated_end is not None and stated_end < term_start(anchor, months, k, convention):
            flags.append("終了日列が未反映（前期以前の値）")
        t = Target(row=row, k=k, start=term_start(anchor, months, k, convention), end=end,
                   anchor=anchor, months=months, flags=flags)
        if status == STATUS_RETIRING:
            excluded.append(t)
        else:
            if status and status not in ("在籍", "休職中"):
                t.flags.append(f"在籍状態不明:{status}")
            if status == "休職中":
                t.flags.append("休職中")
            targets.append(t)
    targets.sort(key=lambda t: ((t.row.get(COL_AM) or "~"), t.end, t.row[COL_ID]))
    ey, em = months_list[-1]
    return ExtractResult(year, month, ey, em, convention, targets, excluded, issues)


# ---------------------------------------------------------------- 旧方式（比較用）
def naive_end_column(rows, year, month):
    """旧方式A: 給与ファイルの「契約終了日」列をそのまま見る（更新の反映遅れ・空欄に弱い）。"""
    out = set()
    for r in rows:
        if (r.get(COL_STATUS) or "") in (STATUS_RETIRING, STATUS_RETIRED):
            continue
        try:
            d = parse_date(r.get(COL_END))
        except ValueError:
            continue
        if d and d.year == year and d.month == month:
            out.add(r[COL_ID])
    return out


def naive_quarter(rows, year, month):
    """旧方式B: 3ヶ月契約は四半期末（3/6/9/12月）に一斉満了する前提で抽出（3ヶ月契約者のみ判定）。"""
    out = set()
    if month not in (3, 6, 9, 12):
        return out
    for r in rows:
        if str(r.get(COL_PERIOD, "")).strip() == "3" and (r.get(COL_STATUS) or "") not in (STATUS_RETIRING, STATUS_RETIRED):
            out.add(r[COL_ID])
    return out


def naive_start_month(rows, year, month):
    """旧方式C: 開始「月」だけを見て (対象月 − 開始月) が N の倍数なら対象とする（日を無視）。
    1日開始（前月末満了）や月末開始の人がずれる。"""
    out = set()
    for r in rows:
        if (r.get(COL_STATUS) or "") in (STATUS_RETIRING, STATUS_RETIRED):
            continue
        try:
            s = parse_date(r.get(COL_START))
            n = int(r.get(COL_PERIOD))
        except (ValueError, TypeError):
            continue
        if s is None or n <= 0:
            continue
        diff = (year * 12 + month) - (s.year * 12 + s.month)
        if diff > 0 and diff % n == 0:
            out.add(r[COL_ID])
    return out
