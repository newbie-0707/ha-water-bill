# custom_components/water_bill/__init__.py
import logging
import importlib
from datetime import timedelta
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval, async_track_time_notifier
import homeassistant.util.dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """통합구성요소 설정 및 스케줄링 등록"""
    
    async def update_rates_service(call: ServiceCall = None):
        """웹 스크래핑을 실행하여 요율을 갱신하는 내부 함수"""
        authority = entry.data.get("authority")
        if authority == "manual":
            _LOGGER.info("수동 설정 모드이므로 스크래핑을 건너뜁니다.")
            return

        _LOGGER.info(f"{authority} 요율 데이터 스크래핑 시작...")
        try:
            module = importlib.import_module(f".scrapers.{authority}", __package__)
            # executor_job을 써서 블로킹 함수인 requests를 안전하게 실행
            new_rates = await hass.async_add_executor_job(module.get_rates)
            
            if new_rates:
                # 갱신된 데이터를 entry에 업데이트 (메모리 및 config_entries.json 저장)
                hass.config_entries.async_update_entry(entry, data={**entry.data, "scraped_rates": new_rates})
                _LOGGER.info(f"{authority} 요율 갱신 완료")
                
                # 센서들에게 데이터가 변경되었음을 알림
                await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
        except Exception as e:
            _LOGGER.error(f"요율 업데이트 중 오류 발생: {e}")

    # 1. 홈어시스턴트 시작 시(또는 통합구성요소 로드 시) 즉시 실행
    hass.async_create_task(update_rates_service())

    # 2. 수동 갱신 서비스 등록 (설정 -> 기기 및 서비스 -> 수도요금 메뉴에서 버튼으로 노출됨)
    hass.services.async_register(DOMAIN, "update_rates", update_rates_service)

    # 3. 매주 월요일 오전 10시 스케줄링
    def schedule_monday_update(now):
        # 현재 요일(0:월 ~ 6:일)과 시간을 체크하여 다음 월요일 10시 예약
        hass.async_create_task(update_rates_service())

    # 매주 월요일 10:00:00에 실행되도록 시간 패턴 추적
    # 'day_of_week'는 지원되지 않을 수 있으므로, 매일 10시에 실행하여 월요일인지 체크하는 방식이 안전함
    async def nightly_check(now):
        if now.weekday() == 0: # 0은 월요일
            await update_rates_service()

    # 매일 오전 10시에 실행 시도
    async_track_time_interval(hass, nightly_check, timedelta(days=1), dt_util.parse_datetime(f"{dt_util.now().date()} 10:00:00"))

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, ["sensor"])
