import json
import random
import pathlib
from datetime import datetime, timedelta
from typing import List
from collector.models import AptDealRecord

APT_SAMPLES = [
    # 서울
    {"sido": "서울특별시", "sigungu": "강남구", "dong": "압구정동", "apt": "현대1차", "build": 1976, "min_p": 380000, "max_p": 650000, "areas": [84.9, 131.2, 160.2]},
    {"sido": "서울특별시", "sigungu": "강남구", "dong": "대치동", "apt": "은마", "build": 1979, "min_p": 220000, "max_p": 270000, "areas": [76.79, 84.43]},
    {"sido": "서울특별시", "sigungu": "서초구", "dong": "반포동", "apt": "아크로리버파크", "build": 2016, "min_p": 360000, "max_p": 500000, "areas": [59.9, 84.95, 112.9]},
    {"sido": "서울특별시", "sigungu": "송파구", "dong": "잠실동", "apt": "잠실엘스", "build": 2008, "min_p": 210000, "max_p": 270000, "areas": [59.96, 84.8, 119.93]},
    {"sido": "서울특별시", "sigungu": "마포구", "dong": "아현동", "apt": "마포래미안푸르지오", "build": 2014, "min_p": 160000, "max_p": 200000, "areas": [59.92, 84.59, 114.7]},
    {"sido": "서울특별시", "sigungu": "노원구", "dong": "상계동", "apt": "상계주공7단지", "build": 1988, "min_p": 60000, "max_p": 90000, "areas": [45.9, 59.39, 79.07]},
    
    # 경기
    {"sido": "경기도", "sigungu": "성남시 분당구", "dong": "백현동", "apt": "판교푸르지오그랑블", "build": 2011, "min_p": 230000, "max_p": 320000, "areas": [98.9, 105.1, 130.5]},
    {"sido": "경기도", "sigungu": "과천시", "dong": "원문동", "apt": "과천위버필드", "build": 2021, "min_p": 170000, "max_p": 220000, "areas": [59.9, 84.98]},
    {"sido": "경기도", "sigungu": "수원시 영통구", "dong": "이의동", "apt": "광교중흥S-클래스", "build": 2019, "min_p": 130000, "max_p": 170000, "areas": [84.9, 109.1]},
    {"sido": "경기도", "sigungu": "하남시", "dong": "망월동", "apt": "미사강변골든센트로", "build": 2014, "min_p": 90000, "max_p": 120000, "areas": [59.9, 84.7]},
    {"sido": "경기도", "sigungu": "화성시", "dong": "오산동", "apt": "동탄역롯데캐슬", "build": 2021, "min_p": 140000, "max_p": 175000, "areas": [65.9, 84.9, 102.3]},

    # 인천
    {"sido": "인천광역시", "sigungu": "연수구", "dong": "송도동", "apt": "송도더샵퍼스트파크", "build": 2017, "min_p": 75000, "max_p": 110000, "areas": [59.9, 84.9, 108.2]},
    {"sido": "인천광역시", "sigungu": "서구", "dong": "청라동", "apt": "청라국제금융단지한양수자인", "build": 2019, "min_p": 60000, "max_p": 85000, "areas": [84.9]},

    # 부산
    {"sido": "부산광역시", "sigungu": "해운대구", "dong": "우동", "apt": "해운대아이파크", "build": 2011, "min_p": 120000, "max_p": 250000, "areas": [84.9, 118.4, 163.5]},
    {"sido": "부산광역시", "sigungu": "수영구", "dong": "남천동", "apt": "삼익비치", "build": 1979, "min_p": 90000, "max_p": 160000, "areas": [61.2, 84.8, 131.1]},

    # 대구
    {"sido": "대구광역시", "sigungu": "수성구", "dong": "범어동", "apt": "두산위브더제니스", "build": 2009, "min_p": 130000, "max_p": 220000, "areas": [129.5, 143.9]},

    # 대전
    {"sido": "대전광역시", "sigungu": "유성구", "dong": "도룡동", "apt": "도룡SK뷰", "build": 2018, "min_p": 95000, "max_p": 140000, "areas": [84.9, 116.5]},

    # 광주
    {"sido": "광주광역시", "sigungu": "남구", "dong": "봉선동", "apt": "봉선한국아델리움3차", "build": 2014, "min_p": 70000, "max_p": 110000, "areas": [84.9]},

    # 세종
    {"sido": "세종특별자치시", "sigungu": "세종시", "dong": "새롬동", "apt": "새뜸마을1단지", "build": 2017, "min_p": 65000, "max_p": 95000, "areas": [59.9, 84.9]},
]

def generate_mock_records(days: int = 7, count_per_day: int = 30) -> List[AptDealRecord]:
    """오늘 기준 과거 N일간의 현실적인 전국 아파트 모의 실거래 데이터를 생성합니다."""
    today = datetime.now().date()
    records = []
    
    # lawd_cd 로드 시도
    lawd_map = {}
    lawd_path = pathlib.Path(__file__).parent / "lawd_cd.json"
    if lawd_path.exists():
        with open(lawd_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                key = f"{item['sido']}_{item['sigungu']}"
                lawd_map[key] = item["code"]

    for d in range(days):
        deal_date = (today - timedelta(days=d)).strftime("%Y-%m-%d")
        daily_count = random.randint(int(count_per_day * 0.7), int(count_per_day * 1.3))
        
        for _ in range(daily_count):
            sample = random.choice(APT_SAMPLES)
            area = random.choice(sample["areas"])
            # 면적 비율에 따른 거래 가격 스케일링
            base_p = random.randint(sample["min_p"], sample["max_p"])
            floor = random.randint(1, 35)
            
            # 3% 확률로 취소 거래 생성
            is_cancelled = random.random() < 0.03
            cancel_day = deal_date if is_cancelled else None
            
            lawd_code = lawd_map.get(f"{sample['sido']}_{sample['sigungu']}", "11110")
            
            rec = AptDealRecord(
                deal_date=deal_date,
                sido=sample["sido"],
                sigungu=sample["sigungu"],
                dong=sample["dong"],
                apt_name=sample["apt"],
                deal_amount=base_p,
                exclusive_area=area,
                floor=floor,
                build_year=sample["build"],
                cancel_deal_day=cancel_day,
                deal_type="중개거래" if random.random() > 0.1 else "직거래",
                lawd_cd=lawd_code
            )
            records.append(rec)
            
    return records
