"""架空の請求書PDFを生成し、ground_truth.json を書き出す（デモ用・全社名架空）。
基準日: 2026-10-11 (Asia/Tokyo)
"""
import json, random, io
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
import pymupdf as fitz
from PIL import Image, ImageFilter
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "samples"; OUT.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont("Gothic", "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"))
pdfmetrics.registerFont(TTFont("Mincho", "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf"))
W, H = A4
RECIPIENT = "株式会社デモ受取ホールディングス"

def yen(n): return f"{n:,}"

def table(c, x, y, cols, rows, font="Gothic", size=10, rowh=7*mm):
    widths = [w for _, w in cols]
    c.setFont(font, size)
    c.setFillGray(0.88); c.rect(x, y - rowh, sum(widths), rowh, fill=1, stroke=1); c.setFillGray(0)
    cx = x
    for (h, w) in cols:
        c.drawString(cx + 2*mm, y - rowh + 2.2*mm, h); cx += w
    y -= rowh
    for r in rows:
        cx = x
        c.rect(x, y - rowh, sum(widths), rowh)
        for i, v in enumerate(r):
            if i == 0: c.drawString(cx + 2*mm, y - rowh + 2.2*mm, str(v))
            else: c.drawRightString(cx + widths[i] - 2*mm, y - rowh + 2.2*mm, str(v))
            cx += widths[i]
        y -= rowh
    return y

# ---------- A: 通信費 / 期日まで4日 / 標準レイアウト ----------
def inv_a(path):
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Gothic", 22); c.drawCentredString(W/2, H-25*mm, "請 求 書")
    c.setFont("Gothic", 10)
    c.drawRightString(W-20*mm, H-35*mm, "請求日：2026年10月1日")
    c.drawRightString(W-20*mm, H-41*mm, "請求書番号：INV-2026-1001")
    c.setFont("Gothic", 13); c.drawString(20*mm, H-50*mm, f"{RECIPIENT} 御中")
    c.setFont("Gothic", 10)
    for i, t in enumerate(["株式会社つばめ架空通信", "〒100-0000 東京都架空区見本町1-2-3", "TEL 03-0000-0000", "登録番号：T1234567890123"]):
        c.drawString(125*mm, H-60*mm - i*5.5*mm, t)
    c.drawString(20*mm, H-65*mm, "下記のとおりご請求申し上げます。")
    c.setFont("Gothic", 14); c.drawString(20*mm, H-80*mm, "ご請求金額（税込）　¥37,620-")
    c.setFont("Gothic", 10); c.drawString(20*mm, H-88*mm, "お支払期限：2026年10月15日")
    rows = [["光回線インターネット利用料（9月分）", "1", "22,000", "22,000"],
            ["固定IP オプション", "1", "3,200", "3,200"],
            ["クラウドPBX 電話回線 5ID", "5", "1,800", "9,000"]]
    y = table(c, 20*mm, H-100*mm, [("品目", 90*mm), ("数量", 20*mm), ("単価", 30*mm), ("金額", 30*mm)], rows)
    sub = 34200; tax = 3420
    c.drawRightString(190*mm, y-8*mm, f"小計　{yen(sub)}")
    c.drawRightString(190*mm, y-14*mm, f"消費税（10%）　{yen(tax)}")
    c.drawRightString(190*mm, y-20*mm, f"合計　{yen(sub+tax)}")
    c.drawString(20*mm, y-35*mm, "【お振込先】")
    c.drawString(20*mm, y-41*mm, "架空みなと銀行 さくら通支店 普通 1234567 カ）ツバメカクウツウシン")
    c.drawString(20*mm, y-50*mm, "※振込手数料は貴社にてご負担をお願いいたします。")
    c.save()
    return dict(invoice_date="2026-10-01", total=37620, vendor="株式会社つばめ架空通信",
                bank=dict(bank="架空みなと銀行", branch="さくら通支店", type="普通", number="1234567", holder="カ）ツバメカクウツウシン"),
                due_date="2026-10-15", category="通信費", layout="text")

