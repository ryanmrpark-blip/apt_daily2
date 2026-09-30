import json
import logging
import os
import pathlib
import time
from datetime import datetime, timedelta
from typing import List, Optional
from dotenv import load_dotenv
from collector.models import AptDealRecord
from collector.client import MolitAptClient
from collector.db import AptDatabase
from collector.mock_generator import generate_mock_records

load_dotenv()

logger = logging.getLogger(__name__)

class AptDailyCollector:
    def __init__(
        self,
        db_path: str = "data/apt_sales.db",
        lawd_file: str = "collector/lawd_cd.json",
        service_key: Optional[str] = None
    ):
        self.db = AptDatabase(db_path)
        self.lawd_file = pathlib.Path(lawd_file)
        self.service_key = service_key or os.environ.get("DATA_GO_KR_API_KEY", "")
        self.client = MolitAptClient(self.service_key) if self.service_key else None

    def load_lawd_codes(self) -> List[dict]:
        if not self.lawd_file.exists():
            logger.warning(f"Lawd code file {self.lawd_file} not found.")
            return []
        with open(self.lawd_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_target_ymds(self, days: int = 7) -> List[str]:
        """최근 N일의 날짜가 속하는 YYYYMM 목록을 반환합니다."""
        today = datetime.now().date()
        ymd_set = set()
        for d in range(days + 1):
            target_date = today - timedelta(days=d)
            ymd_set.add(target_date.strftime("%Y%m"))
        return sorted(list(ymd_set))

    def collect(self, days: int = 7, delay_sec: float = 0.05, max_districts: Optional[int] = None) -> int:
        """전국 시군구를 순회하며 실거래 데이터를 수집하여 SQLite에 적재합니다."""
        if not self.service_key:
            logger.info("API Key not found. Using mock records generator instead.")
            return self.collect_mock(days=days)

        districts = self.load_lawd_codes()
        if max_districts:
            districts = districts[:max_districts]

        target_ymds = self.get_target_ymds(days=days)
        total_inserted = 0
        total_districts = len(districts)

        logger.info(f"Starting collection: {total_districts} districts, target months: {target_ymds}")

        for idx, dist in enumerate(districts, 1):
            lawd_cd = dist["code"]
            sido = dist["sido"]
            sigungu = dist["sigungu"]

            for ymd in target_ymds:
                records = self.client.fetch_district_month(
                    lawd_cd=lawd_cd,
                    deal_ymd=ymd,
                    sido=sido,
                    sigungu=sigungu
                )
                if records:
                    inserted = self.db.insert_records(records)
                    total_inserted += inserted

                if delay_sec > 0:
                    time.sleep(delay_sec)

            if idx % 20 == 0 or idx == total_districts:
                logger.info(f"Progress: [{idx}/{total_districts}] districts processed. Total inserted: {total_inserted}")

        logger.info(f"Collection completed. Total new records inserted: {total_inserted}")
        return total_inserted

    def collect_mock(self, days: int = 7, count_per_day: int = 50) -> int:
        """모의 데이터를 생성하여 SQLite에 적재합니다."""
        records = generate_mock_records(days=days, count_per_day=count_per_day)
        inserted = self.db.insert_records(records)
        logger.info(f"Mock collection completed: {inserted} records inserted.")
        return inserted
