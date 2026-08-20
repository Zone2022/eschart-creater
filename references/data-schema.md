# 数据 Schema（数据源文件规范）

数据目录默认 `C:\Users\24190\Desktop\推广文件`（可用环境变量 `HALO_DATA_DIR` 覆盖）。
文件命名：`<类型>[_]YYYYMMDD.<ext>`，后缀 = 数据所在周的**周一**（如 20260803）。
每周 6 类 × 2 周 = 12 个文件。CSV 一律 **GBK** 编码；xlsx 为品销宝导出。

## 文件清单
| 文件 | 格式 | 粒度 | 说明 |
|---|---|---|---|
| 营销场景报表_YYYYMMDD.csv | CSV/GBK | 场景（可能是日粒度，需按周汇总） | 核心总览与营销场景板块数据源 |
| 关键词报表_YYYYMMDD.csv | CSV/GBK | 词/词包（周汇总） | 关键词板块 |
| 人群报表_YYYYMMDD.csv | CSV/GBK | 人群包（周汇总） | 人群板块 |
| 商品报表_YYYYMMDD.csv | CSV/GBK | 商品主体（周汇总） | 商品主体板块 |
| 计划报表_YYYYMMDD.csv | CSV/GBK | 计划（周汇总） | 计划板块 |
| 品牌专区报表YYYYMMDD.xlsx | xlsx | 日粒度（账户 sheet 按周求和） | 品销宝板块 |

## 关键字段（CSV 共用主字段）
| 字段 | 类型 | 说明 |
|---|---|---|
| 日期 | 文本 | `YYYYMMDD至YYYYMMDD` 或 `YYYY-MM-DD`（日粒度）；**必须与文件名后缀所在周一致** |
| 场景名字 | 文本 | 关键词推广/人群推广/货品全站推广/超级短视频/超级直播 |
| 词类型 / 词名字/词包名字 | 文本 | 关键词报表专用；词类型=关键词/关键词包 |
| 人群名字 | 文本 | 人群报表专用 |
| 计划ID / 计划名字 | 文本 | 本周关键词、人群、计划报表必需；关键词/人群优化清单按这两个源字段展示具体计划。上周关键词、人群报表缺失时，上周仅按同名对象汇总作参考 |
| 主体名称 | 文本 | 商品报表专用 |
| 计划名字 | 文本 | 计划报表专用 |
| 展现量/点击量/花费 | 数值 | CTR=点击量÷展现量；CPC=花费÷点击量 |
| 直接成交金额/间接成交金额/总成交金额 | 数值 | 成交口径不含预售 |
| 总成交笔数/成交新客数/成交人数 | 数值 | 新客率=成交新客数÷成交人数 |
| 总收藏加购数 | 数值 | 分场景合计，未去重 |

## 品销宝 xlsx（账户 sheet 关键字段）
搜索量、展现量、点击量、进店访客数、成交金额、成交笔数、宝贝收藏数、宝贝加购数、回搜触达访客数、店铺收藏数、触达访客数。
客单价 = 成交金额 ÷ 成交笔数（计算字段）。sheet 共 6 个（账户/推广计划/推广单元/创意/品牌流量包/定向人群），当前仅用「账户」。

## analysis.json 中间产物（analyze.py 输出）
- `meta`：this/last 两期的 tag（周一日期）、start/end、warnings（数据校验警告）
- `total` / `scene` / `kw_cat` / `au_cat` / `plan_cat` / `px`：各维度 w0(上周)/w1(本周) 聚合指标
- `plan_matrix`：计划级推广波士顿矩阵点；每项含 key/name/cat/scene 与 `w0`/`w1`（active/spend/gmv/roi/new_rate/new_customers/buyers/quadrant/action）。双周共用坐标尺度；成交人数为 0 时 quadrant=`待观察`，未投放时 quadrant=`未投放`
- `prod_sku`：商品报表全部 SKU，按主体名称汇总；每项含 name 与 `w0`/`w1`（spend/gmv/fee_ratio），其中 fee_ratio=spend÷gmv，gmv=0 时为 null
- `optimize`：kw/au/plan 三类 ROI<5 优化清单（入选=本周花费词≥500 元 / 人群、计划≥1,000 元且本周 ROI<5；含 cat/sp1/g1/roi1/sp0/roi0/sp_chg/action；人群另含 new_rate，计划另含 new_rate/quadrant）
- `kw_detail` / `au_top` / `plan_detail`：明细与合计；关键词、人群源表不含计划 ID/计划名，禁止据此构造单计划直接归因

## insights.json 中间产物（Skill 流程撰写，build_report.py 消费）
- `scene`/`keyword`/`audience`/`brandzone`/`product`/`plan`：**结构化数组**，元素 `{"t": 小标题, "c": 内容}`，每键 3~4 条精简条目（HTML 片段）
- `optimize`：字符串（单段 HTML callout，优化清单汇总与处置优先级）

风格契约见 templates/insight-style.md；填写样例见 templates/insights.example.json。
