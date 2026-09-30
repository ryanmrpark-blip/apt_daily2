import pytest
import tempfile
import pathlib
import pandas as pd
from collector.models import AptDealRecord
from collector.db import AptDatabase
from collector.exporter import export_recent_deals_to_parquet
from analytics.duckdb_client import DuckDBAnalytics

@pytest.fixture
def sample_dataset():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = f.name
    f.close()
    
    parquet_path = db_path.replace(".db", ".parquet")
    db = AptDatabase(db_path)

    records = [
        AptDealRecord("2026-09-29", "서울특별시", "강남구", "대치동", "은마", 250000, 84.43, 10, 1979),
        AptDealRecord("2026-09-28", "서울특별시", "서초구", "반포동", "아크로리버파크", 450000, 84.95, 18, 2016),
        AptDealRecord("2026-09-27", "경기도", "성남시 분당구", "백현동", "판교푸르지오", 220000, 84.9, 12, 2011),
        AptDealRecord("2026-09-26", "부산광역시", "해운대구", "우동", "해운대아이파크", 160000, 84.9, 25, 2011),
        # 취소 거래 1건
        AptDealRecord("2026-09-25", "서울특별시", "송파구", "잠실동", "잠실엘스", 240000, 84.8, 8, 2008, cancel_deal_day="2026-09-26")
    ]
    db.insert_records(records)
    
    export_recent_deals_to_parquet(db_path=db_path, parquet_path=parquet_path, days=14)
    analytics = DuckDBAnalytics(parquet_path=parquet_path)
    
    yield analytics, parquet_path, db_path

    # cleanup
    pathlib.Path(db_path).unlink(missing_ok=True)
    pathlib.Path(parquet_path).unlink(missing_ok=True)

def test_duckdb_kpis(sample_dataset):
    analytics, _, _ = sample_dataset
    kpi = analytics.get_kpis()
    
    # 4 normal deals (cancelled excluded)
    assert kpi["total_deals"] == 4
    assert kpi["max_price"] == 450000
    assert "아크로리버파크" in kpi["max_price_apt"]
    # average price = (250000 + 450000 + 220000 + 160000) / 4 = 270000
    assert kpi["avg_price"] == 270000

def test_duckdb_filtered_kpis(sample_dataset):
    analytics, _, _ = sample_dataset
    seoul_kpi = analytics.get_kpis(sido="서울특별시")
    assert seoul_kpi["total_deals"] == 2
    assert seoul_kpi["avg_price"] == 350000

def test_duckdb_top_deals(sample_dataset):
    analytics, _, _ = sample_dataset
    top = analytics.get_top_deals(limit=2)
    assert len(top) == 2
    assert top.iloc[0]["apt_name"] == "아크로리버파크"
    assert top.iloc[0]["deal_amount"] == 450000

def test_duckdb_sido_summary(sample_dataset):
    analytics, _, _ = sample_dataset
    sido_df = analytics.get_sido_summary()
    assert len(sido_df) == 3 # 서울, 경기, 부산
