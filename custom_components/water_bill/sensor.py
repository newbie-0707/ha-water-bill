async def async_update(self):
        """핵심 요금 계산 로직"""
        state = self.hass.states.get(self._usage_sensor_id)
        if state is None or state.state in ["unknown", "unavailable"]:
            return

        try:
            current_usage = float(state.state)
        except ValueError:
            return

        # 1. 사용할 요율 데이터 결정 (스크래핑 데이터 우선)
        scraped_rates = self._entry.data.get("scraped_rates")
        if scraped_rates:
            # 딕셔너리가 중첩되어 있으므로 깊은 복사(copy)를 권장하지만 
            # 여기서는 원본 수정을 피하기 위해 dict(scraped_rates)를 사용합니다.
            rates = dict(scraped_rates)
        else:
            rates = dict(self._rates)

        # 2. 구경별 요금 처리 (정액제)
        if self._apply_fixed_rate:
            user_pipe_size = self._entry.data.get("pipe_size")
            base_fees = rates.get("base_fees", {})
            # 스크래핑된 구경 목록에서 요금을 찾아 base_fee로 할당
            rates['base_fee'] = base_fees.get(user_pipe_size, rates.get('base_fee', 0))

        # 3. 격월 검침 조정 (사용량 구간을 2배로 늘림)
        if self._billing_cycle == 2:
            adjusted_tiers = []
            for tier in rates.get('tiers', []):
                new_tier = dict(tier)
                if new_tier['max'] < 999999:
                    new_tier['max'] *= 2
                adjusted_tiers.append(new_tier)
            rates['tiers'] = adjusted_tiers

        # 4. 현재 요금 및 예상 요금 계산
        current_fee_info = calculate_water_fee(current_usage, rates, self._apply_fixed_rate)
        
        progress = get_billing_cycle_progress(self._reading_day)
        # 0으로 나누기 방지
        predicted_usage = current_usage / progress if progress > 0 else current_usage
        predicted_fee_info = calculate_water_fee(predicted_usage, rates, self._apply_fixed_rate)

        # 5. 전월 금액 갱신 (리셋 감지: 진척도가 줄어들었을 때)
        if progress < self._last_progress:
            self._last_month_bill = self._state
        self._last_progress = progress

        # 6. 상태 및 속성 업데이트
        self._state = current_fee_info['total']
        self._attrs = {
            "current_usage": current_usage,
            "predicted_usage": round(predicted_usage, 2),
            "predicted_total_fee": predicted_fee_info['total'],
            "last_month_bill": self._last_month_bill,
            "water_fee": current_fee_info['water'],
            "sewerage_fee": current_fee_info['sewer'],
            "water_fund": current_fee_info['fund'],
            "base_fee": current_fee_info['base'],
            "billing_progress": round(progress * 100, 1),
            "reading_day": self._reading_day,
            "billing_cycle": f"{self._billing_cycle}개월"
        }
