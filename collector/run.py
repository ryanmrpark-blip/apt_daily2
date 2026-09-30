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

    # 3. AI 부동산 애널리스트 일일 브리핑 자동 생성 (GEMINI_API_KEY 설정 시)
    import os
    gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if gemini_key:
        logger.info("GEMINI_API_KEY detected. Checking recent deal dates for AI analyst briefing...")
        from analytics.gemini_analyst import GeminiAnalyst
        analyst = GeminiAnalyst(api_key=gemini_key)

        available_dates = collector.db.get_available_deal_dates(limit=5)
        for date_info in available_dates:
            d_date = date_info["deal_date"]
            if not date_info["has_summary"] and date_info["deal_count"] > 0:
                logger.info(f"Generating AI Analyst Report for {d_date} ({date_info['deal_count']} deals)...")
                try:
                    deals = collector.db.get_deals_by_date(d_date, include_cancelled=False)
                    if deals:
                        summary = analyst.generate_daily_analysis(d_date, deals)
                        max_deal = max(deals, key=lambda x: x.get("deal_amount", 0))
                        collector.db.save_daily_summary(
                            deal_date=d_date,
                            summary=summary,
                            deal_count=len(deals),
                            max_price_apt=f"{max_deal['apt_name']} ({max_deal['deal_amount']}만원)",
                            avg_price=date_info.get("avg_price", 0),
                            model=analyst.model
                        )
                        logger.info(f"AI report generated and saved for {d_date}!")
                except Exception as ex:
                    logger.warning(f"Failed to generate AI report for {d_date}: {ex}")

    # 4. 일자별 AI 분석 요약 JSON 내보내기 (Git 커밋 및 배포 동기화용)
    exported_summaries = collector.db.export_summaries_to_json("data/daily_summaries.json")
    logger.info(f"Exported {exported_summaries} daily AI summaries to data/daily_summaries.json")

if __name__ == "__main__":
    main()
