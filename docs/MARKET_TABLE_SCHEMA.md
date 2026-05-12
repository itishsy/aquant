# Aquant 市场数据表结构

本文档说明当前市场数据相关表。市场模块只保存客观原始数据和来源信息，不保存主观评分，不自动入池，不生成交易建议。

## 设计原则

- `mkt_daily` 保存每日大盘概览、三大指数、涨跌家数、成交额等日级市场主数据。
- 财联社“今日机会”“今日风口”和同花顺“话题热榜”拆分为独立结构化表，不再存入 `mkt_daily` JSON 字段。
- 财联社涨停分析接口拆分为涨停个股表和涨停板块表。涨停梯度不再单独建表，由 `mkt_limit_up_stock.ladder_height` 或 `board_count` 统计得出。
- 股票代码统一使用 `600000.SH`、`000001.SZ`、`430000.BJ` 格式，同时在 `raw_secu_code` 保留来源原始代码。
- 所有外部来源数据保留 `source`、`platform`、`source_update_time`、`collected_at`，便于追溯。

## 表关系概览

| 模块 | 主表 | 明细表 | 说明 |
|---|---|---|---|
| 大盘概览 | `mkt_daily` | 无 | 每日市场概览和三大指数 |
| 今日机会 | `mkt_daily_chance` | `mkt_daily_chance_stock` | 财联社 `today_chances` |
| 今日风口 | `mkt_daily_tuyere` | `mkt_daily_tuyere_stock` | 财联社 `today_tuyeres` |
| 话题热榜 | `mkt_daily_topic` | `mkt_daily_topic_stock` | 同花顺 `topic_list` 前 5 |
| 热门板块 | `mkt_hot_board` | 无 | 多平台热门板块原始榜单 |
| 热门个股 | `mkt_hot_stock` | 无 | 多平台热门个股原始榜单 |
| 涨停板块 | `mkt_limit_up_plate` | 无 | 财联社 `plate_stock` 板块维度 |
| 涨停个股 | `mkt_limit_up_stock` | 无 | 财联社 `plate_stock.stock_list` 个股维度，兼容梯度统计 |

## mkt_daily

唯一约束：`trade_date + source`

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源，如 `real`、`mock` |
| `sh_index` / `sz_index` / `cyb_index` | Float | 上证、深成指、创业板指点位 |
| `sh_index_change_pct` / `sz_index_change_pct` / `cyb_index_change_pct` | Float | 三大指数涨跌幅 |
| `sh_index_change_px` / `sz_index_change_px` / `cyb_index_change_px` | Float | 三大指数涨跌点数 |
| `index_trade_status` | JSON | 三大指数交易状态 |
| `total_amount` | Float | 全市场成交额 |
| `up_count` / `down_count` / `flat_count` | Integer | 上涨、下跌、平盘家数 |
| `limit_up_count` / `limit_down_count` | Integer | 涨停、跌停家数 |
| `broken_limit_count` | Integer | 炸板数量 |
| `max_continue_board` | Integer | 最高连板高度 |
| `source_url` | String(512) | 主要数据源 URL |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `raw_snapshot` | JSON | 原始接口快照，仅用于追溯和排错 |

## mkt_daily_chance / mkt_daily_chance_stock

`mkt_daily_chance` 保存财联社 `today_chances` 主体信息，唯一约束：`trade_date + source + subject_id`。

`mkt_daily_chance_stock` 保存关联个股，唯一约束：`chance_id + stock_code`。

## mkt_daily_tuyere / mkt_daily_tuyere_stock

`mkt_daily_tuyere` 保存财联社 `today_tuyeres` 主体信息，唯一约束：`trade_date + source + subject_id`。

`mkt_daily_tuyere_stock` 保存关联个股，唯一约束：`tuyere_id + stock_code`。

## mkt_daily_topic / mkt_daily_topic_stock

`mkt_daily_topic` 保存同花顺话题热榜前 5 条，唯一约束：`trade_date + source + topic_code`。

`mkt_daily_topic_stock` 保存关联个股，唯一约束：`topic_id + stock_code`。

## mkt_hot_board

热门板块榜单表，保存各平台原始板块排名，唯一约束：`trade_date + platform + board_name`。

