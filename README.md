# 🏢 전국 아파트 최근 실거래가 주간 대시보드 (`apt-daily`)

공공데이터포털([data.go.kr](https://www.data.go.kr/data/15126469/openapi.do)) 국토교통부 아파트 매매 실거래 상세 자료 OpenAPI를 활용하여 **최근 1주간의 전국 아파트 실거래가를 매일 자동 수집**하고, **SQLite / Parquet / DuckDB / Streamlit** 기반으로 분석 및 시각화하는 프로젝트입니다.

GitHub Actions와 Streamlit Community Cloud를 통해 **서버 비용 0원(완전 무료)**으로 매일 최신 데이터를 수집 및 호스팅할 수 있도록 설계되었습니다.

---

## 🏗️ 아키텍처 개요

```
[국토교통부 OpenAPI]
        │
        ▼ (일일 자동 수집 / Rate limit 보호)
[collector/collector.py]
        │
        ▼ (trade_id 해시 기반 Upsert 중복 제거)
[(SQLite) data/apt_sales.db]
        │
        ▼ (최근 7일 정상 거래 필터링 & Snappy 압축)
[data/apt_sales_recent.parquet]
        │
        ▼ (GitHub Actions Auto Commit & Push)
[GitHub Repository] ──(Webhook 동기화)──► [Streamlit Community Cloud]
                                                    │
                                                    ▼ (인메모리 초고속 SQL 분석)
                                             [DuckDB 쿼리 엔진]
                                                    │
                                                    ▼ (KPI 카드, 차트, 테이블)
                                             [Streamlit Dashboard]
```

### 기술 스택 및 역할
* **SQLite (`data/apt_sales.db`)**: 원천 거래 원장(OLTP). 전국 약 250개 시군구의 데이터를 고유 거래 키(`trade_id`)로 Upsert하여 중복 적재를 원천 방지합니다.
* **Parquet (`data/apt_sales_recent.parquet`)**: 컬럼 기반 압축 스토리지. 최근 1주일간의 정상 거래만 수십 KB 크기로 압축 보관하여 GitHub 저장소 용량 부담을 최소화합니다.
* **DuckDB (`analytics/duckdb_client.py`)**: 인메모리 OLAP 분석 쿼리 엔진. Streamlit 앱에서 Parquet 파일을 직접 SQL로 초고속 집계합니다.
* **Streamlit (`app.py`)**: 반응형 인터랙티브 대시보드. 핵심 KPI 카드, 지역별 비교 차트, 상세 필터 및 CSV 다운로드를 제공합니다.
* **GitHub Actions (`.github/workflows/daily_collect.yml`)**: 매일 한국 시간 06:00(UTC 21:00)에 데이터를 자동 수집 및 커밋합니다.

---

## 🚀 빠른 시작 (로컬 실행)

### 1. 가상환경 및 의존성 설치
본 프로젝트는 초고속 패키지 관리자인 `uv`를 사용합니다.

```bash
# 의존성 설치 및 가상환경 동기화
uv sync
```

### 2. 데이터 수집 실행

#### 🧪 모의(Mock) 데이터로 테스트 (API 키 불필요)
```bash
uv run python -m collector.run --mock --days 7
```

#### 🌐 실제 공공데이터포털 OpenAPI로 수집
```bash
# 환경변수에 공공데이터포털 일반 인증키(Encoding 또는 Decoding)를 설정합니다.
export DATA_GO_KR_API_KEY="YOUR_SERVICE_KEY"   # Linux/macOS
# set DATA_GO_KR_API_KEY=YOUR_SERVICE_KEY       # Windows CMD
# $env:DATA_GO_KR_API_KEY="YOUR_SERVICE_KEY"   # Windows PowerShell

uv run python -m collector.run --days 7
```

### 3. Streamlit 대시보드 실행
```bash
uv run streamlit run app.py
```
브라우저에서 `http://localhost:8501`로 접속하여 대시보드를 확인합니다.

### 4. 테스트 실행
```bash
uv run pytest
```

---

## ☁️ 무료 자동 배포 가이드

### 1단계: GitHub 저장소 업로드 및 Actions Secrets 설정
1. 이 프로젝트를 본인의 GitHub 저장소에 `push`합니다.
2. GitHub 저장소의 **Settings** > **Secrets and variables** > **Actions**로 이동합니다.
3. **New repository secret** 버튼을 클릭하고 다음 시크릿을 등록합니다:
   * **Name**: `DATA_GO_KR_API_KEY`
   * **Secret**: 공공데이터포털에서 발급받은 OpenAPI 서비스키 (Decoding 키 권장)
4. 이제 매일 아침 06:00 KST에 GitHub Actions가 자동으로 데이터를 수집하고 `data/` 디렉터리에 커밋 및 푸시합니다.
   * *Actions 탭에서 언제든지 'Run workflow'로 수동 즉시 실행도 가능합니다.*

### 2단계: Streamlit Community Cloud 배포 (무료 호스팅)
1. [share.streamlit.io](https://share.streamlit.io)에 접속하여 GitHub 계정으로 로그인합니다.
2. **New app**을 클릭합니다.
3. 방금 푸시한 본인의 GitHub 저장소, 브랜치(`main`), 메인 파일 경로(`app.py`)를 선택합니다.
4. **Deploy** 버튼을 누르면 배포가 완료됩니다!
5. GitHub Actions가 매일 아침 새 데이터를 푸시할 때마다 Streamlit Cloud가 자동으로 변경 사항을 감지하여 최신 대시보드를 보여줍니다.

---

## 📂 디렉터리 구조

```text
apt_daily/
├── .github/
│   └── workflows/
│       └── daily_collect.yml      # 매일 06:00 KST 자동 수집 GitHub Actions
├── collector/
│   ├── lawd_cd.json               # 전국 약 250개 시군구 법정동 코드
│   ├── models.py                  # 거래 데이터 모델 및 trade_id 해시
│   ├── db.py                      # SQLite 스키마 및 Upsert 로직
│   ├── client.py                  # 국토부 OpenAPI XML 파서 및 클라이언트
│   ├── mock_generator.py          # 오프라인/테스트용 모의 실거래 생성기
│   ├── exporter.py                # 최근 7일 정상 거래 Parquet 내보내기
│   └── run.py                     # 수집 파이프라인 CLI 실행기
├── analytics/
│   └── duckdb_client.py           # DuckDB 기반 인메모리 OLAP 집계 엔진
├── data/
│   ├── apt_sales.db               # SQLite 원본 거래 원장
│   └── apt_sales_recent.parquet   # 최근 1주일 정상 거래 압축 Parquet
├── tests/                         # 단위 및 통합 테스트
├── app.py                         # Streamlit 대시보드 웹 애플리케이션
├── pyproject.toml                 # uv 프로젝트 의존성 설정
└── README.md                      # 프로젝트 문서
```
