import xml.etree.ElementTree as ET
import logging
import os
import requests
from typing import List, Optional
from collector.models import AptDealRecord

logger = logging.getLogger(__name__)

DEFAULT_MOLIT_API_URL = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"

def _get_tag_value(item: ET.Element, *tag_names) -> str:
    """주어진 태그명(한국어/영어) 후보 중 존재하는 첫 번째 태그의 텍스트 값을 반환합니다."""
    for tag in tag_names:
        el = item.find(tag)
        if el is not None and el.text:
            val = el.text.strip()
            if val:
                return val
    return ""

def parse_molit_xml_response(
    xml_content: str,
    sido: str,
    sigungu: str,
    lawd_cd: str
) -> List[AptDealRecord]:
    """공공데이터포털 국토교통부 아파트 매매 실거래가 XML 응답을 파싱합니다.
    (한글 태그 및 영문 태그 응답 모두 호환 지원)
    """
    records = []
    if not xml_content or not xml_content.strip():
        return records

    try:
        root = ET.fromstring(xml_content.strip())
    except ET.ParseError as e:
        logger.warning(f"XML parse error for {sido} {sigungu} ({lawd_cd}): {e}")
        return records

    items = root.findall(".//item")
    for item in items:
        try:
            # 1. 아파트 단지명 (한글: 아파트 / 영문: aptNm)
            apt_name = _get_tag_value(item, "aptNm", "아파트", "apt_name")
            if not apt_name:
                continue

            # 2. 거래금액 (한글: 거래금액 / 영문: dealAmount)
            deal_amount_raw = _get_tag_value(item, "dealAmount", "거래금액").replace(",", "").replace(" ", "")
            deal_amount = int(deal_amount_raw) if deal_amount_raw else 0
            if deal_amount <= 0:
                continue

            # 3. 계약일자 (한글: 년, 월, 일 / 영문: dealYear, dealMonth, dealDay)
            year_val = _get_tag_value(item, "dealYear", "년") or "2026"
            month_val = _get_tag_value(item, "dealMonth", "월") or "01"
            day_val = _get_tag_value(item, "dealDay", "일") or "01"

            year = year_val.strip()
            month = f"{int(month_val.strip()):02d}"
            day = f"{int(day_val.strip()):02d}"
            deal_date = f"{year}-{month}-{day}"

            # 4. 전용면적 (한글: 전용면적 / 영문: excluUseAr)
            area_val = _get_tag_value(item, "excluUseAr", "전용면적")
            exclusive_area = float(area_val) if area_val else 0.0

            # 5. 층 (한글: 층 / 영문: floor)
            floor_val = _get_tag_value(item, "floor", "층")
            floor = int(floor_val) if floor_val and floor_val.lstrip("-").isdigit() else 1

            # 6. 건축년도 (한글: 건축년도 / 영문: buildYear)
            build_val = _get_tag_value(item, "buildYear", "건축년도")
            build_year = int(build_val) if build_val and build_val.isdigit() else 2000

            # 7. 법정동 (한글: 법정동 / 영문: dong)
            dong = _get_tag_value(item, "dong", "법정동")

            # 8. 해제사유발생일 (한글: 해제사유발생일 / 영문: cdealDay)
            cancel_deal_day_val = _get_tag_value(item, "cdealDay", "해제사유발생일")
            cancel_deal_day = cancel_deal_day_val if cancel_deal_day_val else None

            # 9. 거래유형 (한글: 거래유형 / 영문: dealingGbn)
            deal_type_val = _get_tag_value(item, "dealingGbn", "거래유형")
            deal_type = deal_type_val if deal_type_val else "중개거래"

            rec = AptDealRecord(
                deal_date=deal_date,
                sido=sido,
                sigungu=sigungu,
                dong=dong,
                apt_name=apt_name,
                deal_amount=deal_amount,
                exclusive_area=exclusive_area,
                floor=floor,
                build_year=build_year,
                cancel_deal_day=cancel_deal_day,
                deal_type=deal_type,
                lawd_cd=lawd_cd
            )
            records.append(rec)
        except Exception as ex:
            logger.debug(f"Skipping item due to error: {ex}")
            continue

    return records

class MolitAptClient:
    def __init__(self, service_key: str, api_url: Optional[str] = None):
        self.service_key = service_key.strip()
        url = api_url or os.environ.get("MOLIT_API_URL") or DEFAULT_MOLIT_API_URL
        if not url.endswith("/getRTMSDataSvcAptTrade") and not url.endswith("/getRTMSDataSvcAptTradeDev"):
            url = url.rstrip("/") + "/getRTMSDataSvcAptTrade"
        self.api_url = url
        self.session = requests.Session()

    def fetch_district_month(
        self,
        lawd_cd: str,
        deal_ymd: str,
        sido: str = "",
        sigungu: str = "",
        page_no: int = 1,
        num_of_rows: int = 1000,
        timeout: int = 15
    ) -> List[AptDealRecord]:
        """특정 시군구의 특정 월(YYYYMM) 실거래 데이터를 조회합니다."""
        if not self.service_key:
            logger.warning("Service key is empty.")
            return []

        import urllib.parse
        service_key = urllib.parse.unquote(self.service_key)

        params = {
            "serviceKey": service_key,
            "LAWD_CD": str(lawd_cd),
            "DEAL_YMD": str(deal_ymd),
            "pageNo": page_no,
            "numOfRows": num_of_rows
        }

        try:
            resp = self.session.get(self.api_url, params=params, timeout=timeout)
            resp.raise_for_status()

            # 응답 내 에러 메시지 체크 (공공데이터포털 공통 에러 응답)
            if "<returnAuthMsg>" in resp.text:
                logger.warning(f"MOLIT API Auth Error ({lawd_cd}, {deal_ymd}): {resp.text[:200]}")
                # 혹시 unquote되지 않은 원본 키로 재시도
                if service_key != self.service_key:
                    params["serviceKey"] = self.service_key
                    resp2 = self.session.get(self.api_url, params=params, timeout=timeout)
                    if "<returnAuthMsg>" not in resp2.text:
                        return parse_molit_xml_response(resp2.text, sido=sido, sigungu=sigungu, lawd_cd=lawd_cd)
                return []
            elif "<errMsg>" in resp.text:
                logger.warning(f"MOLIT API Error ({lawd_cd}, {deal_ymd}): {resp.text[:200]}")
                return []

            return parse_molit_xml_response(resp.text, sido=sido, sigungu=sigungu, lawd_cd=lawd_cd)
        except Exception as e:
            logger.error(f"Error fetching MOLIT API ({lawd_cd}, {deal_ymd}) at {self.api_url}: {e}")
            return []

