# 东方财富 API 端点速查（A股一周预测专用）

## 已验证可用的API

### 1. 融资融券数据（最强预测因子）

```
GET https://datacenter-web.eastmoney.com/api/data/v1/get
  ?reportName=RPTA_WEB_RZRQ_GGMX
  &columns=DATE,RZYE,RZMRE,RZCHE,RZJME,RQYL,RQYE
  &filter=(SCODE=%22{代码}%22)
  &pageNumber=1
  &pageSize=10
  &sortTypes=-1
  &sortColumns=DATE
  &source=WEB
  &client=WEB
```

字段说明：
- `RZYE`: 融资余额（元）
- `RZMRE`: 融资买入额（元）
- `RZCHE`: 融资偿还额（元）
- `RZJME`: 融资净买入（元）= RZMRE - RZCHE
- `RQYL`: 融券余量（股）
- `RQYE`: 融券余额（元）

注意：返回的金额单位是**元**，需要除以100000000转换为**亿元**。

### 2. 涨跌停统计

```
GET https://push2.eastmoney.com/api/qt/ulist.np/get
  ?fltt=2
  &secids=1.000001
  &fields=f104,f105,f106,f107,f108,f109
```

字段说明：
- `f104`: 上涨家数
- `f105`: 下跌家数
- `f106`: 涨停家数
- `f107`: 跌停家数

### 3. 三大指数

```
GET https://push2.eastmoney.com/api/qt/ulist.np/get
  ?fltt=2
  &secids=1.000001,0.399001,0.399006
  &fields=f2,f3,f4,f12,f14
```

字段说明：
- `f2`: 最新价
- `f3`: 涨跌幅%
- `f4`: 涨跌额
- `f12`: 代码
- `f14`: 名称

### 4. K线数据（日线）

```
GET https://push2his.eastmoney.com/api/qt/stock/kline/get
  ?secid={secid}
  &fields1=f1,f2,f3,f4,f5,f6
  &fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61
  &klt=101
  &fqt=0
  &beg={YYYYMMDD}
  &end={YYYYMMDD}
```

secid规则：
- 沪市（60开头）：`1.{代码}`（如 `1.603019`）
- 深市（00/30开头）：`0.{代码}`

fields2字段说明：
- `f51`: 日期
- `f52`: 开盘
- `f53`: 收盘
- `f54`: 最高
- `f55`: 最低
- `f56`: 成交量（手）
- `f57`: 成交额（元）
- `f58`: 振幅%
- `f59`: 涨跌幅%
- `f60`: 涨跌额
- `f61`: 换手率%

### 5. 实时行情

```
GET https://push2.eastmoney.com/api/qt/stock/get
  ?secid={secid}
  &fields=f43,f44,f45,f46,f47,f48,f60,f168,f169,f170
```

字段说明：
- `f43`: 今收
- `f44`: 最高
- `f45`: 最低
- `f46`: 今开
- `f47`: 成交量（手）
- `f48`: 成交额（元）
- `f60`: 昨收
- `f168`: 换手率%
- `f169`: 量比
- `f170`: PE(动)

---

## 已验证不可用的API

### 北向资金
- `push2.eastmoney.com/api/qt/kamtbs.wss` → 返回空
- `push2.eastmoney.com/api/qt/kamt.rtmin/get` → 未测试

### 东方财富新闻搜索
- `search-api-web.eastmoney.com/search/jsonp` → 返回格式复杂，难以解析

---

## 实战经验

### 中科曙光案例（2026-06-28）

**关键发现**：
- 融资融券API返回近10天数据，最有价值
- 6/26单日融资净买入+7亿元（正常水平的10倍）→ 强烈看多信号
- 融资余额从89.5亿飙升至100.6亿 → 杠杆资金加速入场

**数据转换**：
```python
# 融资余额从元转换为亿元
balance_yi = balance_yuan / 100000000
```
