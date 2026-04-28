# Compliance Check

## Product Boundary

- 系统定位为交易辅助工具，不承诺收益，不替代用户决策。
- MVP 禁止自动下单、自动报单、自动撤单、券商接口交易。
- 所有交易动作必须由用户人工确认。

## Signal Copy Rules

- 买入类文案统一使用“买入观察信号”。
- 风险类文案统一使用“风险提醒”。
- 卖出类文案统一使用“卖出观察提醒”。
- 所有信号说明追加“仅作为交易辅助”。

## Data Governance

- 外部数据统一经 Provider 接口抽象。
- MVP 仅使用 MockProvider，不接入真实行情接口或爬虫。
- 数据异常、缺失、质量失败不得生成有效信号。
- `signal_record` 必须存储 `raw_snapshot`。

## To Be Rechecked After Implementation

- [x] 前后端是否存在违规按钮或诱导性文案
- [x] API 是否泄露敏感配置
- [x] 后台任务是否预留鉴权入口
- [x] 是否已防止重复确认交易

## Implementation Result

- 信号文案已限制为“买入观察信号 / 风险提醒 / 卖出观察提醒”，并在策略说明中追加“仅作为交易辅助”。
- 未实现任何券商接口、自动下单、自动报单、自动撤单或真实爬虫。
- ProviderFactory 仅支持 `mock` 模式。
- 管理任务 API 通过 `X-Admin-Token` 预留鉴权入口。
- `TradeService.confirm_trade` 已阻止同一信号重复确认。
