"""Generate synthetic demo_history.csv with 65 consecutive weeks for demo SKUs."""

import datetime

import pandas as pd

start_date = datetime.date(2010, 1, 4)
weeks = [start_date + datetime.timedelta(weeks=i) for i in range(65)]

rows = []
for w in weeks:
    # Synthetic realistic sales
    rows.append(
        {"sku_id": "85123A", "week_start": str(w), "units_sold": 50 + (w.isocalendar()[1] % 10) * 3}
    )
    rows.append(
        {"sku_id": "84077", "week_start": str(w), "units_sold": 30 + (w.isocalendar()[1] % 7) * 2}
    )

df = pd.DataFrame(rows)
df.to_csv("tests/fixtures/demo_history.csv", index=False)
print("Created tests/fixtures/demo_history.csv")
