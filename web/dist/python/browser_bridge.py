"""Browser adapter for the original renewal engine. No network or persistence."""
import base64
import copy
import csv
import io
import json
import tempfile
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path

import renewal as R
import extract_renewals as E

REQUIRED = [R.COL_ID, R.COL_NAME, R.COL_START, R.COL_PERIOD, R.COL_STATUS]


def safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def run_request(payload):
    month = payload.get("month", "2026-11")
    try:
        year, mon = R.parse_ym(month)
        if not 1900 <= year <= 2100:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError("対象月は1900年1月から2100年12月の範囲で指定してください。")
    lookahead = int(payload.get("lookahead", 0))
    if lookahead not in (0, 1, 2):
        raise ValueError("先読み期間は0〜2ヶ月で指定してください。")
    convention = payload.get("convention", "civil")
    if convention not in R.CONVENTIONS:
        raise ValueError("終了日の計算ルールが不正です。")
    source = payload.get("csv_text", "")
    if not source.strip():
        raise ValueError("CSVにデータがありません。サンプルを読み込むかCSVを選んでください。")
    if len(source.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("CSVは2MB以下にしてください。")
    reader = csv.DictReader(io.StringIO(source.lstrip("\ufeff")), strict=True)
    missing = [name for name in REQUIRED if name not in (reader.fieldnames or [])]
    if missing:
        raise ValueError("CSVに必要な列がありません：" + "、".join(missing))
    rows = []
    for row in reader:
        if None in row or any(v is None for v in row.values()):
            raise ValueError("CSVの列数が一致しません。カンマや引用符を確認してください。")
        if any(len(v) > 1000 for v in row.values()):
            raise ValueError("1セルは1,000文字以下にしてください。")
        rows.append(row)
        if len(rows) > 5000:
            raise ValueError("CSVは5,000行以下にしてください。")
    if not rows:
        raise ValueError("CSVにヘッダーしかありません。職員データを追加してください。")
    result = R.extract(rows, year, mon, lookahead, convention)
    records = [E.target_record(t) for t in result.targets]
    comparison = E.naive_comparison(rows, result)
    old_ids = set()
    for i in range(lookahead + 1):
        y, m = R.add_months_ym(year, mon, i)
        old_ids |= R.naive_end_column(rows, y, m)
    missed_ids = {t.row[R.COL_ID] for t in result.targets if t.months == 3} - old_ids
    am = Counter(r["エリアマネージャー"] for r in records)
    deadline = date(*R.add_months_ym(year, mon, -1), 20)
    label = f"{year}年{mon}月"
    if lookahead:
        label += f"〜{result.end_year}年{result.end_month}月"
    # The original workbook writer also uses row names in its issue sheets.
    safe_result = copy.deepcopy(result)
    for target in safe_result.targets + safe_result.excluded:
        target.row = {k: safe_cell(v) for k, v in target.row.items()}
    safe_result.issues = [{k: safe_cell(v) for k, v in item.items()} for item in result.issues]
    safe_records = [{k: safe_cell(v) for k, v in r.items()} for r in records]
    with tempfile.TemporaryDirectory() as tmp:
        xlsx = Path(tmp) / "renewals.xlsx"
        E.build_xlsx(xlsx, safe_result, safe_records, comparison, deadline, label)
        text_csv = io.StringIO(newline="")
        columns = list(records[0]) if records else [R.COL_ID, R.COL_NAME, "現契約終了日(計算)"]
        writer = csv.DictWriter(text_csv, fieldnames=columns)
        writer.writeheader()
        writer.writerows(safe_records)
        message_paths = E.build_messages(str(Path(tmp) / "messages"), records, deadline, label)
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for path in message_paths:
                z.write(path, Path(path).name)
            if not message_paths:
                z.writestr("対象者なし.txt", "指定期間に更新対象者はいません。")
        files = {
            "xlsx": base64.b64encode(xlsx.read_bytes()).decode(),
            "csv": base64.b64encode(text_csv.getvalue().encode("utf-8-sig")).decode(),
            "zip": base64.b64encode(archive.getvalue()).decode(),
        }
    output = {
        "month": month, "lookahead": lookahead, "convention": convention,
        "period": label, "input_count": len(rows), "records": records,
        "excluded": [E.target_record(t) for t in result.excluded], "issues": result.issues,
        "comparison": comparison, "missed_ids": sorted(missed_ids),
        "three_count": sum(t.months == 3 for t in result.targets),
        "am_counts": dict(sorted(am.items())), "message_count": len(message_paths),
        "deadline": str(deadline), "files": files,
    }
    return json.dumps(output, ensure_ascii=False, default=str)
