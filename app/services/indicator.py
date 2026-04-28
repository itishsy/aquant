from __future__ import annotations


class IndicatorService:
    @staticmethod
    def calculate_ma(values: list[float], window: int) -> list[float | None]:
        result: list[float | None] = []
        for idx in range(len(values)):
            if idx + 1 < window:
                result.append(None)
            else:
                segment = values[idx + 1 - window : idx + 1]
                result.append(round(sum(segment) / window, 4))
        return result

    @staticmethod
    def calculate_ema(values: list[float], period: int) -> list[float]:
        multiplier = 2 / (period + 1)
        ema = [values[0]]
        for value in values[1:]:
            ema.append(round((value - ema[-1]) * multiplier + ema[-1], 6))
        return ema

    @classmethod
    def calculate_macd(
        cls, values: list[float], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> dict[str, list[float]]:
        ema_fast = cls.calculate_ema(values, fast)
        ema_slow = cls.calculate_ema(values, slow)
        dif = [round(a - b, 6) for a, b in zip(ema_fast, ema_slow)]
        dea = cls.calculate_ema(dif, signal)
        hist = [round((d - s) * 2, 6) for d, s in zip(dif, dea)]
        return {"dif": dif, "dea": dea, "hist": hist}

    @staticmethod
    def calculate_volume_change(values: list[float]) -> list[float]:
        result = [0.0]
        for prev, current in zip(values, values[1:]):
            if prev == 0:
                result.append(0.0)
            else:
                result.append(round((current - prev) / prev * 100, 2))
        return result
