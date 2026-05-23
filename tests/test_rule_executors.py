from datetime import date

from app.rule_executors import RuleContext, get_executor, list_executors


def test_registry_finds_always_false_executor():
    assert "always_false" in list_executors()
    executor = get_executor("always_false")
    assert executor is not None

    result = executor.execute(
        RuleContext(
            watch_id=1,
            stock_code="000001.SZ",
            stock_name="平安银行",
            trading_system_code="platform_breakout",
            stage="observe",
            system_params={"platform_upper_price": 12.5},
            rule_config={
                "rule_code": "test_rule",
                "rule_name": "测试规则",
                "rule_type": "filter",
            },
            trade_date=date(2026, 5, 23),
            latest_price=12.3,
        )
    )

    assert result.triggered is False
    assert result.rule_code == "test_rule"
    assert result.rule_name == "测试规则"
    assert result.rule_type == "filter"
    assert result.trigger_price == 12.3
    assert result.snapshot["executor_key"] == "always_false"
