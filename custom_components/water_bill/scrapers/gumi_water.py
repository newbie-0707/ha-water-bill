import requests
from bs4 import BeautifulSoup
import logging

_LOGGER = logging.getLogger(__name__)

SCRAPER_NAME = "구미시 상수도사업소"

def get_rates():
    """구미시 요율표 HTML을 파싱하여 데이터를 구조화합니다."""
    url = "https://waterpay.gumi.go.kr/waterpay/ncoe/info/guide.do?guideId=calculationStandardTable&tab=1"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table', class_='table-sm')

        # 1. 상수도 요율 파싱 (첫 번째 테이블)
        water_table = tables[0].find('tbody')
        # 가정용은 첫 3개 행(tr)입니다. (rowspan="3")
        water_rows = water_table.find_all('tr')[:3]
        water_prices = []
        for row in water_rows:
            price_text = row.find_all('td')[-1].text.replace(',', '').strip()
            water_prices.append(int(price_text))

        # 2. 하수도 요율 파싱 (세 번째 테이블)
        sewer_table = tables[2].find('tbody')
        sewer_rows = sewer_table.find_all('tr')[:3]
        sewer_prices = []
        for row in sewer_rows:
            price_text = row.find_all('td')[-1].text.replace(',', '').strip()
            sewer_prices.append(int(price_text))

        # 3. 누진 단계 결합 (가정용 기준)
        tiers = [
            {"max": 20, "water": water_prices[0], "sewer": sewer_prices[0]},
            {"max": 30, "water": water_prices[1], "sewer": sewer_prices[1]},
            {"max": 999999, "water": water_prices[2], "sewer": sewer_prices[2]}
        ]

        # 4. 구경별 정액요금 (두 번째 테이블)
        base_fee_dict = {}
        base_fee_table = tables[1].find('tbody')
        for row in base_fee_table.find_all('tr'):
            tds = row.find_all('td')
            size = tds[0].text.strip() # 예: "13㎜"
            price = int(tds[1].text.replace(',', '').strip())
            base_fee_dict[size] = price

        # 5. 물이용부담금 (텍스트에서 추출)
        # "톤당 170원" 부분 파싱
        fund_tag = soup.find('h4', string=lambda x: x and '물이용부담금' in x)
        water_fund = 170 # 기본값
        if fund_tag:
            fund_text = fund_tag.find('small').text
            water_fund = int(''.join(filter(str.isdigit, fund_text)))

        return {
            "tiers": tiers,
            "base_fees": base_fee_dict, # 구경별 전체 딕셔너리 반환
            "water_fund": water_fund
        }

    except Exception as e:
        _LOGGER.error(f"구미시 스크래핑 실패: {e}")
        return None
