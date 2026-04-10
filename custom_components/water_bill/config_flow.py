import os
import importlib
import importlib.util
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

def sync_get_scraper_list():
    """파일 시스템에 접근하는 동기 함수 (별도 스레드에서 실행될 것)"""
    scraper_dir = os.path.join(os.path.dirname(__file__), "scrapers")
    options = {}

    if os.path.exists(scraper_dir):
        for filename in os.listdir(scraper_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                file_path = os.path.join(scraper_dir, filename)
                try:
                    # 이 부분이 블로킹 호출이므로 executor에서 실행되어야 함
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    friendly_name = getattr(module, "SCRAPER_NAME", module_name.capitalize())
                    options[module_name] = friendly_name
                except Exception:
                    options[module_name] = module_name.capitalize()

    options["manual"] = "직접 입력(수동 설정)"
    return options

class WaterBillConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """데이터 임시 저장을 위한 초기화"""
        self.init_data = {}

    async def async_step_user(self, user_input=None):
        """1단계: 기본 정보 설정"""
        if user_input is not None:
            self.init_data = user_input
            
            # 1. 수동 입력을 선택한 경우
            if user_input["authority"] == "manual":
                return await self.async_step_manual()
            
            # 2. 지자체 스크래퍼를 선택했고 정액제 적용을 체크한 경우
            if user_input.get("apply_fixed_rate"):
                return await self.async_step_pipe()
            
            # 3. 그 외 (스크래퍼 선택 + 정액제 미사용)
            return self.async_create_entry(
                title=f"수도요금 ({user_input['authority']})", 
                data=self.init_data
            )

        scraper_options = await self.hass.async_add_executor_job(sync_get_scraper_list)
        
        DATA_SCHEMA = vol.Schema({
            vol.Required("authority"): vol.In(scraper_options),
            vol.Required("usage_type", default="domestic"): vol.In({
                "domestic": "가정용",
                "commercial": "일반용",
                "industrial": "산업용"
            }),
            vol.Required("usage_sensor"): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", device_class="water")
            ),
            vol.Required("reading_day", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=31)),
            vol.Required("billing_cycle", default=1): vol.In({1: "매달", 2: "격월"}),
            vol.Required("apply_fixed_rate", default=True): bool,
        })

        return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

    async def async_step_pipe(self, user_input=None):
        """2단계 (분기A): 스크래퍼 기반 구경 선택 단계"""
        errors = {}
        authority = self.init_data.get["authority"]

        if user_input is not None:
            # 기존 데이터와 새 데이터를 통합
            final_data = {**self.init_data, **user_input}
            return self.async_create_entry(
                title=f"수도요금 ({authority})", 
                data=final_data
        try:
            # 상대 경로 임포트 문제 방지를 위해 importlib 사용
            module = importlib.import_module(f"custom_components.{DOMAIN}.scrapers.{authority}")
            rates = await self.hass.async_add_executor_job(module.get_rates)
            pipe_options = list(rates.get("base_fees", {}).keys())
            
            if not pipe_options:
                pipe_options = ["기본(단일 요율)"]
        except Exception:
            pipe_options = ["13㎜", "20㎜", "25㎜"]


        return self.async_show_form(
            step_id="pipe",
            data_schema=vol.Schema({
                vol.Required("pipe_size", default=pipe_options[0]): vol.In(pipe_options)
            }),
            errors=errors
        )

    async def async_step_manual(self, user_input=None):
        """2단계 (분기B): 수동 요율 입력 단계"""
        if user_input is not None:
            processed_rates = self._process_manual_input(user_input)
            self.init_data.update({"manual_rates": processed_rates})
            
            return self.async_create_entry(
                title="수도요금 (수동 설정)", 
                data=self.init_data
            )

        MANUAL_SCHEMA = vol.Schema({
            vol.Required("base_fee", default=0): int,
            vol.Required("water_fund_rate", default=170.0): float,
            vol.Required("t1_max", default=20): int,
            vol.Required("t1_water", default=510): int,
            vol.Required("t1_sewer", default=380): int,
            vol.Optional("t2_max"): int,
            vol.Optional("t2_water"): int,
            vol.Optional("t2_sewer"): int,
            vol.Optional("t3_max"): int,
            vol.Optional("t3_water"): int,
            vol.Optional("t3_sewer"): int,
        })

        return self.async_show_form(step_id="manual", data_schema=MANUAL_SCHEMA)

    def _process_manual_input(self, user_input):
        """수동 입력 데이터 구조화"""
        tiers = []
        for i in range(1, 4):  # 예시로 3단계까지 처리
            w_rate = user_input.get(f"t{i}_water")
            s_rate = user_input.get(f"t{i}_sewer")
            t_max = user_input.get(f"t{i}_max", 999999)
            
            if w_rate is not None and s_rate is not None:
                tiers.append({"max": t_max, "water": w_rate, "sewer": s_rate})
        
        return {
            "base_fee": user_input.get("base_fee"),
            "water_fund": user_input.get("water_fund_rate"),
            "tiers": tiers
        }
