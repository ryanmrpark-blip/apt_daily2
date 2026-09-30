import hashlib
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AptDealRecord:
    deal_date: str          # YYYY-MM-DD
    sido: str               # e.g., 서울특별시
    sigungu: str            # e.g., 강남구
    dong: str               # e.g., 대치동
    apt_name: str           # e.g., 은마
    deal_amount: int        # 만원 단위 (e.g. 240000 = 24억원)
    exclusive_area: float   # 전용면적 (m^2)
    floor: int              # 층수
    build_year: int         # 건축년도
    cancel_deal_day: Optional[str] = None  # 해제사유발생일 (e.g., "2026-09-30" or None)
    deal_type: Optional[str] = "중개거래"   # 중개거래 / 직거래
    lawd_cd: Optional[str] = ""
    trade_id: str = field(init=False)
    pyeong: float = field(init=False)
    unit_price_pyeong: int = field(init=False)

    def __post_init__(self):
        # 1. 계산 필드: 평형 및 평당 단가
        self.pyeong = round(self.exclusive_area / 3.3, 1)
        if self.pyeong > 0:
            self.unit_price_pyeong = int(round(self.deal_amount / (self.exclusive_area / 3.3)))
        else:
            self.unit_price_pyeong = 0

        # 2. 고유 trade_id 해시 생성 (시군구+법정동+계약일자+단지명+전용면적+층+거래금액)
        key_str = f"{self.sido}_{self.sigungu}_{self.dong}_{self.deal_date}_{self.apt_name}_{self.exclusive_area:.2f}_{self.floor}_{self.deal_amount}"
        self.trade_id = hashlib.md5(key_str.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "trade_id": self.trade_id,
            "deal_date": self.deal_date,
            "sido": self.sido,
            "sigungu": self.sigungu,
            "dong": self.dong,
            "apt_name": self.apt_name,
            "deal_amount": self.deal_amount,
            "exclusive_area": self.exclusive_area,
            "pyeong": self.pyeong,
            "unit_price_pyeong": self.unit_price_pyeong,
            "floor": self.floor,
            "build_year": self.build_year,
            "cancel_deal_day": self.cancel_deal_day,
            "deal_type": self.deal_type,
            "lawd_cd": self.lawd_cd,
        }
