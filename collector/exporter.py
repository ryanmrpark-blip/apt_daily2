import pathlib
from datetime import datetime, timedelta
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from collector.db import AptDatabase

def export_recent_deals_to_parquet(
    db_path: str = "data/apt_sales.db",
    parquet_path: str = "data/apt_sales_recent.parquet",
    days: int = 14
) -> int:
    """SQLite에서 최근 N일간의 정상 거래 데이터를 추출하여 Parquet로 내보냅니다."""
    db = AptDatabase(db_path)
    today = datetime.now().date()
    start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")

    records = db.get_recent_deals(start_date=start_date, include_cancelled=False)
    target_path = pathlib.Path(parquet_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        # 빈 DataFrame이라도 올바른 스키마를 갖추어 생성
        df = pd.DataFrame(columns=[
            "trade_id", "deal_date", "sido", "sigungu", "dong",
            "apt_name", "deal_amount", "exclusive_area", "pyeong",
            "unit_price_pyeong", "floor", "build_year", "cancel_deal_day",
            "deal_type", "lawd_cd"
        ])
    else:
        df = pd.DataFrame(records)

    table = pa.Table.from_pandas(df)
    pq.write_table(table, target_path, compression="snappy")
    return len(df)
