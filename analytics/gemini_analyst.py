import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class GeminiAnalyst:
    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-3.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
        self.model = model
        self._client = None

    @property
    def client(self):
        if self._client is None and self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Failed to initialize Google GenAI Client: {e}")
        return self._client

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def _prepare_prompt(self, deal_date: str, deals: List[Dict[str, Any]]) -> str:
        """거래 데이터를 애널리스트 분석용 구조화 텍스트로 가공합니다."""
        if not deals:
            return ""

        total_count = len(deals)
        amounts = [d["deal_amount"] for d in deals if d.get("deal_amount")]
        avg_amount = int(sum(amounts) / len(amounts)) if amounts else 0
        max_deal = max(deals, key=lambda x: x.get("deal_amount", 0))

        # 시도별 집계
        sido_counts = {}
        for d in deals:
            s = d.get("sido", "기타")
            sido_counts[s] = sido_counts.get(s, 0) + 1
        sorted_sido = sorted(sido_counts.items(), key=lambda x: x[1], reverse=True)

        # 상위 5건 최고가 거래
        top_deals = sorted(deals, key=lambda x: x.get("deal_amount", 0), reverse=True)[:5]
        top_deals_text = "\n".join([
            f"- **{d.get('apt_name')}** ({d.get('sido')} {d.get('sigungu')} {d.get('dong')}, {d.get('floor')}층) : "
            f"**{d.get('deal_amount', 0):,}만원** ({d.get('exclusive_area', 0)}㎡ / 약 {d.get('pyeong', 0)}평) "
            f"[평당 {d.get('unit_price_pyeong', 0):,}만원]"
            for d in top_deals
        ])

        # 가격대별 분포
        under_3 = sum(1 for a in amounts if a < 30000)
        from_3_to_6 = sum(1 for a in amounts if 30000 <= a < 60000)
        from_6_to_9 = sum(1 for a in amounts if 60000 <= a < 90000)
        from_9_to_15 = sum(1 for a in amounts if 90000 <= a < 150000)
        over_15 = sum(1 for a in amounts if a >= 150000)

        prompt = f"""
당신은 대한민국 최고 권위의 15년 경력 부동산 수석 애널리스트(Chief Real Estate Analyst)입니다.
아래의 {deal_date} 당일 국토교통부 실제 아파트 매매 실거래가 데이터를 면밀히 검토하고, 기관 투자자와 스마트 실수요자를 위한 수준 높고 통찰력 넘치는 '일일 부동산 마켓 브리핑 리포트'를 작성해 주세요.

---
### 📊 {deal_date} 당일 거래 데이터 요약
* **총 유효 거래 건수**: {total_count:,}건
* **당일 평균 거래금액**: {avg_amount:,}만원 ({avg_amount / 10000:.1f}억원)
* **당일 최고가 단지**: {max_deal.get('apt_name')} ({max_deal.get('sido')} {max_deal.get('sigungu')}, {max_deal.get('exclusive_area')}㎡) - **{max_deal.get('deal_amount', 0):,}만원** ({max_deal.get('deal_amount', 0) / 10000:.1f}억원)
* **시도별 거래량 상위**: {', '.join([f'{s}({c}건)' for s, c in sorted_sido[:5]])}
* **가격대별 분포**: 3억 미만 {under_3}건, 3~6억 {from_3_to_6}건, 6~9억 {from_6_to_9}건, 9~15억 {from_9_to_15}건, 15억 이상 초고가 {over_15}건

### 🏆 당일 최고가 거래 Top 5
{top_deals_text}
---

### ✍️ 작성 가이드라인 (반드시 아래 소제목 구조를 준수하세요)
1. **📌 마켓 총평 & 수급 심리 진단**: 당일 거래량과 평균 가격대를 통해 본 시장의 활성도 및 매수세 관망/유입 진단
2. **💎 오늘의 랜드마크 & 최고가 단지 심층 브리핑**: 최고가 단지의 입지 상징성, 평당가 수준, 고가 거래가 주는 시장 신호 분석
3. **🗺️ 권역별 쏠림 & 선호 평형 트렌드**: 거래가 집중된 주요 시도/시군구 및 가격대별 비중 분석
4. **🎯 수석 애널리스트의 제언 (실수요자 & 투자자 관점)**: 현재 시장 상황에서 내 집 마련 실수요자 및 갈아타기 수요자가 취해야 할 구체적인 포지셔닝 제언

* 문체: 단정하면서도 전문적인 비즈니스 리포트 문체 (~입니다, ~로 풀이됩니다, ~에 주목할 필요가 있습니다).
* 시각성: 적절한 볼드체, 불릿 포인트, 핵심 강조 문구를 활용하여 가독성을 극대화하세요.
"""
        return prompt.strip()

    def generate_daily_analysis(
        self,
        deal_date: str,
        deals: List[Dict[str, Any]]
    ) -> str:
        """Gemini API를 호출하여 일자별 부동산 애널리스트 리포트를 생성합니다."""
        if not self.is_available():
            raise ValueError("GEMINI_API_KEY가 설정되지 않았거나 유효하지 않습니다.")

        if not deals:
            return f"⚠️ {deal_date}에는 등록된 실거래 데이터가 없어 분석을 생성할 수 없습니다."

        prompt = self._prepare_prompt(deal_date, deals)

        candidate_models = [self.model, "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
        # 중복 제거 유지
        seen = set()
        models_to_try = [m for m in candidate_models if not (m in seen or seen.add(m))]

        client = self.client
        if not client:
            raise RuntimeError("Google GenAI 클라이언트를 생성할 수 없습니다.")

        last_error = None
        for m in models_to_try:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=prompt
                )
                self.model = m
                return response.text.strip()
            except Exception as e:
                last_error = e
                logger.warning(f"Model {m} failed: {e}. Trying next fallback...")
                continue

        logger.error(f"All Gemini models failed: {last_error}")
        raise RuntimeError(f"Gemini API 분석 생성 실패: {str(last_error)}")
