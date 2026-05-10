# Aquant 市场数据表结构说明

本文档说明 Aquant 当前市场数据相关表设计。市场模块只保存客观原始数据和来源信息，不保存主观评分、不自动入池、不生成交易建议。

## 设计原则

- `mkt_daily` 只保存每日大盘概览、三大指数、涨跌家数、成交额等日级市场主数据。
- 财联社“今日机会”“今日风口”和同花顺“话题热榜”拆分为独立结构化表，不再存入 `mkt_daily` JSON 字段。
- 财联社涨停分析接口拆分为三类表：涨停个股、涨停板块、涨停梯度。
- 股票代码统一使用 `600000.SH`、`000001.SZ`、`430000.BJ` 格式。
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
| 涨停个股 | `mkt_limit_up_stock` | 无 | 财联社 `plate_stock.stock_list` 个股维度 |
| 涨停梯度 | `mkt_limit_up_ladder` | 无 | 财联社 `continuous_limit_up` 梯度维度 |
| 旧兼容涨停表 | `mkt_limit_up` | 无 | 旧接口兼容表，后续主流程优先使用 `mkt_limit_up_stock` |

## 1. mkt_daily

每日市场主表，保存大盘概览与三大指数数据。

唯一约束：`trade_date + source`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源，如 `real`、`mock` |
| `sh_index` | Float | 上证指数点位 |
| `sz_index` | Float | 深证成指点位 |
| `cyb_index` | Float | 创业板指点位 |
| `index_change_pct` | Float | 兼容字段，默认表示上证指数涨跌幅 |
| `sh_index_change_pct` | Float | 上证指数涨跌幅，单位百分比 |
| `sh_index_change_px` | Float | 上证指数涨跌点数 |
| `sz_index_change_pct` | Float | 深证成指涨跌幅，单位百分比 |
| `sz_index_change_px` | Float | 深证成指涨跌点数 |
| `cyb_index_change_pct` | Float | 创业板指涨跌幅，单位百分比 |
| `cyb_index_change_px` | Float | 创业板指涨跌点数 |
| `index_trade_status` | JSON | 三大指数交易状态，保存 `sh000001`、`sz399001`、`sz399006` 状态 |
| `total_amount` | Float | 全市场成交额 |
| `up_count` | Integer | 上涨家数 |
| `down_count` | Integer | 下跌家数 |
| `flat_count` | Integer | 平盘家数 |
| `limit_up_count` | Integer | 涨停家数 |
| `limit_down_count` | Integer | 跌停家数 |
| `broken_limit_count` | Integer | 炸板数量 |
| `max_continue_board` | Integer | 最高连板高度 |
| `source_url` | String(512) | 主要数据源 URL |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `raw_snapshot` | JSON | 原始接口快照，仅用于追溯和排错 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 2. mkt_daily_chance

财联社“今日机会”主表，来自 `today_chances`。

唯一约束：`trade_date + source + subject_id`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源 |
| `platform` | String(32) | 平台，默认 `cls` |
| `rank_no` | Integer | 展示顺序 |
| `subject_id` | Integer | 财联社主题 ID |
| `subject_name` | String(128) | 主题名称 |
| `article_id` | Integer | 关联文章 ID |
| `article_title` | Text | 文章标题 |
| `article_time` | Integer | 文章时间戳 |
| `attention_num` | Integer | 关注度 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 3. mkt_daily_chance_stock

今日机会关联个股表。

唯一约束：`chance_id + stock_code`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `chance_id` | Integer | 关联 `mkt_daily_chance.id` |
| `stock_code` | String(16) | 股票代码 |
| `stock_name` | String(64) | 股票名称 |
| `change_pct` | Float | 个股涨跌幅 |
| `last_price` | Float | 最新价 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 4. mkt_daily_tuyere

财联社“今日风口”主表，来自 `today_tuyeres`。

