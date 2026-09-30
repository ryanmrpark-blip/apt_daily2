import sqlite3
import pathlib
from typing import List, Dict, Any, Optional
from collector.models import AptDealRecord

class AptDatabase:
    def __init__(self, db_path: str = "data/apt_sales.db", auto_sync_json: bool = True):
        self.db_path = str(db_path)
        self.auto_sync_json = auto_sync_json and ("apt_sales.db" in self.db_path)
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

            # AI 일자별 부동산 애널리스트 요약 테이블
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_analyses (
                deal_date TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                deal_count INTEGER NOT NULL DEFAULT 0,
                max_price_apt TEXT DEFAULT '',
                avg_price INTEGER DEFAULT 0,
                model TEXT DEFAULT 'gemini-2.5-flash',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            conn.commit()
        finally:
            conn.close()

        # data/daily_summaries.json이 존재하면 DB로 자동 초기 동기화 (운영 DB 전용)
        if self.auto_sync_json:
            default_json = pathlib.Path("data/daily_summaries.json")
            if default_json.exists():
                try:
                    self.import_summaries_from_json(str(default_json))
                except Exception:
                    pass


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

    def get_deals_by_date(
        self,
        deal_date: str,
        include_cancelled: bool = False
    ) -> List[Dict[str, Any]]:
        """특정 일자의 실거래 목록을 금액 내림차순으로 조회합니다."""
        conditions = ["deal_date = ?"]
        params = [deal_date]
        if not include_cancelled:
            conditions.append("(cancel_deal_day IS NULL OR cancel_deal_day = '')")

        query = f"""
        SELECT * FROM apt_sales
        WHERE {" AND ".join(conditions)}
        ORDER BY deal_amount DESC
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_available_deal_dates(self, limit: int = 30) -> List[Dict[str, Any]]:
        """거래가 존재하는 일자 목록과 거래건수, 요약 존재 여부를 조회합니다."""
        query = """
        SELECT 
            s.deal_date,
            COUNT(*) as deal_count,
            MAX(s.deal_amount) as max_price,
            CAST(AVG(s.deal_amount) AS INTEGER) as avg_price,
            CASE WHEN a.deal_date IS NOT NULL THEN 1 ELSE 0 END as has_summary
        FROM apt_sales s
        LEFT JOIN daily_analyses a ON s.deal_date = a.deal_date
        WHERE (s.cancel_deal_day IS NULL OR s.cancel_deal_day = '')
        GROUP BY s.deal_date
        ORDER BY s.deal_date DESC
        LIMIT ?
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_daily_summary(self, deal_date: str) -> Optional[Dict[str, Any]]:
        """특정 일자의 저장된 AI 부동산 애널리스트 요약을 반환합니다."""
        query = "SELECT * FROM daily_analyses WHERE deal_date = ?"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, (deal_date,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def save_daily_summary(
        self,
        deal_date: str,
        summary: str,
        deal_count: int = 0,
        max_price_apt: str = "",
        avg_price: int = 0,
        model: str = "gemini-2.5-flash"
    ) -> None:
        """일자별 AI 분석 요약을 SQLite에 저장하거나 갱신합니다."""
        sql = """
        INSERT INTO daily_analyses (
            deal_date, summary, deal_count, max_price_apt, avg_price, model, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(deal_date) DO UPDATE SET
            summary = excluded.summary,
            deal_count = excluded.deal_count,
            max_price_apt = excluded.max_price_apt,
            avg_price = excluded.avg_price,
            model = excluded.model,
            updated_at = CURRENT_TIMESTAMP
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql, (deal_date, summary, deal_count, max_price_apt, avg_price, model))
            conn.commit()
        finally:
            conn.close()

    def delete_daily_summary(self, deal_date: str) -> bool:
        """특정 일자의 요약을 삭제합니다."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM daily_analyses WHERE deal_date = ?", (deal_date,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def list_daily_summaries(self) -> List[Dict[str, Any]]:
        """저장된 모든 일자별 요약 목록을 조회합니다."""
        query = """
        SELECT deal_date, deal_count, max_price_apt, avg_price, model, created_at, updated_at
        FROM daily_analyses
        ORDER BY deal_date DESC
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def export_summaries_to_json(self, json_path: str = "data/daily_summaries.json") -> int:
        """저장된 모든 일자별 AI 분석 요약을 JSON 파일로 내보냅니다."""
        import json
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_analyses ORDER BY deal_date DESC")
            all_rows = [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

        target_file = pathlib.Path(json_path)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(all_rows, f, ensure_ascii=False, indent=2)
        return len(all_rows)

    def import_summaries_from_json(self, json_path: str = "data/daily_summaries.json") -> int:
        """JSON 파일에서 AI 분석 요약을 읽어 SQLite DB에 동기화합니다."""
        target_file = pathlib.Path(json_path)
        if not target_file.exists():
            return 0
        import json
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        imported = 0
        for item in data:
            if not item.get("deal_date") or not item.get("summary"):
                continue
            self.save_daily_summary(
                deal_date=item["deal_date"],
                summary=item["summary"],
                deal_count=item.get("deal_count", 0),
                max_price_apt=item.get("max_price_apt", ""),
                avg_price=item.get("avg_price", 0),
                model=item.get("model", "gemini-3.5-flash")
            )
            imported += 1
        return imported


