from apscheduler.schedulers.background import BackgroundScheduler


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    return scheduler
