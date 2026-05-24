from datetime import datetime

from app.models import ConfigTask
from app.services.kline_collection import KlineCollectionService
from app.services.prd_v1 import SeedService
from app.services.tasks import TaskService


class CountingProvider:
    def __init__(self):
        self.intraday_calls = []

    def get_intraday_kline(self, stock_code, interval, start_time, end_time):
        self.intraday_calls.append((stock_code, interval))
        return [
            {
                "trade_time": end_time,
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "volume": 1000,
                "source": "test",
            }
        ]


def test_disabled_task_does_not_execute(db_session):
    SeedService(db_session).init_defaults()
    task = db_session.query(ConfigTask).filter(ConfigTask.task_name == "prepare_watch_kline_data").first()
    task.enabled = False
    db_session.commit()

    log = TaskService(db_session).prepare_watch_kline_data(datetime(2026, 5, 24).date())

    assert log.run_status == "skipped"
    assert log.affected_rows == 0
    assert log.error_message == "task is disabled"


def test_run_window_outside_does_not_execute_collection(db_session):
    SeedService(db_session).init_defaults()
    task = db_session.query(ConfigTask).filter(ConfigTask.task_name == "prepare_watch_kline_data").first()
    task.config_json = {"run_window": "00:00-00:01"}
    db_session.commit()

    log = TaskService(db_session).prepare_watch_kline_data(datetime(2026, 5, 24).date())

    assert log.run_status == "skipped"
    assert log.affected_rows == 0
    assert "outside run_window" in log.error_message


def test_kline_collection_respects_max_requests_per_run(db_session):
    provider = CountingProvider()
    service = KlineCollectionService(
        db_session,
        provider=provider,
        now=datetime(2026, 5, 22, 10, 17),
        max_requests_per_run=1,
    )

    affected = service.collect_for_requirements(
        {
            "000001.SZ": {"5m": {"timeframe": "5m", "lookback_bars": 10, "indicators": [], "reasons": ["r1"]}},
            "000002.SZ": {"5m": {"timeframe": "5m", "lookback_bars": 10, "indicators": [], "reasons": ["r2"]}},
        }
    )

    assert affected == 1
    assert len(provider.intraday_calls) == 1
    assert service.error_summary() == "max_requests_per_run reached"


def test_admin_task_config_can_be_updated(client, db_session):
    SeedService(db_session).init_defaults()
    task = db_session.query(ConfigTask).filter(ConfigTask.task_name == "prepare_watch_kline_data").first()

    response = client.put(
        f"/api/admin/tasks/{task.task_id}",
        json={"config_json": {"interval_minutes": 5, "run_window": "09:30-15:05", "max_requests_per_run": 20}},
    )

    assert response.status_code == 200
    db_session.refresh(task)
    assert task.config_json["run_window"] == "09:30-15:05"
    assert task.config_json["max_requests_per_run"] == 20
