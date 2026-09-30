import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pathlib
from dotenv import load_dotenv

load_dotenv()

from analytics.duckdb_client import DuckDBAnalytics
from collector.collector import AptDailyCollector
from collector.exporter import export_recent_deals_to_parquet

# 1. 페이지 레이아웃 및 타이틀
st.set_page_config(
    page_title="🌸 애경이를 위한 전국 아파트 실거래가 주간 대시보드",
    page_icon="🌸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 커스텀 프리미엄 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .dedicated-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: linear-gradient(135deg, rgba(244, 63, 94, 0.25), rgba(251, 113, 133, 0.15));
        border: 1px solid rgba(251, 113, 133, 0.45);
        color: #FECDD3;
        font-size: 0.95rem;
        font-weight: 700;
        padding: 5px 16px;
        border-radius: 9999px;
        margin-bottom: 12px;
        box-shadow: 0 2px 10px rgba(244, 63, 94, 0.2);
        backdrop-filter: blur(4px);
        letter-spacing: -0.01em;
    }

    .hero-container {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: white;
        padding: 24px 28px;
        border-radius: 14px;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(15, 23, 42, 0.15);
    }
    .hero-title {
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin-bottom: 6px;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #94A3B8;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .status-badge {
        background: rgba(16, 185, 129, 0.2);
        color: #34D399;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 3px 10px;
        border-radius: 9999px;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }

    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
        position: relative;
        overflow: hidden;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    .kpi-blue::before { background: linear-gradient(90deg, #3B82F6, #60A5FA); }
    .kpi-indigo::before { background: linear-gradient(90deg, #6366F1, #818CF8); }
    .kpi-rose::before { background: linear-gradient(90deg, #F43F5E, #FB7185); }
    .kpi-emerald::before { background: linear-gradient(90deg, #10B981, #34D399); }

    .kpi-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    .kpi-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748B;
    }
    .kpi-icon {
        font-size: 1.1rem;
    }
    .kpi-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
    }
    .kpi-desc {
        font-size: 0.8rem;
        color: #94A3B8;
        margin-top: 6px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .section-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

PARQUET_FILE = "data/apt_sales_recent.parquet"
DB_FILE = "data/apt_sales.db"

@st.cache_resource
def get_analytics_engine():
    return DuckDBAnalytics(parquet_path=PARQUET_FILE)

analytics = get_analytics_engine()

# 데이터 소스 준비 여부 검사
parquet_path = pathlib.Path(PARQUET_FILE)
if not parquet_path.exists():
    st.warning("⚠️ 최근 실거래가 데이터 파일(`data/apt_sales_recent.parquet`)이 아직 준비되지 않았습니다.")
    st.info("아래 버튼을 클릭하면 즉시 테스트용 전국 모의 실거래 데이터를 생성하여 대시보드를 둘러보실 수 있습니다.")
    if st.button("🧪 모의(Mock) 실거래 데이터 즉시 생성 및 파이프라인 가동", type="primary"):
        with st.spinner("모의 실거래 데이터 수집 및 Parquet 변환 진행 중..."):
            collector = AptDailyCollector(db_path=DB_FILE)
            collector.collect_mock(days=7, count_per_day=50)
            export_recent_deals_to_parquet(db_path=DB_FILE, parquet_path=PARQUET_FILE, days=7)
        st.success("데이터 생성 완료! 대시보드를 새로고침합니다.")
        st.rerun()
    st.stop()

# 파일 메타데이터
last_update = datetime.fromtimestamp(parquet_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
min_date, max_date = analytics.get_min_max_dates()

# 3. 사이드바 필터
with st.sidebar:
    st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #E11D48; margin-bottom: 12px; display: flex; align-items: center; gap: 6px;'><span>🌸</span> 애경이를 위한 맞춤 분석</div>", unsafe_allow_html=True)
    st.markdown("### 🔍 필터 및 검색 옵션")
    
    # 시도 선택
    sido_list = ["전체"] + analytics.get_distinct_sidos()
    selected_sido = st.selectbox("📍 시·도 선택", sido_list, index=0)

    # 시군구 선택
    sigungu_list = ["전체"]
    if selected_sido != "전체":
        sigungu_list += analytics.get_distinct_sigungus(sido=selected_sido)
    selected_sigungu = st.selectbox("🏙️ 시·군·구 선택", sigungu_list, index=0)

    st.markdown("---")

    # 평형대 필터
    pyeong_range = st.slider(
        "📐 공급 평형대",
        min_value=10,
        max_value=90,
        value=(10, 90),
        step=5,
        format="%d평"
    )

    # 거래 유형 필터
    selected_deal_type = st.radio(
        "🤝 거래 구분",
        ["전체", "중개거래", "직거래"],
        horizontal=True
    )

    st.markdown("---")
    
    # 빠른 아파트/동 텍스트 검색
    search_keyword = st.text_input("🔎 단지명 또는 법정동 검색", placeholder="예: 은마, 반포동, 자이")

    st.markdown("---")
    st.caption(f"🕒 **데이터 기준 기간**: {min_date} ~ {max_date}")
    st.caption(f"🔄 **최종 수집 일시**: {last_update}")
    st.caption("⚡ **파이프라인**: SQLite ➔ Parquet ➔ DuckDB")

# 금액 포맷터 (억/만원 환산)
def format_korean_won(amount_manwon: int) -> str:
    if amount_manwon >= 10000:
        eok = amount_manwon // 10000
        man = amount_manwon % 10000
        if man > 0:
            return f"{eok:,}억 {man:,}만원"
        return f"{eok:,}억원"
    return f"{amount_manwon:,}만원"

# 4. 헤더 배너
st.markdown(f"""
<div class='hero-container'>
    <div class='dedicated-badge'>🌸 애경이를 위한 ✨</div>
    <div class='hero-title'>🏢 전국 아파트 최근 실거래가 주간 대시보드</div>
    <div class='hero-subtitle'>
        <span class='status-badge'>● LIVE DATA</span>
        <span>국토교통부 아파트 매매 실거래 상세 OpenAPI 기반</span>
        <span>·</span>
        <span>조회 기간: <strong>{min_date} ~ {max_date}</strong> (최근 7일)</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. DuckDB KPI 집계 쿼리 실행
kpi = analytics.get_kpis(
    sido=selected_sido,
    sigungu=selected_sigungu,
    min_pyeong=pyeong_range[0],
    max_pyeong=pyeong_range[1],
    search_query=search_keyword,
    deal_type=selected_deal_type
)

# 6. 핵심 KPI 메트릭 카드 (4열 그리드)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class='kpi-card kpi-blue'>
        <div class='kpi-header'>
            <span class='kpi-title'>총 거래 건수</span>
            <span class='kpi-icon'>📋</span>
        </div>
        <div class='kpi-value'>{kpi['total_deals']:,}<span style='font-size:1.1rem;font-weight:500;color:#64748B;'> 건</span></div>
        <div class='kpi-desc'>정상 체결 실거래가 (취소 건 제외)</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    avg_price_text = format_korean_won(kpi['avg_price'])
    st.markdown(f"""
    <div class='kpi-card kpi-indigo'>
        <div class='kpi-header'>
            <span class='kpi-title'>평균 매매 가격</span>
            <span class='kpi-icon'>💳</span>
        </div>
        <div class='kpi-value' style='color:#4F46E5;'>{avg_price_text}</div>
        <div class='kpi-desc'>총 거래금액 합계: {format_korean_won(kpi['total_sum_price'])}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    max_price_text = format_korean_won(kpi['max_price'])
    st.markdown(f"""
    <div class='kpi-card kpi-rose'>
        <div class='kpi-header'>
            <span class='kpi-title'>최고 거래가</span>
            <span class='kpi-icon'>🔥</span>
        </div>
        <div class='kpi-value' style='color:#E11D48;'>{max_price_text}</div>
        <div class='kpi-desc' title='{kpi["max_price_apt"]}'>{kpi['max_price_apt']}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    unit_price = kpi['avg_unit_price']
    st.markdown(f"""
    <div class='kpi-card kpi-emerald'>
        <div class='kpi-header'>
            <span class='kpi-title'>평균 평당 단가</span>
            <span class='kpi-icon'>📐</span>
        </div>
        <div class='kpi-value' style='color:#059669;'>{unit_price:,}<span style='font-size:1.1rem;font-weight:500;color:#64748B;'> 만원</span></div>
        <div class='kpi-desc'>공급면적 3.3㎡(1평)당 환산 단가</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
st.write("")

# 7. 다차원 분석 탭 구성
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 종합 시장 현황 및 시각화",
    "🏆 최고가 및 평당가 랭킹",
    "📋 실거래가 전체 상세 조회",
    "⚙️ 데이터 파이프라인 및 배포 안내"
])

# ----------------- TAB 1: 종합 시장 분석 -----------------
with tab1:
    chart_c1, chart_c2 = st.columns([1, 1])

    with chart_c1:
        st.subheader("📍 지역별 거래량 & 평균 매매 가격")
        sido_data = analytics.get_sido_summary(
            sido=selected_sido,
            sigungu=selected_sigungu,
            min_pyeong=pyeong_range[0],
            max_pyeong=pyeong_range[1],
            search_query=search_keyword,
            deal_type=selected_deal_type
        )
        if not sido_data.empty:
            fig_bar = px.bar(
                sido_data.head(10),
                x="sido",
                y="deal_count",
                color="avg_deal_amount",
                labels={"sido": "지역", "deal_count": "거래 건수(건)", "avg_deal_amount": "평균 매매가(만원)"},
                color_continuous_scale="Purples",
                text="deal_count"
            )
            fig_bar.update_traces(textposition="outside")
            fig_bar.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=380,
                xaxis_title="",
                yaxis_title="거래 건수"
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("조건에 일치하는 지역 데이터가 없습니다.")

    with chart_c2:
        st.subheader("📈 일자별 실거래 신고 추이")
        daily_data = analytics.get_daily_trend(
            sido=selected_sido,
            sigungu=selected_sigungu,
            min_pyeong=pyeong_range[0],
            max_pyeong=pyeong_range[1],
            search_query=search_keyword,
            deal_type=selected_deal_type
        )
        if not daily_data.empty:
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=daily_data["deal_date"],
                y=daily_data["deal_count"],
                mode="lines+markers",
                name="거래 건수",
                line=dict(color="#2563EB", width=3, shape="spline"),
                fill="tozeroy",
                fillcolor="rgba(37, 99, 235, 0.08)"
            ))
            fig_line.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                height=380,
                xaxis_title="계약일자",
                yaxis_title="신고 건수",
                hovermode="x unified"
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("조건에 일치하는 일자별 데이터가 없습니다.")

    st.markdown("---")

    # 평형대별 분포 도넛 차트
    st.subheader("📐 평형대별 거래 비중 분포")
    pyeong_df = analytics.get_pyeong_distribution(
        sido=selected_sido,
        sigungu=selected_sigungu,
        search_query=search_keyword,
        deal_type=selected_deal_type
    )
    if not pyeong_df.empty:
        fig_donut = px.pie(
            pyeong_df,
            names="pyeong_category",
            values="deal_count",
            hole=0.45,
            color_discrete_sequence=px.colors.sequential.Teal
        )
        fig_donut.update_traces(textinfo="percent+label")
        fig_donut.update_layout(margin=dict(l=10, r=10, t=20, b=10), height=320)
        st.plotly_chart(fig_donut, use_container_width=True)

# ----------------- TAB 2: 최고가 및 랭킹 -----------------
with tab2:
    rank_c1, rank_c2 = st.columns(2)

    with rank_c1:
        st.subheader("💰 최고 매매가 아파트 TOP 10")
        top_deals = analytics.get_top_deals(
            limit=10,
            sido=selected_sido,
            sigungu=selected_sigungu,
            min_pyeong=pyeong_range[0],
            max_pyeong=pyeong_range[1],
            search_query=search_keyword,
            deal_type=selected_deal_type
        )
        if not top_deals.empty:
            view_top = top_deals.copy()
            view_top["거래금액"] = view_top["deal_amount"].apply(format_korean_won)
            view_top["평당단가"] = view_top["unit_price_pyeong"].apply(lambda x: f"{x:,}만원/평")
            view_top["전용면적"] = view_top["exclusive_area"].apply(lambda x: f"{x:.1f}㎡ ({round(x/3.3, 1)}평)")
            view_top = view_top[["deal_date", "sido", "sigungu", "dong", "apt_name", "floor", "전용면적", "거래금액", "평당단가"]]
            view_top.columns = ["계약일", "시도", "시군구", "법정동", "단지명", "층", "면적", "거래금액", "평당단가"]
            st.dataframe(view_top, hide_index=True, use_container_width=True)
        else:
            st.info("해당 조건의 거래 건이 없습니다.")

    with rank_c2:
        st.subheader("💎 평당가 최고 아파트 TOP 10")
        top_unit_deals = analytics.get_top_unit_price_deals(
            limit=10,
            sido=selected_sido,
            sigungu=selected_sigungu,
            min_pyeong=pyeong_range[0],
            max_pyeong=pyeong_range[1],
            search_query=search_keyword,
            deal_type=selected_deal_type
        )
        if not top_unit_deals.empty:
            view_unit = top_unit_deals.copy()
            view_unit["평당단가"] = view_unit["unit_price_pyeong"].apply(lambda x: f"{x:,}만원/평")
            view_unit["거래금액"] = view_unit["deal_amount"].apply(format_korean_won)
            view_unit["전용면적"] = view_unit["exclusive_area"].apply(lambda x: f"{x:.1f}㎡ ({round(x/3.3, 1)}평)")
            view_unit = view_unit[["deal_date", "sido", "sigungu", "dong", "apt_name", "floor", "전용면적", "평당단가", "거래금액"]]
            view_unit.columns = ["계약일", "시도", "시군구", "법정동", "단지명", "층", "면적", "평당단가", "총거래금액"]
            st.dataframe(view_unit, hide_index=True, use_container_width=True)
        else:
            st.info("해당 조건의 거래 건이 없습니다.")

# ----------------- TAB 3: 전체 실거래 조회 -----------------
with tab3:
    st.subheader("📋 실거래 상세 내역 탐색기")
    
    all_deals = analytics.get_all_deals_df(
        sido=selected_sido,
        sigungu=selected_sigungu,
        min_pyeong=pyeong_range[0],
        max_pyeong=pyeong_range[1],
        search_query=search_keyword,
        deal_type=selected_deal_type
    )

    if not all_deals.empty:
        col_summary, col_dl = st.columns([5, 1])
        with col_summary:
            st.info(f"검색 조건에 맞는 총 **{len(all_deals):,}** 건의 아파트 실거래 데이터가 조회되었습니다.")
        with col_dl:
            csv_blob = all_deals.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="📥 CSV 내보내기",
                data=csv_blob,
                file_name=f"apt_sales_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        table_display = all_deals.copy()
        table_display["거래금액"] = table_display["deal_amount"].apply(format_korean_won)
        table_display["평당단가"] = table_display["unit_price_pyeong"].apply(lambda x: f"{x:,}만원")
        table_display["전용면적"] = table_display["exclusive_area"].apply(lambda x: f"{x:.2f}㎡ ({round(x/3.3, 1)}평)")
        table_display = table_display[[
            "deal_date", "sido", "sigungu", "dong", "apt_name",
            "floor", "전용면적", "거래금액", "평당단가", "build_year", "deal_type"
        ]]
        table_display.columns = [
            "계약일자", "시도", "시군구", "법정동", "단지명",
            "층", "전용면적", "거래금액", "평당단가", "건축년도", "거래유형"
        ]
        st.dataframe(table_display, hide_index=True, use_container_width=True, height=520)
    else:
        st.warning("선택하신 조건에 해당하는 거래 내역이 없습니다. 사이드바 필터를 변경해 보세요.")

# ----------------- TAB 4: 파이프라인 및 배포 -----------------
with tab4:
    st.subheader("⚙️ 데이터 파이프라인 및 자동 배포 현황")
    
    st_c1, st_c2, st_c3 = st.columns(3)
    parquet_size_kb = round(parquet_path.stat().st_size / 1024, 1) if parquet_path.exists() else 0
    db_path_obj = pathlib.Path(DB_FILE)
    db_size_kb = round(db_path_obj.stat().st_size / 1024, 1) if db_path_obj.exists() else 0

    with st_c1:
        st.metric("Parquet 파일 크기 (배포용)", f"{parquet_size_kb} KB")
    with st_c2:
        st.metric("SQLite 원장 파일 크기", f"{db_size_kb} KB")
    with st_c3:
        st.metric("최종 동기화 시각", last_update)

    st.markdown("---")
    st.markdown("#### 🔄 데이터 수동 갱신")
    st.caption("새로운 모의 실거래 데이터를 추가하거나 OpenAPI를 통한 즉시 수집을 실행할 수 있습니다.")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🧪 모의 실거래가 50건 추가 수집 실행"):
            collector = AptDailyCollector(db_path=DB_FILE)
            added = collector.collect_mock(days=7, count_per_day=50)
            export_recent_deals_to_parquet(db_path=DB_FILE, parquet_path=PARQUET_FILE, days=7)
            st.success(f"{added}건의 모의 거래가 성공적으로 수집되어 Parquet가 갱신되었습니다.")
            st.rerun()

    with col_btn2:
        st.code("uv run python -m collector.run --days 7", language="bash")
        st.caption("터미널에서 실제 공공데이터 OpenAPI 일일 수집을 실행하는 명령어")

    st.markdown("---")
    st.markdown("#### ☁️ 무료 자동 배포 가이드 요약")
    st.markdown("""
    1. **GitHub 저장소 푸시**: 본 저장소를 GitHub에 푸시합니다.
    2. **GitHub Secrets 설정**: `Settings > Secrets and variables > Actions`에 `DATA_GO_KR_API_KEY` (공공데이터포털 서비스키)를 등록합니다.
    3. **GitHub Actions 스케줄**: 매일 아침 06:00 KST에 `.github/workflows/daily_collect.yml`이 자동 실행되어 최신 1주 데이터를 수집하고 Git Push합니다.
    4. **Streamlit Community Cloud 배포**: [share.streamlit.io](https://share.streamlit.io)에서 저장소와 `app.py`를 지정하면 무료로 자동 배포 및 업데이트가 연동됩니다.
    """)
