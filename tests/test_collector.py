import pytest
from collector.client import parse_molit_xml_response, MolitAptClient, DEFAULT_MOLIT_API_URL

SAMPLE_XML_ENGLISH = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <dealAmount> 150,000</dealAmount>
        <buildYear>2012</buildYear>
        <dealYear>2026</dealYear>
        <dealMonth>9</dealMonth>
        <dealDay>28</dealDay>
        <dong>반포동</dong>
        <aptNm>래미안퍼스티지</aptNm>
        <excluUseAr>84.93</excluUseAr>
        <floor>12</floor>
        <cdealDay> </cdealDay>
        <dealingGbn>중개거래</dealingGbn>
        <sggCd>11650</sggCd>
      </item>
    </items>
    <numOfRows>1000</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>1</totalCount>
  </body>
</response>
"""

SAMPLE_XML_KOREAN = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE.</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <거래금액> 230,000</거래금액>
        <건축년도>1983</건축년도>
        <년>2026</년>
        <월>9</월>
        <일>27</일>
        <법정동>개포동</법정동>
        <아파트>개포주공1단지</아파트>
        <전용면적>84.95</전용면적>
        <층>7</층>
        <해제사유발생일>26.09.28</해제사유발생일>
        <거래유형>중개거래</거래유형>
      </item>
    </items>
    <numOfRows>1000</numOfRows>
    <pageNo>1</pageNo>
    <totalCount>1</totalCount>
  </body>
</response>
"""

def test_parse_molit_xml_english_response():
    records = parse_molit_xml_response(
        xml_content=SAMPLE_XML_ENGLISH,
        sido="서울특별시",
        sigungu="서초구",
        lawd_cd="11650"
    )
    assert len(records) == 1
    r = records[0]
    assert r.apt_name == "래미안퍼스티지"
    assert r.deal_amount == 150000
    assert r.deal_date == "2026-09-28"
    assert r.exclusive_area == 84.93
    assert r.floor == 12
    assert r.cancel_deal_day is None

def test_parse_molit_xml_korean_response():
    records = parse_molit_xml_response(
        xml_content=SAMPLE_XML_KOREAN,
        sido="서울특별시",
        sigungu="강남구",
        lawd_cd="11680"
    )
    assert len(records) == 1
    r = records[0]
    assert r.apt_name == "개포주공1단지"
    assert r.deal_amount == 230000
    assert r.deal_date == "2026-09-27"
    assert r.exclusive_area == 84.95
    assert r.floor == 7
    assert r.build_year == 1983
    assert r.cancel_deal_day == "26.09.28"

def test_client_endpoint_url():
    client = MolitAptClient(service_key="test_key")
    assert client.api_url == "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"

    client2 = MolitAptClient(service_key="test_key", api_url="https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade")
    assert client2.api_url == "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