# ---------- B: 広告宣伝費 / 2026/10/31 / 右上発行者、スラッシュ日付、口座が表形式 ----------
def inv_b(path):
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Mincho", 11)
    c.drawString(20*mm, H-20*mm, f"{RECIPIENT}")
    c.drawString(20*mm, H-26*mm, "経理ご担当者様")
    c.setFont("Mincho", 20); c.drawString(20*mm, H-42*mm, "INVOICE ／ ご請求書")
    c.setFont("Mincho", 10)
    x = 130*mm
    for i, t in enumerate(["発行日 2026/10/05", "No. B-77812", "", "合同会社ひまわり架空広告", "大阪府見本市架空町4-5-6", "適格請求書発行事業者 T9876543210987"]):
        c.drawString(x, H-20*mm - i*5.5*mm, t)
    c.setFont("Mincho", 12)
    c.drawString(20*mm, H-60*mm, "合計金額　　110,000 円（税込）")
    c.drawString(20*mm, H-67*mm, "お支払期日　2026/10/31")
    rows = [["SNS広告運用代行（10月）", "1式", "70,000", "70,000"],
            ["リスティング広告 出稿費 立替分", "1式", "30,000", "30,000"]]
    y = table(c, 20*mm, H-80*mm, [("摘要", 95*mm), ("数量", 20*mm), ("単価", 27*mm), ("金額", 28*mm)], rows, font="Mincho")
    c.drawRightString(190*mm, y-8*mm, "税抜金額 100,000")
    c.drawRightString(190*mm, y-14*mm, "消費税等(10%) 10,000")
    c.drawRightString(190*mm, y-20*mm, "税込合計 110,000")
    y2 = y - 35*mm
    c.drawString(20*mm, y2, "お振込先口座")
    rows2 = [["金融機関", "ひかり架空信用金庫"], ["支店名", "梅田支店"], ["口座種別", "当座"], ["口座番号", "0076543"], ["口座名義", "ゴウ）ヒマワリカクウコウコク"]]
    for i, (k, v) in enumerate(rows2):
        c.rect(20*mm, y2 - (i+1)*7*mm - 2*mm, 30*mm, 7*mm); c.rect(50*mm, y2 - (i+1)*7*mm - 2*mm, 80*mm, 7*mm)
        c.drawString(22*mm, y2 - (i+1)*7*mm + 0.2*mm, k); c.drawString(52*mm, y2 - (i+1)*7*mm + 0.2*mm, v)
    c.save()
    return dict(invoice_date="2026-10-05", total=110000, vendor="合同会社ひまわり架空広告",
                bank=dict(bank="ひかり架空信用金庫", branch="梅田支店", type="当座", number="0076543", holder="ゴウ）ヒマワリカクウコウコク"),
                due_date="2026-10-31", category="広告宣伝費", layout="text")

# ---------- C: 外注費・個人事業主・源泉徴収あり / 令和 / 期限切れ（スキャン） ----------
def inv_c(path):
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Gothic", 20); c.drawString(20*mm, H-25*mm, "請求書")
    c.setFont("Gothic", 11)
    c.drawString(20*mm, H-38*mm, f"{RECIPIENT} 御中")
    c.drawRightString(W-20*mm, H-25*mm, "令和8年9月30日")
    for i, t in enumerate(["あおい架空デザイン事務所", "代表 架空 太郎", "東京都見本区デモ2-8-1", "登録番号 T5555666677778"]):
        c.drawString(130*mm, H-38*mm - i*6*mm, t)
    c.setFont("Gothic", 14); c.drawString(20*mm, H-70*mm, "ご請求額 ￥199,580")
    c.setFont("Gothic", 11); c.drawString(20*mm, H-78*mm, "振込期限 令和8年10月10日")
    rows = [["Webサイト デザイン制作業務委託", "1", "150,000", "150,000"],
            ["バナー画像制作", "4", "12,500", "50,000"]]
    y = table(c, 20*mm, H-90*mm, [("内容", 90*mm), ("数量", 20*mm), ("単価", 30*mm), ("金額", 30*mm)], rows, size=11, rowh=8*mm)
    c.drawRightString(190*mm, y-8*mm, "小計 200,000")
    c.drawRightString(190*mm, y-15*mm, "消費税 20,000")
    c.drawRightString(190*mm, y-22*mm, "源泉徴収税額 -20,420")
    c.drawRightString(190*mm, y-29*mm, "差引ご請求額 199,580")
    c.drawString(20*mm, y-45*mm, "振込先: 架空ゆめ銀行 デモ支店 普通預金 7654321 アオイカクウデザイン カクウ タロウ")
    c.save()
    # 源泉: 200,000 * 10.21% = 20,420 → 200,000 + 20,000 - 20,420 = 199,580
    return dict(invoice_date="2026-09-30", total=199580, vendor="あおい架空デザイン事務所",
                bank=dict(bank="架空ゆめ銀行", branch="デモ支店", type="普通", number="7654321", holder="アオイカクウデザイン カクウ タロウ"),
                due_date="2026-10-10", category="外注費", layout="scan")

# ---------- D: 地代家賃 / ハイフン日付 + 支払期日は和文 / スキャン（傾き大きめ） ----------
def inv_d(path):
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Mincho", 18); c.drawCentredString(W/2, H-22*mm, "御 請 求 書")
    c.setFont("Mincho", 11)
    c.drawString(20*mm, H-36*mm, f"{RECIPIENT} 様")
    c.drawString(20*mm, H-44*mm, "発行日 2026-09-25")
    for i, t in enumerate(["株式会社かもめ架空不動産", "神奈川県例示市サンプル1-1", "登録番号 T3333444455556"]):
        c.drawString(125*mm, H-36*mm - i*6*mm, t)
    c.drawString(20*mm, H-60*mm, "2026年11月分 事務所賃料等を下記のとおりご請求いたします。")
    rows = [["事務所 賃料（11月分）", "180,000"], ["共益費（11月分）", "20,000"], ["駐車場使用料（11月分）", "15,000"]]
    y = table(c, 20*mm, H-70*mm, [("項目", 120*mm), ("金額", 50*mm)], rows, font="Mincho", size=11, rowh=8*mm)
    c.drawRightString(190*mm, y-8*mm, "小計 215,000")
    c.drawRightString(190*mm, y-15*mm, "消費税(10%) 21,500")
    c.setFont("Mincho", 13); c.drawRightString(190*mm, y-24*mm, "合計金額 236,500円")
    c.setFont("Mincho", 11)
    c.drawString(20*mm, y-40*mm, "支払期日　2026年10月16日")
    c.drawString(20*mm, y-48*mm, "お振込先　架空はまなす銀行　横浜西支店　普通　3141592")
    c.drawString(20*mm, y-55*mm, "口座名義　カ）カモメカクウフドウサン")
    c.save()
    return dict(invoice_date="2026-09-25", total=236500, vendor="株式会社かもめ架空不動産",
                bank=dict(bank="架空はまなす銀行", branch="横浜西支店", type="普通", number="3141592", holder="カ）カモメカクウフドウサン"),
                due_date="2026-10-16", category="地代家賃", layout="scan")

