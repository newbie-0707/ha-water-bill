import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval
import homeassistant.util.dt as dt_util

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """통합구성요소 설정"""
    
    async def update_rates_service(call=None):
        """요율 업데이트 서비스 (수동/자동 공용)"""
        _LOGGER.info("수도 요금 요율 업데이트를 시작합니다.")
        # 여기에 나중에 실제 스크래핑 호출 로직이 추가됩니다.

    # 서비스 등록
    hass.services.async_register(DOMAIN, "update_rates", update_rates_service)

    # 매일 오전 10시에 체크하여 월요일이면 실행
    async def nightly_check(now):
        if now.weekday() == 0:  # 0: 월요일
            await update_rates_service()

    # 매일 1회 체크 실행 (간결하게 timedelta 사용)
    entry.async_on_unload(
        async_track_time_interval(hass, nightly_check, timedelta(days=1))
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """통합구성요소 제거"""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
