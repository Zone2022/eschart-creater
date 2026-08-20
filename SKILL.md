---
name: eschart-creater
description: Halo 自然光环站内推广周报生成。触发信号：用户要求生成/更新 Halo 站内推广周报、周度复盘、周环比分析；或用户将新一周万相台无界/品销宝导出表放入数据目录后要求出周报；或要求补更计划矩阵、SKU 费比等周报板块。输入为两周推广报表（关键词/人群/商品/计划/营销场景 CSV + 品牌专区 xlsx），输出为桌面 HTML 周报。
---

# Halo 站内推广周报生成

生成 Halo 自然光环（宠物食品）阿里系站内推广的**周度复盘网页**：本周 vs 上周环比，以计划为评价中心，通过 ROI×新客率推广波士顿矩阵分类计划，并保留各维度宏观统计，沿用 Halo 紫色 VI 模板。

## When to use

- 用户要求"做/更新 Halo 推广周报""本周推广复盘""周环比分析"。
- 用户通知新一周导出表已放入数据目录（默认 `C:\Users\24190\Desktop\推广文件`）。
- 用户要求补更计划矩阵、SKU 推广费比等周报板块。

## When NOT to use

- 月度/季度/年度复盘（本 skill 仅周度口径，月报另行处理）。
- 非 Halo 品牌或非万相台/品销宝渠道的数据分析。
- 单次数据查询、临时取数（直接回答，不出完整周报）。
- 数据源文件缺失且用户未提供补齐方式时——停止并询问，不要继续。

## Inputs

| 输入 | 位置 | 必需 |
|---|---|---|
| 两周 × 6 类报表 | `C:\Users\24190\Desktop\推广文件`（可用环境变量 `HALO_DATA_DIR` 覆盖） | 是 |
| 文件名日期后缀 | 数据所在周的**周一**，YYYYMMDD（如 20260803） | 是 |
| insights.json | 本流程第 3 步产出的简评文案 | 是（由 Skill 流程撰写） |
| 模板 CSS | 桌面最新周报 HTML，或环境变量 `HALO_TEMPLATE_HTML` 指定 | 是 |
| 模型署名 | 参数 `--model` 或环境变量 `HALO_MODEL_NAME` | 否（默认当前模型名） |

字段与文件规范见 `references/data-schema.md`；分类 token 见 `references/classification-tokens.json`；业务规则（口径/计划矩阵/判定标准）见 `references/business-rules.md`。

## Procedure

1. **校验输入**：运行 `scripts/validate_inputs.py`。存在 errors（缺文件/读取失败）→ 停止，向用户列出缺失清单并等待补齐；warnings（文件内部日期与后缀所在周不一致）→ 必须向用户确认后再继续（历史上发生过导错周期）。
2. **确定性计算**：运行 `scripts/analyze.py`，产出 `scripts/analysis.json`（artifact）。检查其 `meta.warnings`；阅读 stdout JSON 摘要。脚本输出 `plan_matrix`（同一计划包含 w0/w1 双周指标，横轴 ROI 中线 5、纵轴新客率中线 50%）、`prod_sku`（全部 SKU 的双周推广费比，费比=花费÷总成交金额）与 `optimize`（ROI<5 优化清单：本周花费词 ≥500 元 / 人群、计划 ≥1,000 元）。
3. **业务判断（撰写简评）**：先阅读 `plan_matrix`，以四象限分类为计划评价主线；再阅读各维度宏观聚合与 `optimize`，按 `templates/insight-style.md` 撰写 `scripts/insights.json`（键：scene/keyword/audience/brandzone/product/plan/optimize/actions；前六键为 `{"t","c"}` 结构化数组，结论需精简；样例见 `templates/insights.example.json`）。关键词、人群后续分析必须围绕计划好坏与调整方向展开；因源表不含计划 ID/计划名，只能按策略分类辅助计划诊断，禁止虚构单计划归因。**所有数字必须来自 analysis.json，禁止编造**。
4. **渲染**：运行 `scripts/build_report.py`，产出桌面 HTML。输出契约见 `templates/report-contract.json`。
5. **交付与核对**：向用户展示报告，列出各矩阵象限的计划数量与重点调整计划、优化清单合计规模、待复核点（分类待确认项见 references/classification-tokens.json 的 notes.review_pending）。

