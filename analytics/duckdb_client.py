import duckdb
import pathlib
import pandas as pd
from typing import Optional, Dict, Any

class DuckDBAnalytics:
    def __init__(self, parquet_path: str = "data/apt_sales_recent.parquet"):
        self.parquet_path = str(parquet_path)
        self.con = duckdb.connect(database=":memory:")

    def _is_source_ready(self) -> bool:
        return pathlib.Path(self.parquet_path).exists()

    def _build_where_clause(
        self,
        sido: Optional[str] = None,
        sigungu: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_pyeong: Optional[float] = None,
        max_pyeong: Optional[float] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        search_query: Optional[str] = None,
        deal_type: Optional[str] = None
    ) -> str:
        clauses = []
        if sido and sido != "전체":
            clauses.append(f"sido = '{sido}'")
        if sigungu and sigungu != "전체":
            clauses.append(f"sigungu = '{sigungu}'")
        if start_date:
            clauses.append(f"deal_date >= '{start_date}'")
        if end_date:
            clauses.append(f"deal_date <= '{end_date}'")
        if min_pyeong is not None:
            clauses.append(f"pyeong >= {min_pyeong}")
        if max_pyeong is not None:
            clauses.append(f"pyeong <= {max_pyeong}")
        if min_price is not None and min_price > 0:
            clauses.append(f"deal_amount >= {min_price}")
        if max_price is not None:
            clauses.append(f"deal_amount <= {max_price}")
        if deal_type and deal_type != "전체":
            clauses.append(f"deal_type = '{deal_type}'")
        if search_query and search_query.strip():
            sq = search_query.strip().replace("'", "''")
            clauses.append(f"(apt_name ILIKE '%{sq}%' OR dong ILIKE '%{sq}%')")

        if clauses:
            return "WHERE " + " AND ".join(clauses)
        return ""

    def get_kpis(
        self,
        sido: Optional[str] = None,
        sigungu: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_pyeong: Optional[float] = None,
        max_pyeong: Optional[float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """핵심 지표(총 거래건수, 평균가, 최고가, 최고가 단지, 평균 평당가)를 계산합니다."""
        if not self._is_source_ready():
            return {
                "total_deals": 0, "avg_price": 0, "max_price": 0,
                "max_price_apt": "-", "avg_unit_price": 0, "total_sum_price": 0
            }

        where = self._build_where_clause(
            sido=sido, sigungu=sigungu, start_date=start_date,
            end_date=end_date, min_pyeong=min_pyeong, max_pyeong=max_pyeong,
            **kwargs
        )
        
        # 1. 집계 쿼리
        summary_query = f"""
        SELECT 
            COUNT(*) as total_deals,
            COALESCE(ROUND(AVG(deal_amount)), 0) as avg_price,
            COALESCE(MAX(deal_amount), 0) as max_price,
            COALESCE(ROUND(AVG(unit_price_pyeong)), 0) as avg_unit_price,
            COALESCE(SUM(deal_amount), 0) as total_sum_price
        FROM '{self.parquet_path}'
        {where}
        """
        res = self.con.execute(summary_query).fetchone()
        total_deals, avg_price, max_price, avg_unit_price, total_sum_price = res

        # 2. 최고가 단지 정보 조회
        max_apt_str = "-"
        if total_deals > 0 and max_price > 0:
            top_apt_query = f"""
            SELECT apt_name, sigungu, floor, exclusive_area
            FROM '{self.parquet_path}'
            {where}
            ORDER BY deal_amount DESC
            LIMIT 1
            """
            top_row = self.con.execute(top_apt_query).fetchone()
            if top_row:
                max_apt_str = f"{top_row[0]} ({top_row[1]}, {top_row[2]}층, {top_row[3]:.1f}㎡)"

        return {
            "total_deals": int(total_deals),
            "avg_price": int(avg_price),
            "max_price": int(max_price),
            "max_price_apt": max_apt_str,
            "avg_unit_price": int(avg_unit_price),
            "total_sum_price": int(total_sum_price)
        }

    def get_top_deals(self, limit: int = 10, **kwargs) -> pd.DataFrame:
        """거래 금액 상위 N개 아파트 거래 목록을 반환합니다."""
        if not self._is_source_ready():
            return pd.DataFrame()

        where = self._build_where_clause(**kwargs)
        query = f"""
        SELECT 
            deal_date,
            sido,
            sigungu,
            dong,
            apt_name,
            deal_amount,
            exclusive_area,
            pyeong,
            unit_price_pyeong,
            floor,
            build_year,
            deal_type
        FROM '{self.parquet_path}'
        {where}
        ORDER BY deal_amount DESC
        LIMIT {limit}
        """
        return self.con.execute(query).df()

    def get_top_unit_price_deals(self, limit: int = 10, **kwargs) -> pd.DataFrame:
        """평당가 상위 N개 아파트 거래 목록을 반환합니다."""
        if not self._is_source_ready():
            return pd.DataFrame()

        where = self._build_where_clause(**kwargs)
        query = f"""
        SELECT 
            deal_date,
            sido,
            sigungu,
            dong,
            apt_name,
            deal_amount,
            exclusive_area,
            pyeong,
            unit_price_pyeong,
            floor,
            build_year,
            deal_type
        FROM '{self.parquet_path}'
        {where}
        ORDER BY unit_price_pyeong DESC
        LIMIT {limit}
        """
        return self.con.execute(query).df()

    def get_sido_summary(self, **kwargs) -> pd.DataFrame:
        """시도별 거래량 및 평균 가격 집계를 반환합니다."""
        if not self._is_source_ready():
            return pd.DataFrame()

        where = self._build_where_clause(**kwargs)
        query = f"""
        SELECT 
            sido,
            COUNT(*) as deal_count,
            ROUND(AVG(deal_amount)) as avg_deal_amount,
            ROUND(AVG(unit_price_pyeong)) as avg_unit_price
        FROM '{self.parquet_path}'
        {where}
        GROUP BY sido
        ORDER BY deal_count DESC
        """
        return self.con.execute(query).df()

    def get_daily_trend(self, **kwargs) -> pd.DataFrame:
        """일자별 거래량 및 평균 가격 추이를 반환합니다."""
        if not self._is_source_ready():
            return pd.DataFrame()

        where = self._build_where_clause(**kwargs)
        query = f"""
        SELECT 
            deal_date,
            COUNT(*) as deal_count,
            ROUND(AVG(deal_amount)) as avg_deal_amount
        FROM '{self.parquet_path}'
        {where}
        GROUP BY deal_date
        ORDER BY deal_date ASC
        """
        return self.con.execute(query).df()

    def get_pyeong_distribution(self, **kwargs) -> pd.DataFrame:
        """평형대 구간별 거래량 및 평균 매매가 집계를 반환합니다."""
        if not self._is_source_ready():
            return pd.DataFrame()

        where = self._build_where_clause(**kwargs)
        query = f"""
        SELECT 
            CASE 
                WHEN pyeong < 20 THEN '소형 (~20평 미만)'
                WHEN pyeong >= 20 AND pyeong < 30 THEN '중소형 (20~30평 미만)'
                WHEN pyeong >= 30 AND pyeong < 40 THEN '중형 (30~40평 미만)'
                ELSE '대형 (40평 이상)'
            END as pyeong_category,
            COUNT(*) as deal_count,
            ROUND(AVG(deal_amount)) as avg_deal_amount
        FROM '{self.parquet_path}'
        {where}
        GROUP BY pyeong_category
        ORDER BY deal_count DESC
        """
        return self.con.execute(query).df()

    def get_all_deals_df(self, **kwargs) -> pd.DataFrame:
        """조건에 맞는 전체 거래 목록을 반환합니다."""
        if not self._is_source_ready():
            return pd.DataFrame()

        where = self._build_where_clause(**kwargs)
        query = f"""
        SELECT 
            deal_date,
            sido,
            sigungu,
            dong,
            apt_name,
            deal_amount,
            exclusive_area,
            pyeong,
            unit_price_pyeong,
            floor,
            build_year,
            deal_type
        FROM '{self.parquet_path}'
        {where}
        ORDER BY deal_date DESC, deal_amount DESC
        """
        return self.con.execute(query).df()

    def get_distinct_sidos(self) -> list:
        if not self._is_source_ready():
            return []
        query = f"SELECT DISTINCT sido FROM '{self.parquet_path}' ORDER BY sido"
        rows = self.con.execute(query).fetchall()
        return [r[0] for r in rows]

    def get_distinct_sigungus(self, sido: Optional[str] = None) -> list:
        if not self._is_source_ready():
            return []
        where = f"WHERE sido = '{sido}'" if sido and sido != "전체" else ""
        query = f"SELECT DISTINCT sigungu FROM '{self.parquet_path}' {where} ORDER BY sigungu"
        rows = self.con.execute(query).fetchall()
        return [r[0] for r in rows]

    def get_min_max_dates(self) -> tuple:
        if not self._is_source_ready():
            return ("", "")
        query = f"SELECT MIN(deal_date), MAX(deal_date) FROM '{self.parquet_path}'"
        row = self.con.execute(query).fetchone()
        return (row[0] or "", row[1] or "")
