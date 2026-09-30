import sqlite3
import pathlib
from typing import List, Dict, Any, Optional
from collector.models import AptDealRecord

class AptDatabase:
    def __init__(self, db_path: str = "data/apt_sales.db"):
        self.db_path = str(db_path)
        pathlib.Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS apt_sales (
                trade_id TEXT PRIMARY KEY,
                deal_date TEXT NOT NULL,
                sido TEXT NOT NULL,
                sigungu TEXT NOT NULL,
                dong TEXT NOT NULL,
                apt_name TEXT NOT NULL,
                deal_amount INTEGER NOT NULL,
                exclusive_area REAL NOT NULL,
                pyeong REAL NOT NULL,
                unit_price_pyeong INTEGER NOT NULL,
                floor INTEGER NOT NULL,
                build_year INTEGER NOT NULL,
                cancel_deal_day TEXT,
                deal_type TEXT,
                lawd_cd TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_deal_date ON apt_sales(deal_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sido_sigungu ON apt_sales(sido, sigungu)")
            conn.commit()
        finally:
            conn.close()

    def insert_records(self, records: List[AptDealRecord]) -> int:
        if not records:
            return 0
        
        sql = """
        INSERT OR IGNORE INTO apt_sales (
            trade_id, deal_date, sido, sigungu, dong, apt_name,
            deal_amount, exclusive_area, pyeong, unit_price_pyeong,
            floor, build_year, cancel_deal_day, deal_type, lawd_cd
        ) VALUES (
            :trade_id, :deal_date, :sido, :sigungu, :dong, :apt_name,
            :deal_amount, :exclusive_area, :pyeong, :unit_price_pyeong,
            :floor, :build_year, :cancel_deal_day, :deal_type, :lawd_cd
        )
        """
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            inserted_count = 0
            for record in records:
                before = conn.total_changes
                cursor.execute(sql, record.to_dict())
                if conn.total_changes > before:
                    inserted_count += 1
            conn.commit()
            return inserted_count
        finally:
            conn.close()

    def get_total_count(self) -> int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM apt_sales")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def get_recent_deals(
        self,
        start_date: str,
        end_date: Optional[str] = None,
        include_cancelled: bool = False
    ) -> List[Dict[str, Any]]:
        conditions = ["deal_date >= ?"]
        params = [start_date]

        if end_date:
            conditions.append("deal_date <= ?")
            params.append(end_date)

        if not include_cancelled:
            conditions.append("(cancel_deal_day IS NULL OR cancel_deal_day = '')")

        where_clause = " AND ".join(conditions)
        query = f"""
        SELECT * FROM apt_sales
        WHERE {where_clause}
        ORDER BY deal_date DESC, deal_amount DESC
        """

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