# ---------- E: 消耗品費 / ドット日付 / 期日が文中「…までに」 ----------
def inv_e(path):
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Gothic", 9); c.drawString(20*mm, H-15*mm, "2026.10.08 発行")
    c.setFont("Gothic", 12); c.drawString(20*mm, H-28*mm, "有限会社こばと架空文具")
    c.setFont("Gothic", 9); c.drawString(20*mm, H-33*mm, "福岡県例市見本3-3-3 / 登録番号 T7777888899990")
    c.setFont("Gothic", 18); c.drawString(20*mm, H-50*mm, "請求書")
    c.setFont("Gothic", 11); c.drawString(20*mm, H-60*mm, f"お客様：{RECIPIENT} 様")
    rows = [["コピー用紙 A4 5000枚", "4", "3,600", "14,400"],
            ["トナーカートリッジ 黒", "2", "8,900", "17,800"],
            ["ボールペン・付箋 文房具セット", "10", "450", "4,500"]]
    y = table(c, 20*mm, H-72*mm, [("品名", 90*mm), ("数量", 20*mm), ("単価", 30*mm), ("金額", 30*mm)], rows)
    c.drawRightString(190*mm, y-8*mm, "小計 36,700")
    c.drawRightString(190*mm, y-14*mm, "消費税 3,670")
    c.setFont("Gothic", 13); c.drawRightString(190*mm, y-22*mm, "お支払総額 40,370円")
    c.setFont("Gothic", 10)
    c.drawString(20*mm, y-38*mm, "上記金額を 2026年11月20日 までに下記口座へお振込みください。")
    c.drawString(20*mm, y-45*mm, "架空ふくおか銀行　天神中央支店　普通　2718281　ユ）コバトカクウブング")
    c.save()
    return dict(invoice_date="2026-10-08", total=40370, vendor="有限会社こばと架空文具",
                bank=dict(bank="架空ふくおか銀行", branch="天神中央支店", type="普通", number="2718281", holder="ユ）コバトカクウブング"),
                due_date="2026-11-20", category="消耗品費", layout="text")

def to_scan(src, dst, angle, seed, dpi=150, blur=0.6, noise=10, quality=60):
    rng = np.random.default_rng(seed)
    doc = fitz.open(src)
    pix = doc[0].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
    img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    img = img.rotate(angle, resample=Image.BICUBIC, expand=False, fillcolor=255)
    a = np.asarray(img).astype(np.float32)
    a = a * 0.92 + 12 + rng.normal(0, noise, a.shape)           # 地色のくすみ + ノイズ
    a[rng.random(a.shape) < 0.002] = 0                            # ごま塩ノイズ
    img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur))
    buf = io.BytesIO(); img.save(buf, "JPEG", quality=quality)
    out = fitz.open(); page = out.new_page(width=pix.width * 72 / dpi, height=pix.height * 72 / dpi)
    page.insert_image(page.rect, stream=buf.getvalue()); out.save(dst)

if __name__ == "__main__":
    gt = {}
    tmp = ROOT / "tools" / "_tmp"; tmp.mkdir(exist_ok=True)
    gt["INV_A_tsubame_tsushin.pdf"] = inv_a(OUT / "INV_A_tsubame_tsushin.pdf")
    gt["INV_B_himawari_kokoku.pdf"] = inv_b(OUT / "INV_B_himawari_kokoku.pdf")
    gt["INV_C_aoi_design_scan.pdf"] = inv_c(tmp / "c.pdf"); to_scan(tmp / "c.pdf", OUT / "INV_C_aoi_design_scan.pdf", angle=1.2, seed=1)
    inv_d(tmp / "d.pdf"); to_scan(tmp / "d.pdf", OUT / "INV_D_kamome_fudosan_scan.pdf", angle=-2.0, seed=2, blur=0.8, noise=14, quality=50)
    gt["INV_D_kamome_fudosan_scan.pdf"] = inv_d(tmp / "d.pdf")
    gt["INV_E_kobato_bungu.pdf"] = inv_e(OUT / "INV_E_kobato_bungu.pdf")
    (ROOT / "ground_truth.json").write_text(json.dumps(gt, ensure_ascii=False, indent=2))
    print("generated", list(gt))
