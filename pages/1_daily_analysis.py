import os
import pathlib
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime
from dotenv import load_dotenv

from collector.db import AptDatabase
from analytics.gemini_analyst import GeminiAnalyst

load_dotenv()

# 1. 페이지 설정
st.set_page_config(
    page_title="일자별 상세 거래 & AI 분석 | 애경이를 위한",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. 프리미엄 커스텀 CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1300px;
    }

    .hero-banner {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        color: white;
        padding: 24px 28px;
        border-radius: 14px;
        margin-bottom: 24px;
        box-shadow: 0 4px 15px rgba(15, 23, 42, 0.15);
    }
    .hero-title {
        font-size: 1.85rem;
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
        background: rgba(225, 29, 72, 0.15);
        color: #FB7185;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 12px;
        border-radius: 9999px;
        border: 1px solid rgba(225, 29, 72, 0.3);
    }

    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
        position: relative;
        overflow: hidden;
    }
    .kpi-label {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.7rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #94A3B8;
        margin-top: 4px;
    }

    /* AI 애널리스트 리포트 카드 */
    .analyst-card {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
        border: 1px solid #CBD5E1;
        border-top: 4px solid #6366F1;
        border-radius: 14px;
        padding: 24px 28px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.06);
    }
    .analyst-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 14px;
        margin-bottom: 18px;
    }
    .analyst-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #1E1B4B;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .analyst-badge-cached {
        background: #EEF2FF;
        color: #4F46E5;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #C7D2FE;
    }
    .analyst-badge-new {
        background: #ECFDF5;
        color: #059669;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #A7F3D0;
    }

    /* 비밀번호 입력 필드의 눈 모양(보기/숨기기) 아이콘 완전 비활성화 및 숨김 */
    button[data-testid="stTextInputVisibilityToggle"],
    button[aria-label="Show password text"],
    button[aria-label="Hide password text"],
    .stTextInput button {
        display: none !important;
        pointer-events: none !important;
        visibility: hidden !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터베이스 및 클라이언트 초기화
DB_PATH = "data/apt_sales.db"
db = AptDatabase(DB_PATH)

# 사용 가능한 거래 일자 목록 조회
available_dates_info = db.get_available_deal_dates(limit=60)

# 사이드바 설정
with st.sidebar:
    st.markdown("<div style='font-size: 1.05rem; font-weight: 700; color: #E11D48; margin-bottom: 12px;'>🌸 애경이를 위한 맞춤 분석</div>", unsafe_allow_html=True)
    
    st.markdown("### 📑 페이지 이동")
    st.page_link("app.py", label="전국 종합 대시보드", icon="🏢")

    st.markdown("---")
    st.markdown("### 📅 일자 선택")

    if not available_dates_info:
        st.warning("수집된 거래 일자가 없습니다. 메인 페이지에서 데이터를 먼저 수집해 주세요.")
        st.stop()

    date_options = [d["deal_date"] for d in available_dates_info]
    
    # 날짜별 포맷 라벨 (거래건수 및 AI 분석 저장 여부 표시)
    def format_date_label(deal_date):
        item = next((d for d in available_dates_info if d["deal_date"] == deal_date), None)
        if item:
            badge = " [🤖 AI 분석완료]" if item["has_summary"] else ""
            return f"{deal_date} ({item['deal_count']}건){badge}"
        return deal_date

    selected_date = st.selectbox(
        "조회할 계약일자",
        date_options,
        index=0,
        format_func=format_date_label
    )

    st.markdown("---")
    st.markdown("### 🔑 Gemini AI 설정")
    
    env_gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_gemini_key:
        st.markdown("""
        <div style='background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; padding: 10px 14px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; display: flex; align-items: center; gap: 8px;'>
            <span>🔒</span>
            <div>
                <div>Gemini API Key 보안 연동됨</div>
                <div style='font-size: 0.75rem; color: #047857; font-weight: normal; margin-top: 2px;'>.env 파일의 키가 안전하게 암전 처리되었습니다.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander("다른 키로 임시 변경 (선택)"):
            user_gemini_key = st.text_input(
                "Gemini API Key 변경",
                value="",
                type="password",
                placeholder="새로운 키 입력...",
                help="입력하지 않으면 .env에 설정된 키가 기본 사용됩니다."
            )
        active_gemini_key = user_gemini_key.strip() if user_gemini_key.strip() else env_gemini_key
    else:
        st.markdown("""
        <div style='background: #FEF2F2; border: 1px solid #FECACA; color: #991B1B; padding: 8px 12px; border-radius: 8px; font-size: 0.85rem; font-weight: 600;'>
            ⚠️ Gemini API Key 미설정
        </div>
        """, unsafe_allow_html=True)
        user_gemini_key = st.text_input(
            "Gemini API Key 입력",
            value="",
            type="password",
            placeholder="AI Studio 키 입력...",
            help="세션 동안 사용할 Gemini API Key를 입력하세요."
        )
        active_gemini_key = user_gemini_key.strip()

    gemini_analyst = GeminiAnalyst(api_key=active_gemini_key)

    st.markdown("---")
    st.markdown("### 🔍 당일 데이터 필터")
    
    # 선택된 날짜의 전체 데이터 로드
    day_deals = db.get_deals_by_date(selected_date, include_cancelled=False)
    df_day = pd.DataFrame(day_deals)

    if not df_day.empty:
        sidos = ["전체"] + sorted(list(df_day["sido"].unique()))
        selected_sido = st.selectbox("시·도 필터", sidos, index=0)
        
        pyeong_min = int(df_day["pyeong"].min()) if "pyeong" in df_day else 10
        pyeong_max = int(df_day["pyeong"].max()) if "pyeong" in df_day else 90
        if pyeong_min == pyeong_max:
            pyeong_max += 1

        selected_pyeong = st.slider(
            "공급 평형대",
            min_value=max(5, pyeong_min),
            max_value=max(80, pyeong_max),
            value=(max(5, pyeong_min), max(80, pyeong_max)),
            step=5,
            format="%d평"
        )
    else:
        selected_sido = "전체"
        selected_pyeong = (10, 90)

# 헤더 영역
st.markdown(f"""
<div class="hero-banner">
    <div class="hero-title">📅 {selected_date} 실거래 상세 & AI 애널리스트 브리핑</div>
    <div class="hero-subtitle">
        <span class="status-badge">🌸 애경이를 위한 부동산 마켓 리서치</span>
        <span>국토교통부 실거래가 전수 검증 및 Gemini 2.5 Flash 기반 심층 분석</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not day_deals:
    st.info(f"선택하신 일자({selected_date})에는 등록된 실거래 데이터가 없습니다.")
    st.stop()

# 4. 당일 핵심 지표 (KPI Cards)
col1, col2, col3, col4 = st.columns(4)

total_count = len(df_day)
avg_price = int(df_day["deal_amount"].mean())
max_deal = df_day.sort_values(by="deal_amount", ascending=False).iloc[0]
avg_unit_price = int(df_day["unit_price_pyeong"].mean())

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">당일 총 거래건수</div>
        <div class="kpi-value">{total_count:,}건</div>
        <div class="kpi-sub">{selected_date} 계약 체결분</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    max_amount_str = f"{max_deal['deal_amount'] / 10000:.1f}억" if max_deal['deal_amount'] >= 10000 else f"{max_deal['deal_amount']:,}만"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">당일 최고가 단지</div>
        <div class="kpi-value" style="color: #E11D48;">{max_amount_str}</div>
        <div class="kpi-sub" title="{max_deal['apt_name']}">{max_deal['apt_name']} ({max_deal['sido']} {max_deal['sigungu']})</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    avg_price_str = f"{avg_price / 10000:.1f}억" if avg_price >= 10000 else f"{avg_price:,}만"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">당일 평균 매매가</div>
        <div class="kpi-value">{avg_price_str}</div>
        <div class="kpi-sub">전체 단지 평균</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">평당 평균 거래단가</div>
        <div class="kpi-value">{avg_unit_price:,}만원</div>
        <div class="kpi-sub">3.3㎡당 평균 단가</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

# 5. AI 부동산 수석 애널리스트 브리핑 섹션 (SQLite 캐시 연동)
saved_summary_info = db.get_daily_summary(selected_date)

st.markdown("### 🏛️ AI 수석 부동산 애널리스트 일일 브리핑")

if saved_summary_info:
    # (1) SQLite DB에 이미 저장된 요약이 있는 경우 -> 즉시 로드
    created_at_str = saved_summary_info.get("created_at", "")[:19]
    model_str = saved_summary_info.get("model", "gemini-2.5-flash")
    
    st.markdown(f"""
    <div class="analyst-card">
        <div class="analyst-header">
            <div class="analyst-title">
                <span>🤖</span> 수석 부동산 애널리스트 마켓 리포트
            </div>
            <div class="analyst-badge-cached">
                💾 SQLite DB 저장본 (생성일시: {created_at_str} | 모델: {model_str})
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown(saved_summary_info["summary"])
    st.markdown("</div>", unsafe_allow_html=True)

    # 재분석 옵션
    with st.expander("🔄 애널리스트 분석 새로고침 (DB 갱신)"):
        st.caption("새로운 거래 데이터가 추가되었거나 최신 프롬프트로 재분석하고 싶으신 경우 아래 버튼을 클릭하세요.")
        if st.button("Gemini AI 재분석 실행 및 DB 갱신", type="secondary"):
            if not gemini_analyst.is_available():
                st.error("Gemini API Key가 필요합니다. 좌측 사이드바에 유효한 API Key를 입력해 주세요.")
            else:
                with st.spinner(f"Gemini AI가 {selected_date} 실거래 데이터를 다시 분석 중입니다..."):
                    try:
                        new_summary = gemini_analyst.generate_daily_analysis(selected_date, day_deals)
                        db.save_daily_summary(
                            deal_date=selected_date,
                            summary=new_summary,
                            deal_count=len(day_deals),
                            max_price_apt=f"{max_deal['apt_name']} ({max_deal['deal_amount']}만원)",
                            avg_price=avg_price,
                            model=gemini_analyst.model
                        )
                        st.success("✅ 새로운 분석이 SQLite DB에 성공적으로 갱신되었습니다!")
                        st.rerun()
                    except Exception as err:
                        st.error(f"분석 갱신 실패: {err}")

else:
    # (2) 아직 분석 요약이 저장되지 않은 경우
    st.info(f"💡 **{selected_date}**의 AI 애널리스트 분석 리포트가 아직 생성되지 않았습니다.")
    
    if not gemini_analyst.is_available():
        st.warning("👉 Gemini API를 사용하여 분석 리포트를 생성하려면 **좌측 사이드바의 'Gemini API Key'** 입력창에 키를 입력하거나 `.env` 파일에 `GEMINI_API_KEY`를 설정해 주세요.")
    else:
        st.markdown("버튼을 누르면 **Gemini 2.5 Flash**가 당일 실거래가를 전수 분석하여 전문 브리핑을 작성하고 **SQLite DB에 영구 저장**합니다. (다음 조회부터는 저장된 내용이 0.01초 만에 표시됩니다)")
        
        if st.button("🚀 AI 수석 애널리스트 분석 생성하기 (최초 1회 실행)", type="primary"):
            with st.spinner(f"Gemini AI가 {selected_date} 실거래 데이터({len(day_deals)}건)를 다각도로 정밀 분석하고 있습니다..."):
                try:
                    summary_text = gemini_analyst.generate_daily_analysis(selected_date, day_deals)
                    db.save_daily_summary(
                        deal_date=selected_date,
                        summary=summary_text,
                        deal_count=len(day_deals),
                        max_price_apt=f"{max_deal['apt_name']} ({max_deal['deal_amount']}만원)",
                        avg_price=avg_price,
                        model=gemini_analyst.model
                    )
                    st.success("✅ AI 애널리스트 분석 생성이 완료되어 SQLite DB에 영구 저장되었습니다!")
                    st.rerun()
                except Exception as err:
                    st.error(f"분석 생성 중 오류가 발생했습니다: {err}")

st.markdown("<div style='height: 32px;'></div>", unsafe_allow_html=True)

# 6. 당일 거래 분포 시각화 (시도별 거래량 및 가격대 분포)
st.markdown("### 📊 당일 거래 분포 시각화")
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("##### 📍 시·도별 거래량 현황")
    sido_counts = df_day["sido"].value_counts().reset_index()
    sido_counts.columns = ["sido", "count"]
    
    chart1 = alt.Chart(sido_counts.head(10)).mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4).encode(
        y=alt.Y("sido:N", sort="-x", title=None),
        x=alt.X("count:Q", title="거래 건수"),
        color=alt.value("#3B82F6"),
        tooltip=[
            alt.Tooltip("sido", title="시·도"),
            alt.Tooltip("count", title="거래 건수", format=",")
        ]
    ).properties(height=260)
    st.altair_chart(chart1, use_container_width=True)

with chart_col2:
    st.markdown("##### 💰 가격대별 거래 비중")
    bins = [0, 30000, 60000, 90000, 150000, float("inf")]
    labels = ["3억 미만", "3~6억", "6~9억", "9~15억", "15억 이상"]
    df_day["price_bracket"] = pd.cut(df_day["deal_amount"], bins=bins, labels=labels, right=False)
    price_dist = df_day["price_bracket"].value_counts()[labels].reset_index()
    price_dist.columns = ["bracket", "count"]

    chart2 = alt.Chart(price_dist).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("bracket:N", sort=labels, title=None),
        y=alt.Y("count:Q", title="거래 건수"),
        color=alt.Color("bracket:N", scale=alt.Scale(scheme="blues"), legend=None),
        tooltip=[
            alt.Tooltip("bracket", title="가격대"),
            alt.Tooltip("count", title="거래 건수", format=",")
        ]
    ).properties(height=260)
    st.altair_chart(chart2, use_container_width=True)

st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

# 7. 당일 실거래 상세 내역 테이블
st.markdown("### 📋 당일 실거래 전수 상세 목록")

# 필터링 적용
filtered_df = df_day.copy()
if selected_sido != "전체":
    filtered_df = filtered_df[filtered_df["sido"] == selected_sido]

filtered_df = filtered_df[
    (filtered_df["pyeong"] >= selected_pyeong[0]) & 
    (filtered_df["pyeong"] <= selected_pyeong[1])
]

# 검색 필터
search_query = st.text_input("🔍 아파트명 또는 동 이름으로 단지 검색", placeholder="예: 힐스테이트, 반포, 역삼...")
if search_query:
    filtered_df = filtered_df[
        filtered_df["apt_name"].str.contains(search_query, na=False) |
        filtered_df["dong"].str.contains(search_query, na=False)
    ]

# 표시용 컬럼 포맷팅
display_df = filtered_df.copy()
display_df["거래금액_억만원"] = display_df["deal_amount"].apply(
    lambda x: f"{x // 10000}억 {x % 10000:,}만원" if x >= 10000 else f"{x:,}만원"
)
display_df["전용면적_㎡"] = display_df["exclusive_area"].apply(lambda x: f"{x:.1f}㎡")
display_df["공급평형"] = display_df["pyeong"].apply(lambda x: f"{x:.1f}평")
display_df["평당단가"] = display_df["unit_price_pyeong"].apply(lambda x: f"{x:,}만원")
display_df["층수"] = display_df["floor"].apply(lambda x: f"{x}층")
display_df["건축년도"] = display_df["build_year"].apply(lambda x: f"{x}년")

cols_to_show = [
    "sido", "sigungu", "dong", "apt_name", "거래금액_억만원",
    "공급평형", "전용면적_㎡", "평당단가", "층수", "건축년도", "deal_type"
]
rename_cols = {
    "sido": "시·도",
    "sigungu": "시·군·구",
    "dong": "법정동",
    "apt_name": "아파트 단지명",
    "deal_type": "거래유형"
}
table_data = display_df[cols_to_show].rename(columns=rename_cols)

st.dataframe(
    table_data,
    use_container_width=True,
    hide_index=True,
    column_config={
        "거래금액_억만원": st.column_config.TextColumn("거래금액", width="medium"),
        "아파트 단지명": st.column_config.TextColumn("아파트 단지명", width="large")
    }
)

# CSV 다운로드
csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label=f"📥 {selected_date} 필터링 실거래 데이터 CSV 다운로드 ({len(filtered_df):,}건)",
    data=csv_data,
    file_name=f"apt_sales_{selected_date}.csv",
    mime="text/csv",
    type="secondary"
)
