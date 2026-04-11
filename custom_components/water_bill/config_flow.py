import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import DOMAIN
from .scraper import get_scraper_instance # 스크래퍼 인스턴스 가져오는 함수 가정

class WaterBillConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self.init_data = {}

    async def async_step_user(self, user_input=None):
        """1단계: 공급사 선택"""
        if user_input is not None:
            self.init_data.update(user_input)
            # 공급사를 선택했으므로 상세 설정 단계로 이동
            return await self.async_step_details()

        # scraper 폴더의 목록을 가져오는 함수 (기존 구현 사용)
        scraper_list = await self.hass.async_add_executor_job(get_all_scrapers)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("authority"): vol.In(scraper_list),
            })
        )

    async def async_step_details(self, user_input=None):
        """2단계: 스크래퍼 데이터를 기반으로 동적 목록 표시"""
        errors = {}
        authority = self.init_data.get("authority")

        # 1. 해당 공급사의 스크래퍼 실행해서 목록 가져오기
        try:
            scraper = get_scraper_instance(authority)
            # 스크래퍼 내부의 목록 정보를 가져오는 메서드 호출 (가정)
            usage_options = await self.hass.async_add_executor_job(scraper.get_usage_types)
            pipe_options = await self.hass.async_add_executor_job(scraper.get_pipe_sizes)
            
            # '정액요금 미사용' 옵션을 리스트 맨 앞에 추가
            pipe_options = {"none": "정액요금 미적용 (기본값)", **pipe_options}
            
        except Exception as e:
            return self.async_abort(reason="cannot_connect")

        if user_input is not None:
            # 최종 데이터 병합 및 엔트리 생성
            final_config = {**self.init_data, **user_input}
            return self.async_create_entry(
                title=f"수도 요금 ({authority})",
                data=final_config
            )

        # 2. 동적으로 생성된 목록으로 스키마 구성
        return self.async_show_form(
            step_id="details",
            data_schema=vol.Schema({
                vol.Required("usage_type"): vol.In(usage_options),
                vol.Required("pipe_size", default="none"): vol.In(pipe_options),
                vol.Required("usage_sensor"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor", device_class="water")
                ),
                vol.Required("reading_day", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=31)),
            }),
            errors=errors
        )
