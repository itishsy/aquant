from datetime import date

from app.models import ConfigTask, WatchPool
from app.services.prd_v1 import SeedService
from app.tasks.scheduler import build_scheduler


def test_seed_includes_kline_prepare_tasks(db_session):
    SeedService(db_session).init_defaults()

    tasks = {
        row.task_name: row.owner_module
        for row in db_session.query(ConfigTask)
        .filter(ConfigTask.task_name.in_(["prepare_watch_kline_data", "prepare_trade_kline_data"]))
        .all()
    }

    assert tasks == {
        "prepare_watch_kline_data": "kline",
        "prepare_trade_kline_data": "kline",
    }


def test_admin_can_run_prepare_watch_kline_data(client, db_session):
    SeedService(db_session).init_defaults()
    db_session.add(
        WatchPool(
            stock_code="603019.SH",
            stock_name="Test Stock",
            active=True,
            status="watching",
            system_stage="observe",
            monitor_enabled=True,
            signal_enabled=True,
            trading_system_code="breakout",
            trading_system="breakout",
        )
    )
    db_session.commit()
    task = db_session.query(ConfigTask).filter(ConfigTask.task_name == "prepare_watch_kline_data").first()

    response = client.post(f"/api/admin/tasks/{task.task_id}/run")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["task_name"] == "prepare_watch_kline_data"
    assert payload["run_status"] == "success"
    assert payload["affected_rows"] >= 0


def test_scheduler_registers_kline_prepare_jobs():
    scheduler = build_scheduler()

    watch_job = scheduler.get_job("prepare_watch_kline_data")
    trade_job = scheduler.get_job("prepare_trade_kline_data")

    assert watch_job is not None
    assert trade_job is not None
    assert watch_job.trigger.interval.total_seconds() == 300
    assert trade_job.trigger.interval.total_seconds() == 300
