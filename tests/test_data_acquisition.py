"""Tests for dataset acquisition and provenance tracking (Task T02)."""

import hashlib
import json

import pandas as pd
import yaml

from demandguard.data import acquire_source_data, compute_sha256


def test_compute_sha256(tmp_path):
    """Verify SHA-256 calculation on known string."""
    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"DemandGuard Test Content")
    expected = hashlib.sha256(b"DemandGuard Test Content").hexdigest()
    assert compute_sha256(test_file) == expected


def test_acquire_creates_valid_manifest(tmp_path):
    """Verify that acquire creates a compliant manifest from an excel file."""
    excel_path = tmp_path / "test_retail.xlsx"
    manifest_path = tmp_path / "source_manifest.json"

    # Create synthetic workbook with two sheets
    df1 = pd.DataFrame(
        {
            "Invoice": ["489434"],
            "StockCode": ["85048"],
            "Description": ["15CM CHRISTMAS GLASS BALL 20 LIGHTS"],
            "Quantity": [12],
            "InvoiceDate": ["2009-12-01 07:45:00"],
            "Price": [6.95],
            "Customer ID": [13085.0],
            "Country": ["United Kingdom"],
        }
    )
    df2 = pd.DataFrame(
        {
            "Invoice": ["536365"],
            "StockCode": ["85123A"],
            "Description": ["WHITE HANGING HEART T-LIGHT HOLDER"],
            "Quantity": [6],
            "InvoiceDate": ["2010-12-01 08:26:00"],
            "Price": [2.55],
            "Customer ID": [17850.0],
            "Country": ["United Kingdom"],
        }
    )

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name="Year 2009-2010", index=False)
        df2.to_excel(writer, sheet_name="Year 2010-2011", index=False)

    config = {
        "data": {
            "source_landing_url": "https://archive.ics.uci.edu/dataset/502/online+retail+ii",
            "source_download_url": "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip",
            "raw_excel_path": str(excel_path),
            "source_manifest_path": str(manifest_path),
        }
    }
    cfg_file = tmp_path / "project.yaml"
    with open(cfg_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    manifest = acquire_source_data(str(cfg_file))

    assert manifest["dataset_name"] == "Online Retail II"
    assert manifest_path.exists()
    with open(manifest_path, "r", encoding="utf-8") as f:
        saved = json.load(f)

    assert saved["dataset_name"] == "Online Retail II"
    assert "Year 2009-2010" in saved["sheet_names"]
    assert "Year 2010-2011" in saved["sheet_names"]
    assert saved["total_raw_rows"] == 2
    assert len(saved["sha256"]) == 64
