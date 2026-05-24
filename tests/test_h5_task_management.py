from datetime import datetime

from app.models import ConfigTask, ConfigTaskLog
from app.services.prd_v1 import SeedService


def test_h5_my_tasks_include_execution_plan_and_latest_run(client, db_session):
    SeedService(db_session).init_defaults()
    task = db_session.query(ConfigTask).filter(ConfigTask.task_name == "collect_market_daily").first()
    db_session.add(
        ConfigTaskLog(
            task_id=task.task_id,
            task_name=task.task_name,
            run_status="success",
            started_at=datetime(2026, 5, 22, 18, 0, 0),
            finished_at=datetime(2026, 5, 22, 18, 3, 0),
            affected_rows=12,
        )
    )
    db_session.commit()

    response = client.get("/api/h5/me/tasks")

    assert response.status_code == 200
    tasks = response.json()["data"]["tasks"]
    row = next(item for item in tasks if item["task_name"] == "collect_market_daily")
    assert row["task_label"] == "大盘数据采集"
    assert row["execution_plan"] == "每日18点"
    assert row["latest_log"]["run_status"] == "success"
    assert row["latest_log"]["started_at"].startswith("2026-05-22")
