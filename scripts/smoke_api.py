"""Verify actual forecast and constrained reorder serving with synthetic history."""

import csv
import json
import math
from urllib.request import Request, urlopen


def request(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        "http://127.0.0.1:8000" + path, data=data, headers={"Content-Type": "application/json"}
    )
    with urlopen(req, timeout=30) as response:
        assert response.status == 200
        return json.load(response)


def main() -> None:
    assert request("/ready")["status"] == "ready"
    with open("tests/fixtures/demo_history.csv", newline="", encoding="utf-8") as handle:
        history = [
            {**row, "units_sold": float(row["units_sold"])} for row in csv.DictReader(handle)
        ]
    common = {"as_of_week_start": max(row["week_start"] for row in history), "history": history}
    forecast = request("/forecast", {**common, "horizon_weeks": 4})
    assert len(forecast["predictions"]) == 8
    assert all(
        math.isfinite(row["predicted_units"]) and row["predicted_units"] >= 0
        for row in forecast["predictions"]
    )
    reorder = request(
        "/reorder",
        {
            **common,
            "warehouse_capacity_slots": 5000,
            "weekly_budgets_scu": [2000.0] * 4,
            "inventory": [
                {"sku_id": sku, "on_hand_units": 50, "incoming_week_1_units": 0}
                for sku in ["85123A", "84077"]
            ],
        },
    )
    assert reorder["status"] == "OPTIMAL"
    assert reorder["validation_status"] == "PASSED"
    assert len(reorder["worklist"]) == 2
    print(json.dumps({"forecast_rows": 8, "reorder_validation": reorder["validation_status"]}))


if __name__ == "__main__":
    main()