## Outputs

- 主产物：`C:\Users\24190\Desktop\Halo站内推广周报_<本周起止>.html`，结构与硬性规则见 `templates/report-contract.json`。
- 中间产物（artifact，不依赖对话记忆）：`scripts/analysis.json`、`scripts/insights.json`。
- 各脚本 stdout 输出机器可读 JSON（ok/error/out 等字段）。

## Constraints

- 禁止编造业务数据；输入缺失或校验失败时必须中断并询问用户。
- 不计算、不展示、不引用偏移指数、偏移标签、偏移调整算法或双因素拆解；不得将其作为评价指标的一部分。
- 关键词竞品词花费为 0 属策略基线，不作异常。
- 货品全站推广 ROI 必须带 ※ 标注（含免费流量）；品销宝不计算 ROI。
- 判定标准（8 月方案）：单项合格线 ROI≥5、整体红线 ROI≥6、警戒线 ROI 4；拉新类人群包需新客率≥50% 且 ROI≥5，竞品拦截人群按三件套（新客率代理）不单看短期 ROI。详见 `references/business-rules.md`。
- 推广波士顿矩阵：横轴 ROI 中线 5，纵轴新客率中线 50%；分类为明星计划、效率计划、拉新潜力、待调整；成交人数为 0 时列待观察。本周与上周必须共用坐标尺度，通过按钮切换；切换时同一计划点位平滑移动，新增/退出计划淡入淡出。
- 每个矩阵点必须支持鼠标悬停提示，至少显示计划名称、周次、场景、分类、花费、ROI、新客率和象限；不得只依赖编号反查计划。
- 商品主体板块删除全部概览 KPI 卡，展示商品报表中的所有 SKU，不剔除赠品/积分/购物金等主体；以横向直方图展示本周和上周推广费比。推广费比=花费÷总成交金额，成交金额为 0 时显示“—”。
- 各维度宏观统计口径与展示保持不变，只重写后续分析段落；关键词、人群分析以计划矩阵中的计划评价与调整方向为主线。
- 报告前两部分固定为核心总览、品销宝，内容保持不变；其后依次为营销场景、计划矩阵、关键词、人群、商品主体、优化清单、下周动作、口径附录。
- 无"结论速览"独立板块；大盘结论并入营销场景总结；下周动作仅保留 4 条执行建议。
- 文案为数据分析师口吻（数字+阈值+动作），结论为结构化精简条目，遵循 `templates/insight-style.md`。
- 脚本不含任何密钥；数据目录等通过环境变量注入。

## Error Handling

| 场景 | 处理 |
|---|---|
| 输入文件缺失 | 中断，输出缺失清单，等待用户补齐（exit 2） |
| CSV 编码错误 | 中断，提示需 GBK 编码重新导出（exit 2） |
| 文件内部日期与后缀周不一致 | 记 warning，**转人工确认**后再继续 |
| insights.json 缺失/缺键/结构非法/actions 非 4 条 | 中断，提示先完成简评撰写（exit 3） |
| 模板 CSS 来源缺失 | 中断，提示设置 HALO_TEMPLATE_HTML（exit 2） |
| 数据量级异常（如总花费为 0） | analysis.json warnings 记录，向用户说明后由用户决定是否继续 |

## Examples

**标准流程**（数据已放入推广文件目录）：
```bash
python scripts/validate_inputs.py            # 1. 校验
python scripts/analyze.py                    # 2. 计算 → analysis.json（自动识别最新两个周）
# 3. 按 templates/insight-style.md 撰写 scripts/insights.json
python scripts/build_report.py               # 4. 渲染 → 桌面 HTML
```

**指定周次与数据目录**：
```bash
set HALO_DATA_DIR=D:\data\推广文件
python scripts/analyze.py --this 20260803 --last 20260727
python scripts/build_report.py --model Kimi-K3
```

**缺文件**：validate_inputs.py 输出 `{"ok": false, "errors": ["缺少本周文件：关键词报表_20260803.csv"]}` → 停止并请用户补导。
