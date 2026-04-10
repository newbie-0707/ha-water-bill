import logging
from datetime import timedelta
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up water_bill from a config entry."""
    
    # 요율 업데이트 서비스 등록 (예시)
    async def update_rates_service(call):
        _LOGGER.info("수도 요금 요율 업데이트 서비스가 호출되었습니다.")

    hass.services.async_register(DOMAIN, "update_rates", update_rates_service)

    # 매일 1회 실행되는 타이머 설정 (오류 수정됨)
    entry.async_on_unload(
        async_track_time_interval(
            hass, 
            update_rates_service, 
            timedelta(hours=24)
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
