"""Tests for data cleaning, reconciliation, and weekly aggregation (Task T03)."""

import pandas as pd

from demandguard.data import clean_transactions, prepare_weekly_panel


def test_clean_transactions_exclusions():
    """Verify each cleaning rule properly categorises exclusions."""
    raw_data = pd.DataFrame(
        [
            # Valid row 1
            {
                "invoice_id": "489434",
                "sku_id": "85048",
                "description": "VALID 1",
                "quantity": 10,
                "transaction_at": "2009-12-01 10:00:00",
                "sale_unit_price_gbp": 2.5,
                "country": "United Kingdom",
            },
            # Valid row 2
            {
                "invoice_id": "489435",
                "sku_id": "85048",
                "description": "VALID 2",
                "quantity": 5,
                "transaction_at": "2009-12-02 11:00:00",
                "sale_unit_price_gbp": 2.5,
                "country": "United Kingdom",
            },
            # Cancellation (starts with C)
            {
                "invoice_id": "C489436",
                "sku_id": "85048",
                "description": "CANCELLATION",
                "quantity": -5,
                "transaction_at": "2009-12-02 12:00:00",
                "sale_unit_price_gbp": 2.5,
                "country": "United Kingdom",
            },
            # Nonpositive quantity
            {
                "invoice_id": "489437",
                "sku_id": "85048",
                "description": "ZERO QTY",
                "quantity": 0,
                "transaction_at": "2009-12-02 13:00:00",
                "sale_unit_price_gbp": 2.5,
                "country": "United Kingdom",
            },
            # Nonpositive price
            {
                "invoice_id": "489438",
                "sku_id": "85048",
                "description": "FREE",
                "quantity": 10,
                "transaction_at": "2009-12-02 14:00:00",
                "sale_unit_price_gbp": 0.0,
                "country": "United Kingdom",
            },
            # Nonmerchandise code
            {
                "invoice_id": "489439",
                "sku_id": "POST",
                "description": "POSTAGE",
                "quantity": 1,
                "transaction_at": "2009-12-02 15:00:00",
                "sale_unit_price_gbp": 15.0,
                "country": "United Kingdom",
            },
            # Non-UK country
            {
                "invoice_id": "489440",
                "sku_id": "85048",
                "description": "FRANCE",
                "quantity": 20,
                "transaction_at": "2009-12-02 16:00:00",
                "sale_unit_price_gbp": 2.5,
                "country": "France",
            },
            # Missing essential (missing sku_id)
            {
                "invoice_id": "489441",
                "sku_id": None,
                "description": "NO SKU",
                "quantity": 5,
                "transaction_at": "2009-12-02 17:00:00",
                "sale_unit_price_gbp": 2.5,
                "country": "United Kingdom",
            },
        ]
    )

    clean_df, audit = clean_transactions(raw_data, country="United Kingdom")

    assert len(clean_df) == 2
    assert clean_df["quantity"].sum() == 15
    assert audit["exclusions"]["cancellations"]["rows"] == 1
    assert audit["exclusions"]["nonpositive_quantity"]["rows"] == 1
    assert audit["exclusions"]["nonpositive_or_nan_price"]["rows"] == 1
    assert audit["exclusions"]["nonmerchandise_codes"]["rows"] == 1
    assert audit["exclusions"]["non_target_country"]["rows"] == 1
    assert audit["exclusions"]["missing_essentials"]["rows"] == 1


