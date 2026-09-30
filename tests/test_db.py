import pytest
import sqlite3
import tempfile
import pathlib
import gc
from collector.models import AptDealRecord
from collector.db import AptDatabase

@pytest.fixture
def temp_db():
    f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = f.name
    f.close()
    
    db = AptDatabase(db_path)
    yield db
    
    del db
    gc.collect()
    try:
        pathlib.Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass

def test_trade_id_generation():
    rec = AptDealRecord(
        deal_date="2026-09-29",
        sido="서울특별시",
        sigungu="강남구",
        dong="대치동",
        apt_name="은마",
        deal_amount=240000,
        exclusive_area=84.43,
        floor=10,
        build_year=1979,
        cancel_deal_day=None
    )
    assert rec.trade_id is not None
    assert len(rec.trade_id) == 32 # MD5 hash
    assert rec.pyeong == round(84.43 / 3.3, 1)
    assert rec.unit_price_pyeong == round(240000 / (84.43 / 3.3))

def test_insert_and_deduplication(temp_db):
    rec = AptDealRecord(
        deal_date="2026-09-29",
        sido="서울특별시",
        sigungu="강남구",
        dong="대치동",
        apt_name="은마",
        deal_amount=240000,
        exclusive_area=84.43,
        floor=10,
        build_year=1979,
        cancel_deal_day=None
    )
    
    # 1st insert
    inserted = temp_db.insert_records([rec])
    assert inserted == 1

    # 2nd insert with same record (should be ignored due to trade_id conflict)
    inserted_again = temp_db.insert_records([rec])
    assert inserted_again == 0

    # Total count should still be 1
    total = temp_db.get_total_count()
    assert total == 1

def test_filter_recent_normal_deals(temp_db):
    normal_recent = AptDealRecord(
        deal_date="2026-09-28",
        sido="서울특별시",
        sigungu="서초구",
        dong="반포동",
        apt_name="아크로리버파크",
        deal_amount=380000,
        exclusive_area=84.95,
        floor=15,
        build_year=2016,
        cancel_deal_day=None
    )
    cancelled = AptDealRecord(
        deal_date="2026-09-28",
        sido="서울특별시",
        sigungu="서초구",
        dong="반포동",
        apt_name="반포자이",
        deal_amount=350000,
        exclusive_area=84.98,
        floor=8,
        build_year=2009,
        cancel_deal_day="2026-09-29"
    )
    temp_db.insert_records([normal_recent, cancelled])
    
    # Query normal deals
    deals = temp_db.get_recent_deals(start_date="2026-09-25")
    assert len(deals) == 1
    assert deals[0]["apt_name"] == "아크로리버파크"