关键字段：`platform_rank`、`raw_score`、`change_pct`、`amount`、`leader_stock_code`、`leader_stock_name`、`leading_stocks`、`reason`、`source_url`、`source_update_time`、`raw_payload`。

## mkt_hot_stock

热门个股榜单表，保存平台原始排名和原始分数，唯一约束：`trade_date + platform + stock_code`。

关键字段：`platform_rank`、`raw_score`、`raw_reason`、`price`、`change_pct`、`board_name`、`source_url`、`source_update_time`、`raw_payload`。

## mkt_limit_up_plate

涨停板块表，来自财联社 `up_down_analysis.plate_stock` 的板块层信息，唯一约束：`trade_date + source + plate_code`。

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源 |
| `platform` | String(32) | 平台，默认 `cls` |
| `plate_code` | String(32) | 板块代码 |
| `plate_name` | String(128) | 板块名称 |
| `change_pct` | Float | 板块涨跌幅 |
| `limit_up_count` | Integer | 板块内涨停家数 |
| `up_reason` | Text | 板块上涨原因 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |

## mkt_limit_up_stock

涨停个股表，来自财联社 `up_down_analysis.plate_stock[].stock_list`。该表同时承载 `continuous_limit_up` 的梯度高度回填，页面“涨停梯度”从本表实时统计。

唯一约束：`trade_date + source + stock_code`

| 字段 | 类型 | 说明 |
|---|---|---|
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源 |
| `platform` | String(32) | 平台，默认 `cls` |
| `stock_code` | String(16) | 标准股票代码，如 `002583.SZ` |
| `raw_secu_code` | String(32) | 来源原始代码，如 `sz002583` |
| `stock_name` | String(64) | 股票名称 |
| `plate_code` | String(32) | 所属涨停板块代码 |
| `plate_name` | String(128) | 所属涨停板块名称 |
| `change_pct` | Float | 个股涨跌幅 |
| `last_price` | Float | 最新价 |
| `circulating_market_cap` | Float | 流通市值 |
| `limit_time` | String(32) | 来源涨停时间文本 |
| `limit_datetime` | DateTime | 来源涨停时间，结构化后用于排序 |
| `board_days` | Integer | `N天M板` 中的 N |
| `board_count` | Integer | `N天M板` 中的 M，或首板为 1 |
| `board_text` | String(64) | 连板原始文本，如 `15天11板` |
| `limit_reason` | Text | 涨停原因全文 |
| `reason_tags` | String(256) | 涨停原因标签 |
| `ladder_height` | Integer | 从 `continuous_limit_up` 回填的真实梯度高度 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |

## 采集来源对应关系

| 接口 | 入库表 |
|---|---|
| 财联社三大指数接口 `/v2/quote/a/web/stocks/basic` | `mkt_daily` |
| 财联社推荐接口 `/api/subject/recommend/article` 的 `today_chances` | `mkt_daily_chance`、`mkt_daily_chance_stock` |
| 财联社推荐接口 `/api/subject/recommend/article` 的 `today_tuyeres` | `mkt_daily_tuyere`、`mkt_daily_tuyere_stock` |
| 同花顺话题热榜 `/hot_list/v1/topic` 的 `topic_list` 前 5 | `mkt_daily_topic`、`mkt_daily_topic_stock` |
| 财联社涨停分析 `/v2/quote/a/plate/up_down_analysis` 的 `plate_stock` | `mkt_limit_up_plate`、`mkt_limit_up_stock` |
| 财联社涨停分析 `/v2/quote/a/plate/up_down_analysis` 的 `continuous_limit_up` | 回填 `mkt_limit_up_stock.ladder_height`，不再单独建表 |

## 备注

- `raw_snapshot` 和 `raw_payload` 只用于追溯，不作为页面主展示字段。
- 热门个股和热门板块只保留平台原始排名、原始分数、原始原因，不做主观综合评分。
- 涨停榜页面列表展示个股摘要，点击后查看明细和 K 线辅助图；梯度由 `mkt_limit_up_stock` 统计，不依赖独立梯度表。
- 所有页面展示均为行情和资讯辅助，不代表交易建议。
