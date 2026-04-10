"""수도 요금 계산 통합구성요소를 위한 상수 정의"""

import logging

# 통합구성요소의 도메인 이름 (manifest.json의 domain과 일치해야 함)
DOMAIN = "water_bill"

# 로거 설정
_LOGGER = logging.getLogger(__package__)

# 플랫폼 설정
PLATFORMS = ["sensor"]

# 설정 시 사용할 키 (Config Entry Keys)
CONF_AUTHORITY = "authority"
CONF_USAGE_TYPE = "usage_type"
CONF_USAGE_SENSOR = "usage_sensor"
CONF_READING_DAY = "reading_day"
CONF_BILLING_CYCLE = "billing_cycle"
CONF_APPLY_FIXED_RATE = "apply_fixed_rate"
CONF_PIPE_SIZE = "pipe_size"

# 스크래핑된 요율 데이터를 저장할 키
CONF_SCRAPED_RATES = "scraped_rates"
CONF_MANUAL_RATES = "manual_rates"

# 기본값 설정
DEFAULT_NAME = "수도 요금"
