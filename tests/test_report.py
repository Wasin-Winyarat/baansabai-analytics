"""รายงานรายเดือนต้องใช้ตัวเลขเดียวกับ metrics.py"""
import pytest

from src import metrics as m
from src import report


@pytest.fixture(scope="module")
def df():
    return m.load_orders()


def test_report_march_net_sales(df):
    s = report.summarize(df, "2026-03")
    assert s["net_sales"] == pytest.approx(1_147_155, abs=1)
    assert s["prev_month"] == "2026-02"
    assert len(s["top_products"]) == 5
    assert s["top_products"]["net"].is_monotonic_decreasing


def test_report_markdown_file(df, tmp_path):
    path = report.write_report(df, "2026-03", tmp_path / "monthly_report.md")
    text = path.read_text(encoding="utf-8")
    assert "1,147,155 บาท" in text
    assert "อัตรายกเลิก" in text and "อัตราคืนสินค้า" in text


def test_report_sample_not_hardcoded():
    sample = m.load_orders(m.DATA / "orders_sample_80.csv")
    month = sample["month"].iloc[0]
    s = report.summarize(sample, month)
    assert s["net_sales"] == pytest.approx(m.net_sales(m.orders_in_month(sample, month)))
