"""ホールドアウト（抽出ロジック確定後に作成した未見レイアウト）2件。抽出器はこれを見て調整していない。"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from generate_samples import canvas, A4, W, H, mm, table, to_scan, ROOT

OUT = ROOT / "samples_holdout"; OUT.mkdir(exist_ok=True)

def h1(path):  # 英日混在・ラベル未知・個人事業主（法人格なし）・ゆうちょ
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Gothic", 20); c.drawString(20*mm, H-25*mm, "INVOICE 請求書")
    c.setFont("Gothic", 10)
    c.drawString(20*mm, H-38*mm, "To: 株式会社デモ受取HD 御中")
    c.drawRightString(W-20*mm, H-25*mm, "Issue date: R8.10.02")
    c.drawRightString(W-20*mm, H-31*mm, "ほしぞら架空ラボ（代表 架空 花子）")
    c.drawRightString(W-20*mm, H-37*mm, "Registration No. T2222333344445")
    rows = [["システム保守サポート 月額（10月）", "1", "40,000", "40,000"], ["サーバー監視オプション", "1", "8,000", "8,000"]]
    y = table(c, 20*mm, H-55*mm, [("Item / 品目", 90*mm), ("Qty", 20*mm), ("Unit", 30*mm), ("Amount", 30*mm)], rows)
    c.drawRightString(190*mm, y-8*mm, "Subtotal 48,000"); c.drawRightString(190*mm, y-14*mm, "Tax(10%) 4,800")
    c.setFont("Gothic", 13); c.drawRightString(190*mm, y-22*mm, "Total Amount (tax incl.) JPY 52,800")
    c.setFont("Gothic", 10)
    c.drawString(20*mm, y-36*mm, "支払締切日：R8.11.30")
    c.drawString(20*mm, y-44*mm, "Bank: ゆうちょ銀行 〇一八店 普通 1234567 ホシゾラカクウラボ カクウ ハナコ")
    c.save()
    return dict(invoice_date="2026-10-02", total=52800, vendor="ほしぞら架空ラボ",
                bank=dict(bank="ゆうちょ銀行", branch="〇一八店", type="普通", number="1234567", holder="ホシゾラカクウラボ カクウ ハナコ"),
                due_date="2026-11-30", category="外注費", layout="text")

def h2(path):  # 旅行代理店・口座2つ・曜日付き日付・スキャン
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Mincho", 18); c.drawCentredString(W/2, H-22*mm, "ご 請 求 書")
    c.setFont("Mincho", 11)
    c.drawString(20*mm, H-36*mm, "株式会社デモ受取ホールディングス 総務部 御中")
    c.drawString(125*mm, H-36*mm, "株式会社 れんげ架空トラベル")
    c.drawString(125*mm, H-42*mm, "登録番号 T8888999900001")
    c.drawString(125*mm, H-48*mm, "請求日 2026年10月6日(火)")
    c.rect(20*mm, H-66*mm, 80*mm, 16*mm)
    c.drawString(23*mm, H-57*mm, "お支払い期限"); c.drawString(23*mm, H-63*mm, "2026年10月13日(火)")
    rows = [["新幹線 東京-新大阪 往復 2名", "2", "29,000", "58,000"], ["ビジネスホテル 宿泊 1泊 2名", "2", "11,000", "22,000"]]
    y = table(c, 20*mm, H-78*mm, [("明細", 110*mm), ("数", 15*mm), ("単価", 22*mm), ("金額", 23*mm)], rows, font="Mincho", size=11, rowh=8*mm)
    c.setFont("Mincho", 13); c.drawRightString(190*mm, y-10*mm, "合計 ¥88,000（うち消費税 ¥8,000）")
    c.setFont("Mincho", 10)
    c.drawString(20*mm, y-26*mm, "下記いずれかの口座へお振込みください。")
    c.drawString(20*mm, y-33*mm, "① 架空れんげ銀行 本店営業部 普通 1112223 カ）レンゲカクウトラベル")
    c.drawString(20*mm, y-40*mm, "② 架空あさひ信用金庫 駅前支店 当座 4445556 カ）レンゲカクウトラベル")
    c.save()
    return dict(invoice_date="2026-10-06", total=88000, vendor="株式会社れんげ架空トラベル",
                bank=dict(bank="架空れんげ銀行", branch="本店営業部", type="普通", number="1112223", holder="カ）レンゲカクウトラベル"),
                due_date="2026-10-13", category="旅費交通費", layout="scan")

if __name__ == "__main__":
    tmp = ROOT / "tools" / "_tmp"
    gt = {"HOLD_1_hoshizora_lab.pdf": h1(OUT / "HOLD_1_hoshizora_lab.pdf")}
    gt["HOLD_2_renge_travel_scan.pdf"] = h2(tmp / "h2.pdf"); to_scan(tmp / "h2.pdf", OUT / "HOLD_2_renge_travel_scan.pdf", angle=0.8, seed=3)
    (ROOT / "ground_truth_holdout.json").write_text(json.dumps(gt, ensure_ascii=False, indent=2))
    print("holdout generated", list(gt))