唯一约束：`trade_date + source + subject_id`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源 |
| `platform` | String(32) | 平台，默认 `cls` |
| `rank_no` | Integer | 展示顺序 |
| `subject_id` | Integer | 财联社主题 ID |
| `subject_name` | String(128) | 主题名称 |
| `driver` | Text | 风口驱动原因 |
| `attention_num` | Integer | 关注度 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 5. mkt_daily_tuyere_stock

今日风口关联个股表。

唯一约束：`tuyere_id + stock_code`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `tuyere_id` | Integer | 关联 `mkt_daily_tuyere.id` |
| `stock_code` | String(16) | 股票代码 |
| `stock_name` | String(64) | 股票名称 |
| `change_pct` | Float | 个股涨跌幅 |
| `last_price` | Float | 最新价 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 6. mkt_daily_topic

同花顺话题热榜主表，当前采集 `topic_list` 前 5 条。

唯一约束：`trade_date + source + topic_code`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源 |
| `platform` | String(32) | 平台，默认 `ths` |
| `rank_no` | Integer | 榜单排名 |
| `topic_code` | String(64) | 话题代码 |
| `title` | Text | 话题标题 |
| `description` | Text | 话题描述 |
| `subtitle` | Text | 副标题 |
| `hot_value` | Float | 原始热度值 |
| `jump_url` | String(512) | 原始跳转链接 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 7. mkt_daily_topic_stock

话题热榜关联个股表。

唯一约束：`topic_id + stock_code`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `topic_id` | Integer | 关联 `mkt_daily_topic.id` |
| `stock_code` | String(16) | 股票代码 |
| `stock_name` | String(64) | 股票名称 |
| `change_pct` | Float | 个股涨跌幅 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 8. mkt_hot_board

热门板块榜单表，保存各平台原始板块排名。

唯一约束：`trade_date + platform + board_name`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `platform` | String(32) | 平台 |
| `board_name` | String(128) | 板块名称 |
| `platform_rank` | Integer | 平台原始排名 |
| `raw_score` | Float | 平台原始分数 |
| `change_pct` | Float | 板块涨跌幅 |
| `amount` | Float | 成交额 |
| `leader_stock_code` | String(16) | 领涨股代码 |
| `leader_stock_name` | String(64) | 领涨股名称 |
| `leading_stocks` | JSON | 领涨股原始列表 |
| `reason` | Text | 入榜原因 |
| `source_url` | String(512) | 来源链接 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `raw_payload` | JSON | 原始负载 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 9. mkt_hot_stock

热门个股榜单表，保存平台原始排名和分数。

唯一约束：`trade_date + platform + stock_code`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `platform` | String(32) | 平台 |
| `stock_code` | String(16) | 股票代码 |
| `stock_name` | String(64) | 股票名称 |
| `board_name` | String(128) | 所属板块 |
| `platform_rank` | Integer | 平台原始排名 |
| `raw_score` | Float | 平台原始分数 |
| `raw_reason` | Text | 平台原始原因 |
| `price` | Float | 最新价 |
| `change_pct` | Float | 涨跌幅 |
| `source_url` | String(512) | 来源链接 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `raw_payload` | JSON | 原始负载 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 10. mkt_limit_up_plate

涨停板块表，来自财联社 `up_down_analysis.plate_stock` 的板块层信息。

唯一约束：`trade_date + source + plate_code`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源 |
| `platform` | String(32) | 平台，默认 `cls` |
| `plate_code` | String(32) | 板块代码，如 `cls80201` |
| `plate_name` | String(128) | 板块名称 |
| `change_pct` | Float | 板块涨跌幅 |
| `limit_up_count` | Integer | 板块内涨停家数 |
| `up_reason` | Text | 板块上涨原因 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 11. mkt_limit_up_stock

涨停个股表，来自财联社 `up_down_analysis.plate_stock[].stock_list`。

