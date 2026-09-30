import pytest
import tempfile
import pathlib
from collector.db import AptDatabase
from collector.models import AptDealRecord
from analytics.gemini_analyst import GeminiAnalyst

@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    db = AptDatabase(db_path)
    
    # 샘플 데이터 삽입
    records = [
        AptDealRecord(
            deal_date="2026-09-29",
            sido="서울특별시",
            sigungu="서초구",
            dong="반포동",
            apt_name="반포자이",
            deal_amount=350000,
            exclusive_area=84.9,
            floor=15,
            build_year=2009,
            cancel_deal_day=None,
            deal_type="중개거래",
            lawd_cd="11650"
        ),
        AptDealRecord(
            deal_date="2026-09-29",
            sido="경기도",
            sigungu="성남시 분당구",
            dong="정자동",
            apt_name="정든마을",
            deal_amount=120000,
            exclusive_area=59.8,
            floor=10,
            build_year=1995,
            cancel_deal_day=None,
            deal_type="중개거래",
            lawd_cd="41135"
        )
    ]
    db.insert_records(records)
    yield db
    pathlib.Path(db_path).unlink(missing_ok=True)

def test_daily_summary_crud(temp_db):
    # 1. 초기 상태: 요약 없음
    summary = temp_db.get_daily_summary("2026-09-29")
    assert summary is None

    # 2. 요약 저장
    sample_text = "### 📌 마켓 총평\n반포자이 등 주요 핵심지 고가 거래가 시장을 견인하고 있습니다."
    temp_db.save_daily_summary(
        deal_date="2026-09-29",
        summary=sample_text,
        deal_count=2,
        max_price_apt="반포자이 (350000만원)",
        avg_price=235000,
        model="gemini-2.5-flash"
    )

    # 3. 요약 조회 (캐시 로드)
    saved = temp_db.get_daily_summary("2026-09-29")
    assert saved is not None
    assert saved["deal_date"] == "2026-09-29"
    assert saved["summary"] == sample_text
    assert saved["deal_count"] == 2
    assert saved["model"] == "gemini-2.5-flash"

    # 4. 목록 조회
    all_summaries = temp_db.list_daily_summaries()
    assert len(all_summaries) == 1
    assert all_summaries[0]["deal_date"] == "2026-09-29"

    # 5. 거래 일자 목록 조회 시 has_summary 확인
    dates_info = temp_db.get_available_deal_dates(limit=10)
    assert len(dates_info) == 1
    assert dates_info[0]["deal_date"] == "2026-09-29"
    assert dates_info[0]["has_summary"] == 1

    # 6. 요약 삭제
    deleted = temp_db.delete_daily_summary("2026-09-29")
    assert deleted is True
    assert temp_db.get_daily_summary("2026-09-29") is None

def test_get_deals_by_date(temp_db):
    deals = temp_db.get_deals_by_date("2026-09-29")
    assert len(deals) == 2
    assert deals[0]["apt_name"] == "반포자이"  # 금액 내림차순 정렬 확인
    assert deals[1]["apt_name"] == "정든마을"

def test_gemini_analyst_prompt_preparation(temp_db):
    deals = temp_db.get_deals_by_date("2026-09-29")
    analyst = GeminiAnalyst(api_key="mock_key_for_testing")
    prompt = analyst._prepare_prompt("2026-09-29", deals)
    assert "2026-09-29" in prompt
    assert "반포자이" in prompt
    assert "총 유효 거래 건수" in prompt
    assert "마켓 총평" in prompt
