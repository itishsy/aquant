# 真实数据采集启动说明

## 手动采集

设置真实数据模式：

```powershell
$env:DATA_PROVIDER_MODE="real"
$env:DATABASE_URL="mysql+pymysql://aquant:Hsy%40841121@8.148.181.1:3306/a_quant?charset=utf8mb4"
$env:CANDLE_DATABASE_URL="mysql+pymysql://aquant:Hsy%40841121@8.148.181.1:3306/a_candle?charset=utf8mb4"
```

启动后端后触发当日采集：

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/admin/tasks/generate_daily_snapshot_task/run?provider_mode=real" `
  -Headers @{ "X-Admin-Token" = "dev-admin-token" }
```

补采指定日期。接口会拒绝未来日期，避免误采明天数据：

```powershell
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/api/admin/tasks/generate_daily_snapshot_task/run?trade_date=2026-04-30&provider_mode=real" `
  -Headers @{ "X-Admin-Token" = "dev-admin-token" }
```

## 每日定时采集

显式开启每日一次采集：

```powershell
$env:DATA_PROVIDER_MODE="real"
$env:ENABLE_SCHEDULER="true"
$env:DAILY_COLLECTION_HOUR="16"
$env:DAILY_COLLECTION_MINUTE="10"
$env:TIMEZONE="Asia/Shanghai"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

默认每天 16:10 触发 `generate_daily_snapshot_task`，采集市场行情、热门板块、热榜、涨停榜和市场复盘快照。系统仅做行情监测和交易辅助，请结合个人交易计划确认。