唯一约束：`trade_date + source + stock_code`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源 |
| `platform` | String(32) | 平台，默认 `cls` |
| `stock_code` | String(16) | 股票代码 |
| `stock_name` | String(64) | 股票名称 |
| `plate_code` | String(32) | 所属涨停板块代码 |
| `plate_name` | String(128) | 所属涨停板块名称 |
| `change_pct` | Float | 个股涨跌幅 |
| `last_price` | Float | 最新价 |
| `circulating_market_cap` | Float | 流通市值 |
| `limit_time` | String(32) | 涨停时间 |
| `board_count` | Integer | 连板数，按接口 `up_num` 解析 |
| `board_text` | String(64) | 连板原始文本，如 `3天3板` |
| `limit_reason` | Text | 涨停原因全文 |
| `reason_tags` | String(256) | 涨停原因标签 |
| `ladder_height` | Integer | 真实涨停梯度高度，仅来自 `continuous_limit_up` |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 12. mkt_limit_up_ladder

涨停梯度表，来自财联社 `up_down_analysis.continuous_limit_up`。

唯一约束：`trade_date + source + height`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `source` | String(32) | 数据来源 |
| `platform` | String(32) | 平台，默认 `cls` |
| `height` | Integer | 梯度高度，如 `4` 表示 4 板 |
| `stock_count` | Integer | 该梯度股票数量 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 13. mkt_limit_up

旧涨停兼容表。当前新采集主流程优先写入并读取：

- `mkt_limit_up_stock`
- `mkt_limit_up_plate`
- `mkt_limit_up_ladder`

`mkt_limit_up` 可用于历史兼容，后续如确认无历史依赖，可逐步废弃。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer | 主键 |
| `trade_date` | Date | 交易日期 |
| `platform` | String(32) | 平台 |
| `stock_code` | String(16) | 股票代码 |
| `stock_name` | String(64) | 股票名称 |
| `limit_time` | String(16) | 首次涨停时间 |
| `last_limit_time` | String(16) | 最后涨停时间 |
| `open_limit_count` | Integer | 开板次数 |
| `seal_amount` | Float | 封单金额 |
| `seal_volume` | Float | 封单量 |
| `turnover_rate` | Float | 换手率 |
| `amount` | Float | 成交额 |
| `board_count` | Integer | 连板数 |
| `concept` | String(128) | 概念/板块 |
| `limit_reason` | Text | 涨停原因 |
| `limit_type` | String(64) | 涨停类型 |
| `source_url` | String(512) | 来源链接 |
| `source_update_time` | DateTime | 来源更新时间 |
| `collected_at` | DateTime | 系统采集时间 |
| `raw_payload` | JSON | 原始负载 |
| `created_at` | DateTime | 创建时间 |
| `updated_at` | DateTime | 更新时间 |

## 采集来源对应关系

| 接口 | 入库表 |
|---|---|
| 财联社三大指数接口 `/v2/quote/a/web/stocks/basic` | `mkt_daily` |
| 财联社推荐接口 `/api/subject/recommend/article` 的 `today_chances` | `mkt_daily_chance`、`mkt_daily_chance_stock` |
| 财联社推荐接口 `/api/subject/recommend/article` 的 `today_tuyeres` | `mkt_daily_tuyere`、`mkt_daily_tuyere_stock` |
| 同花顺话题热榜 `/hot_list/v1/topic` 的 `topic_list` 前 5 | `mkt_daily_topic`、`mkt_daily_topic_stock` |
| 财联社涨停分析 `/v2/quote/a/plate/up_down_analysis` 的 `plate_stock` | `mkt_limit_up_plate`、`mkt_limit_up_stock` |
| 财联社涨停分析 `/v2/quote/a/plate/up_down_analysis` 的 `continuous_limit_up` | `mkt_limit_up_ladder`，并回填 `mkt_limit_up_stock.ladder_height` |

## 备注

- `raw_snapshot` 和 `raw_payload` 只用于追溯，不作为页面主展示字段。
- 热门个股和热门板块只保留平台原始排名、原始分数、原始原因，不做主观综合评分。
- 涨停梯度以 `continuous_limit_up` 为准；未进入该字段的涨停股，`mkt_limit_up_stock.ladder_height` 保持为空。
- 所有页面展示均为行情和资讯辅助，不代表交易建议。
