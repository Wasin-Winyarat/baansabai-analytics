"""เทียบผลจัดหมวดตั๋วกับ gold set: accuracy, confusion matrix, ตัวอย่างแถวที่ผิด"""
import sys

import pandas as pd

GOLD = "../data/tickets_dev_gold.csv"
PRED = "tickets_classified.csv"
TICKETS = "../data/tickets.csv"
FIELDS = ["category", "sentiment", "urgency"]

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 20)
pd.set_option("display.max_colwidth", 90)
pd.set_option("display.unicode.east_asian_width", True)


def main(gold_path=GOLD, pred_path=PRED, tickets_path=TICKETS, n_errors=10):
    n_errors = int(n_errors)
    gold = pd.read_csv(gold_path, encoding="utf-8-sig")
    pred = pd.read_csv(pred_path, encoding="utf-8-sig")
    msgs = pd.read_csv(tickets_path, encoding="utf-8-sig")[["ticket_id", "message"]]

    df = gold[["ticket_id"] + FIELDS].merge(
        pred[["ticket_id"] + FIELDS], on="ticket_id", how="left", suffixes=("_gold", "_pred")
    )
    missing = df[f"{FIELDS[0]}_pred"].isna().sum()
    print(f"gold rows: {len(gold)} | matched in pred: {len(df) - missing} | missing: {missing}\n")

    print("== Accuracy ==")
    for f in FIELDS:
        correct = (df[f"{f}_gold"] == df[f"{f}_pred"]).sum()
        print(f"{f:<10} {correct}/{len(df)} = {correct / len(df):.2%}")
    all_ok = (df[[f"{f}_gold" for f in FIELDS]].values == df[[f"{f}_pred" for f in FIELDS]].values).all(axis=1)
    print(f"{'all 3':<10} {all_ok.sum()}/{len(df)} = {all_ok.mean():.2%}\n")

    for f in FIELDS:
        print(f"== Confusion matrix: {f} (แถว = gold, คอลัมน์ = pred) ==")
        cm = pd.crosstab(df[f"{f}_gold"], df[f"{f}_pred"], rownames=["gold"], colnames=["pred"], margins=True)
        print(cm.to_string(), "\n")

    wrong = df[~all_ok].merge(msgs, on="ticket_id", how="left")
    wrong["wrong_fields"] = wrong.apply(
        lambda r: ",".join(f for f in FIELDS if r[f"{f}_gold"] != r[f"{f}_pred"]), axis=1
    )
    # เรียงให้ category ผิดขึ้นก่อน เพราะสำคัญที่สุด
    wrong["_cat_wrong"] = wrong["category_gold"] != wrong["category_pred"]
    wrong = wrong.sort_values(["_cat_wrong", "ticket_id"], ascending=[False, True])

    print(f"== แถวที่ผิด ({len(wrong)} แถว, แสดง {min(n_errors, len(wrong))}) ==")
    for _, r in wrong.head(n_errors).iterrows():
        print(f"\n{r['ticket_id']}  ผิดที่: {r['wrong_fields']}")
        print(f"  ข้อความ: {r['message']}")
        for f in FIELDS:
            mark = "  " if r[f"{f}_gold"] == r[f"{f}_pred"] else "✗ "
            print(f"  {mark}{f:<10} gold={r[f'{f}_gold']:<22} pred={r[f'{f}_pred']}")


if __name__ == "__main__":
    main(*sys.argv[1:])