def test_prepare_weekly_panel_monday_boundaries(tmp_path):
    """Verify DuckDB weekly aggregation sums Monday-to-Sunday and truncates partial edge weeks."""
    out_parquet = tmp_path / "weekly_sales.parquet"

    # Range spanning 2 complete weeks:
    # 2009-11-30 is Monday (Week 1)
    # 2009-12-06 is Sunday (End of Week 1)
    # 2009-12-07 is Monday (Week 2)
    # 2009-12-13 is Sunday (End of Week 2)
    tx_df = pd.DataFrame(
        [
            # Partial start day (e.g. Sunday 2009-11-29) - should be excluded if first monday is 2009-11-30
            {
                "invoice_id": "1",
                "sku_id": "SKU_A",
                "description": "A",
                "quantity": 100,
                "transaction_at": "2009-11-29 12:00:00",
                "sale_unit_price_gbp": 1.0,
                "country": "United Kingdom",
            },
            # Week 1 transactions
            {
                "invoice_id": "2",
                "sku_id": "SKU_A",
                "description": "A",
                "quantity": 10,
                "transaction_at": "2009-11-30 08:00:00",
                "sale_unit_price_gbp": 1.0,
                "country": "United Kingdom",
            },
            {
                "invoice_id": "3",
                "sku_id": "SKU_A",
                "description": "A",
                "quantity": 20,
                "transaction_at": "2009-12-06 20:00:00",
                "sale_unit_price_gbp": 1.0,
                "country": "United Kingdom",
            },
            {
                "invoice_id": "4",
                "sku_id": "SKU_B",
                "description": "B",
                "quantity": 5,
                "transaction_at": "2009-12-01 10:00:00",
                "sale_unit_price_gbp": 2.0,
                "country": "United Kingdom",
            },
            # Week 2 transactions
            {
                "invoice_id": "5",
                "sku_id": "SKU_A",
                "description": "A",
                "quantity": 15,
                "transaction_at": "2009-12-07 09:00:00",
                "sale_unit_price_gbp": 1.0,
                "country": "United Kingdom",
            },
            {
                "invoice_id": "6",
                "sku_id": "SKU_B",
                "description": "B",
                "quantity": 25,
                "transaction_at": "2009-12-13 18:00:00",
                "sale_unit_price_gbp": 2.0,
                "country": "United Kingdom",
            },
            # Partial trailing day (Monday 2009-12-14) - should be excluded as last complete week ended Sunday 12-13
            {
                "invoice_id": "7",
                "sku_id": "SKU_A",
                "description": "A",
                "quantity": 200,
                "transaction_at": "2009-12-14 09:00:00",
                "sale_unit_price_gbp": 1.0,
                "country": "United Kingdom",
            },
        ]
    )
    tx_df["transaction_at"] = pd.to_datetime(tx_df["transaction_at"])

    weekly_df = prepare_weekly_panel(tx_df, output_parquet_path=out_parquet)

    assert out_parquet.exists()
    assert len(weekly_df) == 4  # (SKU_A, W1), (SKU_A, W2), (SKU_B, W1), (SKU_B, W2)

    sku_a_w1 = weekly_df[
        (weekly_df["sku_id"] == "SKU_A") & (weekly_df["week_start"].astype(str) == "2009-11-30")
    ]
    assert len(sku_a_w1) == 1
    assert sku_a_w1["units_sold"].iloc[0] == 30  # 10 + 20

    sku_b_w2 = weekly_df[
        (weekly_df["sku_id"] == "SKU_B") & (weekly_df["week_start"].astype(str) == "2009-12-07")
    ]
    assert len(sku_b_w2) == 1
    assert sku_b_w2["units_sold"].iloc[0] == 25


def test_estimate_censored_demand():
    """Verify Tobit unbiasing flags stockouts and imputes latent demand."""
    from demandguard.data import estimate_censored_demand

    panel = pd.DataFrame(
        [
            {"sku_id": "SKU_1", "week_start": "2020-01-06", "units_sold": 50},
            {"sku_id": "SKU_1", "week_start": "2020-01-13", "units_sold": 60},
            {"sku_id": "SKU_1", "week_start": "2020-01-20", "units_sold": 0},  # Censored stockout
            {"sku_id": "SKU_1", "week_start": "2020-01-27", "units_sold": 55},
            {"sku_id": "SKU_1", "week_start": "2020-02-03", "units_sold": 45},
        ]
    )
    result = estimate_censored_demand(panel, min_history_weeks=3)
    assert "unbiased_demand" in result.columns
    assert "is_censored" in result.columns
    censored_row = result[result["week_start"] == "2020-01-20"].iloc[0]
    assert censored_row["is_censored"] is True or censored_row["is_censored"] == 1
    assert censored_row["unbiased_demand"] > 0


def test_compute_cold_start_priors():
    """Verify cold start priors extraction."""
    from demandguard.data import compute_cold_start_priors

    df = pd.DataFrame([{"quantity": 10}, {"quantity": 20}, {"quantity": 30}])
    priors = compute_cold_start_priors(df)
    assert "global" in priors
    assert priors["global"]["mean_weekly_units"] == 20.0

