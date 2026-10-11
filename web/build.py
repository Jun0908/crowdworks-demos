"""Copy the tested engine and generate a clearly labelled sample snapshot."""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "3_契約更新抽出"
DIST = ROOT / "web" / "dist"
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(DIST / "python"))
from browser_bridge import run_request

for name in ("renewal.py", "extract_renewals.py"):
    shutil.copyfile(SOURCE / name, DIST / "python" / name)
shutil.copyfile(SOURCE / "data" / "staff.csv", DIST / "sample.csv")
snapshot = run_request({"csv_text": (DIST / "sample.csv").read_text(encoding="utf-8-sig")})
(DIST / "sample-result.json").write_text(snapshot, encoding="utf-8")
data = json.loads(snapshot)
assert len(data["records"]) == 80 and data["three_count"] == 37
assert len(data["missed_ids"]) == 19 and len(data["issues"]) == 7
print("Sample built: 250 inputs, 80 targets, 37 three-month contracts, 19 recovered, 7 issues")
