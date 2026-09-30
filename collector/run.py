import argparse
import logging
import sys
from dotenv import load_dotenv
from collector.collector import AptDailyCollector
from collector.exporter import export_recent_deals_to_parquet

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="전국 아파트 실거래가 수집 및 Parquet 내보내기")
    parser.add_argument("--days", type=int, default=7, help="수집 및 내보낼 최근 일수 (기본값: 7일)")
    parser.add_argument("--mock", action="store_true", help="공공데이터포털 API 대신 모의 데이터 생성")
    parser.add_argument("--db-path", type=str, default="data/apt_sales.db", help="SQLite DB 파일 경로")
    parser.add_argument("--parquet-path", type=str, default="data/apt_sales_recent.parquet", help="Parquet 파일 경로")
    parser.add_argument("--max-districts", type=int, default=None, help="테스트용 최대 수집 시군구 수")
    parser.add_argument("--delay", type=float, default=0.05, help="API 호출 간격(초)")

    args = parser.parse_args()

    collector = AptDailyCollector(db_path=args.db_path)

    if args.mock:
        logger.info(f"Generating mock data for the last {args.days} days...")
        collector.collect_mock(days=args.days)
    else:
        logger.info(f"Starting OpenAPI collection for the last {args.days} days...")
        collector.collect(days=args.days, delay_sec=args.delay, max_districts=args.max_districts)

    logger.info(f"Exporting recent deals (last {args.days} days) to Parquet: {args.parquet_path}")
    count = export_recent_deals_to_parquet(
        db_path=args.db_path,
        parquet_path=args.parquet_path,
        days=args.days
    )
    logger.info(f"Export complete. Total {count} recent normal deals stored in {args.parquet_path}.")

if __name__ == "__main__":
    main()
