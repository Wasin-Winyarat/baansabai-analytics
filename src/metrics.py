"""ฟังก์ชันคำนวณตัวชี้วัดของบ้านสบาย ช็อป

ทุกฟังก์ชันรับ DataFrame ที่ได้จาก load_orders() เป็นพารามิเตอร์แรก
นิยามตัวชี้วัดอยู่ใน CLAUDE.md
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

DELIVERED = "จัดส่งสำเร็จ"
CANCELLED = "ยกเลิก"
RETURNED = "คืนสินค้า"


def load_orders(path: Path | str = DATA / "orders.csv") -> pd.DataFrame:
    """อ่าน orders.csv แล้วเพิ่มคอลัมน์ที่ใช้บ่อย: net, unit_cost, gp, month, date"""
    df = pd.read_csv(path, encoding="utf-8-sig")
    products = pd.read_csv(DATA / "products.csv", encoding="utf-8-sig")
    df = df.merge(products[["product_id", "unit_cost"]], on="product_id", how="left")

    # net และ gp นับเฉพาะแถวที่จัดส่งสำเร็จ แถวอื่นเป็น 0
    delivered = df["status"] == DELIVERED
    gross = df["qty"] * df["unit_price"] * (1 - df["discount_pct"] / 100)
    df["net"] = gross.where(delivered, 0.0)
    df["gp"] = (gross - df["qty"] * df["unit_cost"]).where(delivered, 0.0)
    df["month"] = df["order_datetime"].str[:7]
    df["date"] = df["order_datetime"].str[:10]
    return df


def _delivered(df: pd.DataFrame) -> pd.DataFrame:
    return df[df["status"] == DELIVERED]


def _net(df: pd.DataFrame) -> pd.Series:
    """ยอดขายสุทธิรายแถว (คำนวณจากคอลัมน์ดิบ ไม่พึ่งคอลัมน์ net)"""
    ok = _delivered(df)
    return ok["qty"] * ok["unit_price"] * (1 - ok["discount_pct"] / 100)


def _rate(df: pd.DataFrame, status: str) -> float:
    if len(df) == 0:
        return float("nan")
    return (df["status"] == status).sum() / len(df) * 100


def _between_dates(df: pd.DataFrame, start_date: str | None, end_date: str | None) -> pd.DataFrame:
    date = df["order_datetime"].str[:10]
    mask = pd.Series(True, index=df.index)
    if start_date is not None:
        mask &= date >= start_date
    if end_date is not None:
        mask &= date <= end_date
    return df[mask]


def orders_in_month(df: pd.DataFrame, month: str) -> pd.DataFrame:
    """คำสั่งซื้อทุกสถานะในเดือนที่ระบุ ('YYYY-MM')"""
    return df[df["order_datetime"].str[:7] == month]


def previous_month(month: str) -> str:
    """เดือนก่อนหน้าของ 'YYYY-MM'"""
    return str(pd.Period(month, freq="M") - 1)


def net_sales(df: pd.DataFrame) -> float:
    """ยอดขายสุทธิรวม (บาท)"""
    return float(_net(df).sum())


def gross_profit(df: pd.DataFrame) -> float:
    """กำไรขั้นต้นรวม (บาท)"""
    ok = _delivered(df)
    if "unit_cost" in ok.columns:
        cost = ok["unit_cost"]
    else:
        products = pd.read_csv(DATA / "products.csv", encoding="utf-8-sig")
        cost = ok["product_id"].map(products.set_index("product_id")["unit_cost"])
    return float(_net(df).sum() - (ok["qty"] * cost).sum())


def aov(df: pd.DataFrame) -> float:
    """ยอดขายสุทธิเฉลี่ยต่อคำสั่งซื้อที่จัดส่งสำเร็จ (บาท)"""
    ok = _delivered(df)
    return net_sales(df) / ok["order_id"].nunique()


def cancel_rate(df: pd.DataFrame) -> float:
    """อัตรายกเลิกของคำสั่งซื้อทั้งหมดใน df (เปอร์เซ็นต์ 0–100)"""
    return float(_rate(df, CANCELLED))


def monthly_sales(df: pd.DataFrame) -> pd.Series:
    """ยอดขายสุทธิรายเดือน index = 'YYYY-MM' เรียงตามเวลา"""
    ok = _delivered(df)
    return _net(df).groupby(ok["order_datetime"].str[:7]).sum().sort_index()


def best_month(df: pd.DataFrame) -> str:
    """เดือนที่ยอดขายสุทธิสูงสุด ('YYYY-MM')"""
    return str(monthly_sales(df).idxmax())


def channel_share(df: pd.DataFrame, channel: str, start_month: str, end_month: str) -> float:
    """สัดส่วนยอดขายสุทธิของช่องทางในช่วงเดือน start_month..end_month (รวมทั้งสองเดือน) เป็นเปอร์เซ็นต์"""
    month = df["order_datetime"].str[:7]
    period = df[(month >= start_month) & (month <= end_month)]
    total = net_sales(period)
    return net_sales(period[period["channel"] == channel]) / total * 100


def rating_by_ship_bucket(df: pd.DataFrame) -> dict[str, float]:
    """คะแนนรีวิวเฉลี่ยตามระยะส่ง คืน dict คีย์ '1-2', '3-4', '5-6', '7+'"""
    rated = df.dropna(subset=["rating", "ship_days"])
    buckets = pd.cut(rated["ship_days"], bins=[0, 2, 4, 6, float("inf")],
                     labels=["1-2", "3-4", "5-6", "7+"])
    means = rated["rating"].groupby(buckets, observed=False).mean()
    return {str(k): float(v) for k, v in means.items()}


def top_products(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """สินค้าขายดีตามยอดขายสุทธิ n อันดับแรก คอลัมน์ product_id, product_name, qty, net"""
    ok = _delivered(df)
    sales = ok[["product_id", "product_name", "qty"]].assign(net=_net(df))
    top = (sales.groupby(["product_id", "product_name"], as_index=False)[["qty", "net"]].sum()
           .sort_values("net", ascending=False).head(n))
    return top.reset_index(drop=True)


def top_province(df: pd.DataFrame, region: str) -> str:
    """จังหวัดที่มียอดขายสุทธิสูงสุดในภูมิภาคที่ระบุ"""
    sub = df[df["region"] == region]
    ok = _delivered(sub)
    return str(_net(sub).groupby(ok["province"]).sum().idxmax())


def avg_ship_days(df: pd.DataFrame, region: str | None = None, carrier: str | None = None,
                  start_date: str | None = None, end_date: str | None = None) -> float:
    """ระยะส่งเฉลี่ย (วัน) ตามตัวกรองที่ให้มา วันที่เป็น 'YYYY-MM-DD' และรวมทั้งสองวัน"""
    sub = _between_dates(df, start_date, end_date)
    if region is not None:
        sub = sub[sub["region"] == region]
    if carrier is not None:
        sub = sub[sub["carrier"] == carrier]
    return float(sub["ship_days"].dropna().mean())


def return_rate(df: pd.DataFrame, product_id: str | None = None,
                start_date: str | None = None, end_date: str | None = None) -> float:
    """อัตราคืนสินค้า (เปอร์เซ็นต์) ของสินค้าและช่วงวันที่ที่ระบุ"""
    sub = _between_dates(df, start_date, end_date)
    if product_id is not None:
        sub = sub[sub["product_id"] == product_id]
    return float(_rate(sub, RETURNED))
