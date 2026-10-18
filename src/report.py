"""สร้างรายงานยอดขายรายเดือนเป็น Markdown

ใช้: python -m src.report 2026-03
ผลลัพธ์: reports/monthly_report.md
ทุกตัวเลขคำนวณผ่านฟังก์ชันใน src/metrics.py
"""
import sys
from pathlib import Path

import pandas as pd

from src import metrics as m

REPORTS = Path(__file__).resolve().parent.parent / "reports"


def summarize(df: pd.DataFrame, month: str, n_top: int = 5) -> dict:
    """ตัวเลขสรุปของเดือนที่ระบุ เทียบกับเดือนก่อน"""
    cur = m.orders_in_month(df, month)
    if len(cur) == 0:
        raise ValueError(f"ไม่มีคำสั่งซื้อในเดือน {month}")
    prev_month = m.previous_month(month)
    prev = m.orders_in_month(df, prev_month)

    net = m.net_sales(cur)
    prev_net = m.net_sales(prev) if len(prev) else None
    change_pct = (net - prev_net) / prev_net * 100 if prev_net else None
    return {
        "month": month,
        "orders": len(cur),
        "net_sales": net,
        "prev_month": prev_month,
        "prev_net_sales": prev_net,
        "change_pct": change_pct,
        "top_products": m.top_products(cur, n_top),
        "cancel_rate": m.cancel_rate(cur),
        "return_rate": m.return_rate(cur),
    }


def _baht(x: float) -> str:
    return f"{x:,.0f} บาท"


def to_markdown(s: dict) -> str:
    if s["prev_net_sales"] is None:
        compare = f"ไม่มีข้อมูลเดือน {s['prev_month']}"
    else:
        compare = f"{_baht(s['prev_net_sales'])} ({s['change_pct']:+.1f}%)"

    lines = [
        f"# รายงานยอดขายประจำเดือน {s['month']} · บ้านสบาย ช็อป",
        "",
        "## ภาพรวม",
        "",
        "| ตัวชี้วัด | ค่า |",
        "|---|---:|",
        f"| ยอดขายสุทธิ | {_baht(s['net_sales'])} |",
        f"| เดือนก่อน ({s['prev_month']}) | {compare} |",
        f"| อัตรายกเลิก | {s['cancel_rate']:.2f}% |",
        f"| อัตราคืนสินค้า | {s['return_rate']:.2f}% |",
        f"| คำสั่งซื้อทั้งหมด (ทุกสถานะ) | {s['orders']:,} |",
        "",
        f"## {len(s['top_products'])} สินค้าขายดี (ตามยอดขายสุทธิ)",
        "",
        "| อันดับ | รหัส | สินค้า | จำนวนชิ้น | ยอดขายสุทธิ |",
        "|---:|---|---|---:|---:|",
    ]
    for i, r in enumerate(s["top_products"].itertuples(), start=1):
        lines.append(f"| {i} | {r.product_id} | {r.product_name} | {r.qty:,} | {_baht(r.net)} |")
    lines += [
        "",
        "> ยอดขายสุทธิ = qty × unit_price × (1 − discount_pct/100) เฉพาะสถานะ \"จัดส่งสำเร็จ\" ไม่รวมค่าส่ง",
        "> อัตรายกเลิก/คืน = จำนวนแถวสถานะนั้น ÷ คำสั่งซื้อทั้งหมดของเดือน × 100",
        "",
    ]
    return "\n".join(lines)


def write_report(df: pd.DataFrame, month: str, out_path: Path | str = REPORTS / "monthly_report.md") -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(to_markdown(summarize(df, month)), encoding="utf-8")
    return out_path


def main(argv: list[str]) -> None:
    if len(argv) != 1:
        sys.exit("ใช้: python -m src.report YYYY-MM")
    path = write_report(m.load_orders(), argv[0])
    print(f"เขียนรายงานแล้ว: {path}")


if __name__ == "__main__":
    main(sys.argv[1:])
