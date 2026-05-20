---
name: us-stock-analysis
description: 美股深度研究系统（三层架构版），基于yfinance免费数据（无需API key），生成专业的美股基本面分析HTML报告。包含K线图、财务分析、五维评分、投资建议。绿涨红跌。当用户说"分析AAPL"、"analyze TSLA"、"美股分析"时触发。
trigger_keywords: ["分析美股", "美股分析", "analyze", "US stock", "美股研究"]
version: 1.0
last_updated: 2026-05-19
---

# 美股深度研究系统（三层架构版）

> 版本：v1.0 | 更新：2026-05-19 | 定位：三层架构 + 强制Step 0-8 + AI手写HTML
> 基于A股版 stock-analysis v2.2 适配美股市场

---

## ⚡ 使用方式

**当用户说"分析 AAPL"或"analyze TSLA"时，AI一次性完成三阶段全流程（连续执行，中间不询问用户是否继续）：**

### Phase 1: 数据采集（30-60秒）

```bash
cd ~/.claude/skills/us-stock-analysis
python3 us_stock_report.py <TICKER>
```

**示例：**
```bash
python3 us_stock_report.py AAPL   # Apple
python3 us_stock_report.py TSLA   # Tesla
python3 us_stock_report.py MSFT   # Microsoft
```

**唯一输出：** `output/data_<TICKER>.json`

**⚠️ Phase 1完成后立即进入Phase 2**，不要停下来询问用户。JSON只是数据中间产物。

---

### Phase 2: AI深度分析（30-60分钟）

**AI必须手动执行以下步骤：**

1. **读取数据：** `output/data_<TICKER>.json`
2. **执行搜索：** 根据实际需要用WebSearch搜索（通常3-6次）
   - 行业趋势、市场规模（英文搜索）
   - 竞争对手、市场份额
   - Wall Street研报、目标价
   - 最新新闻、Fed政策动态
3. **逐步完成Step 0-8分析：** 严格按照分析框架，每个Step达到要求
4. **输出MD报告：** `output/个股研究-<公司名称>.md`

**⚠️ 三阶段连续执行，中间不中断。**

---

### Phase 3: HTML生成层（AI手动分批拼装 + 逐批机械校验）

> ⚠️ 写 HTML 只用 Write 工具。整个 Phase 3 只需 6 次 Write 调用，约 30 分钟。不要用 Python 替代。

**执行步骤：**

1. **读取模板：** `shared/template_base.css` + `shared/template_base.js`
2. **读取数据：** `output/个股研究-{公司名称}.md` + `output/data_{TICKER}.json`
3. **分批手写HTML（每批 = Write + grep校验）：**
   - 每批 ≤300行，用 **Write工具** 直接写HTML markup
   - 写完后立即跑该批对应的 grep 校验命令
   - 校验通过 → 下一批。校验失败 → Edit 修正 → 重新校验
4. **合并：** 仅用 `cat` 做机械字节拼接
5. **输出：** `output/个股研究-{公司名称}.html`
6. **自动打开：** 合并完成后立即执行 `open "output/个股研究-{公司名称}.html"` 在浏览器中打开报告

### ⚠️ 分批手写规则（强制）

**禁止行为：**

| 禁止 | 原因 |
|------|------|
| ❌ **Python f-string/template 生成HTML** | 需要大量 `{{}}` 转义，易出错 |
| ❌ **Bash heredoc 生成HTML** | 多行HTML下经常EOF匹配失败 |
| ❌ **一次性写出整个HTML** | >300行文件必须分批 |

**正确做法：**

| 操作 | 工具 | 说明 |
|------|------|------|
| 写入HTML内容 | **Write** | 直接写HTML markup |
| 精确局部修改 | **Edit** | 替换特定行 |
| 机械合并部分文件 | **Bash `cat`** | 仅读取+拼接字节 |

**标准分批方案（~900行HTML）：**

| 批次 | 内容 | 行数 |
|------|------|------|
| Batch 0 | DOCTYPE + `<head>` + `<style>`（CSS完整复制） | ~180行 |
| Batch 1 | `<body>` + nav + hero + conclusion-top + profile | ~150行 |
| Batch 2 | K线图卡片 + Step 0-3 卡片 | ~200行 |
| Batch 3 | Step 4-6 卡片（弹性/风险/估值） | ~200行 |
| Batch 4 | Step 7-8 卡片 + footer + `</div>` | ~150行 |
| Batch 5 | `<script>`（JS复制 + 注入rawData + pieData） | ~150行 |

---

### 输出文件

```
output/
├── data_<TICKER>.json              # Phase 1: 原始数据（yfinance采集）
├── 个股研究-<公司名称>.md           # Phase 2: 完整分析报告
└── 个股研究-<公司名称>.html         # Phase 3: 可视化HTML报告
```

---

## 🏗️ 三层架构

```
┌─────────────────────────────────────────────┐
│               用户输入                       │
│     "分析 AAPL" 或 "analyze TSLA"           │
└────────────────────┬────────────────────────┘
                     │
  ┌──────────────────▼──────────────────┐
  │  Phase 1: 数据采集（脚本·并发）      │
  │  python3 us_stock_report.py <TICKER>│
  │  → output/data_{TICKER}.json        │
  │  ⏱️ 30-60秒（ThreadPoolExecutor）   │
  └──────────────────┬──────────────────┘
                     │
  ┌──────────────────▼──────────────────┐
  │  Phase 2: AI分析（手写）             │
  │  读取 data JSON → WebSearch搜索     │
  │  → 逐步完成 Step 0-8                │
  │  → output/个股研究-{名称}.md         │
  └──────────────────┬──────────────────┘
                     │
  ┌──────────────────▼──────────────────┐
  │  Phase 3: HTML生成（手写）           │
  │  CSS/JS 从 shared/ 搬运             │
  │  内容从 MD + data JSON 提取         │
  │  → output/个股研究-{名称}.html       │
  └──────────────────┬──────────────────┘
                     │
              ┌──────▼──────┐
              │  完成 ✓     │
              └─────────────┘
```

---

## 📊 美股特有适配

### 涨跌颜色
- **绿涨红跌**（美股标准），与A股版（红涨绿跌）相反
- CSS变量：`--green-up:#28c75b` / `--red-down:#f55656`
- K线图、成交量柱、表格标记全部统一

### 数据源
- **yfinance**（免费，无需API key）
- 并发采集：ThreadPoolExecutor，13个数据块分组并行
- 数据块：basic_info, spot, kline_daily, financials, balance_sheet, income_stmt, cashflow, institutional_holders, recommendations, news, insider_transactions, options_summary, dividends, splits, sustainability

### 分析语境
- 宏观：Fed利率周期、美国经济、地缘政治
- 估值：PE/PEG/EV-Revenue/DCF，参照美股历史中位数
- 风险：Short Interest、期权隐含波动率、SEC监管
- 资金面：机构持仓变化、内部人交易、ETF资金流
- 货币：USD，K线tooltip显示$符号

---

## 🔧 Phase 2: Step 0-8 分析框架

**强制执行清单：**

```
□ Step 0: 任务锁定（10行）
  ├─ 标的（公司名、Ticker、交易所NYSE/NASDAQ）
  ├─ 周期（短线/中线/长线）
  ├─ 数据截止日（YYYY-MM-DD）
  ├─ 研究状态（首次覆盖/持续跟踪）
  └─ 风格预判（配置型/交易型/左侧博弈型）

□ Step 1: 宏观与周期定位（50行）
  ├─ 1a. 经济周期映射（Fed利率周期、美国经济阶段）
  ├─ 1b. 政策与环境扫描（货币政策、财政政策、监管）
  └─ 1c. 核心矛盾提炼（XX vs YY）

□ Step 2: 产业链深度拆解（100行）
  ├─ 2a. 题材来源判断
  ├─ 2b. 产业链图谱（全球视角：上游→中游→下游）
  ├─ 2c. 趋势三要素（表格+打分）
  └─ 2d. 价值链利润分布

□ Step 3: 公司筛选与质量评分（50行）
  ├─ 3a. 正面筛选清单（6项标准）
  ├─ 3b. 不碰清单（SEC调查、持续亏损、做空报告等）
  └─ 3c. 质量评分（100分制，6维度）

□ Step 4: 业绩弹性测算（80行）
  ├─ 4a. 分业务弹性树
  ├─ 4b. 价格敏感度公式（关键变量→EPS影响$）
  └─ 4c. 情景分析（Bear/Base/Bull）

□ Step 5: 风险分析（40行）
  ├─ 5a. 风险清单（含Short Interest、期权IV、SEC风险）
  └─ 5b. 逻辑破坏条件（5个止损信号）

□ Step 6: 估值与买卖时机（100行）
  ├─ 6a. 估值方法选择（PE/PEG/EV-Revenue/DCF）
  ├─ 6a+. 资金面分析（机构持仓、内部人交易、做空比率）
  ├─ 6a++. 技术面分析（均线、支撑阻力、RSI）
  ├─ 6b. 三档目标价（短期/中期/长期 $）
  └─ 6c. 盈亏比量化（Risk/Reward）

□ Step 7: 对标分析（60行）
  ├─ 7a. 案例类比法（全球同行对比）
  └─ 7b. 增长引擎切换

□ Step 8: 跟踪计划与综合结论（50行）
  ├─ 8a. 分层跟踪锚点（Earnings Call/月度/事件）
  ├─ 8b. 执行清单
  ├─ 8c. 综合结论
  └─ 8d. 五维综合评分（基本面40%+资金面20%+技术面15%+情绪面15%+事件10%）

✅ 总计：540行（最低要求）
```

---

## 🎨 HTML手写规范

### 核心要点

- `<style>` = `shared/template_base.css` 完整搬运，不做修改
- `<script>` = `shared/template_base.js` 骨架 + 注入 rawData（K线）+ pieData（业务构成）
- OHLC 格式 `[open, close, low, high]`，成交量每根单独着色
- **绿涨红跌**全篇一致
- 产业链SVG文字用 `.svg-hdr` / `.svg-sub` class
- MathJax用 `\(...\)`（单反斜杠）
- 所有CSS class必须来自template_base.css
- **评分条score-fill必须为`<div>`，带内联`style="width:X%"`**
- **📌总结框为强制组件**：Step 8底部必须有红色左边框总结框
- **弹性树强制HTML模板**：flex+CSS边框构建树形图

### 页面结构（强制顺序）

```
top-nav → .hero → .conclusion-top → grid-2(公司画像+动态) → grid-2(饼图+财务)
→ .card(K线图) → 分析章节9卡片 → footer
```

### Step 0-8 关键可视化组件

- **Step 0:** 4个信息卡片（标的/周期/风格/命题）
- **Step 1:** 核心矛盾高亮框
- **Step 2:** 产业链SVG图谱、grid-2布局
- **Step 3:** grid-2布局、6个评分条、评级徽章
- **Step 4:** 弹性树、公式卡片2x2、情景分析grid-3（Bear/Base/Bull）
- **Step 5:** grid-2布局、止损信号列表
- **Step 6:** grid-2布局、三档目标价$、Risk/Reward量化卡片
- **Step 7:** 对比表格、增长引擎切换3卡片
- **Step 8:** grid-2布局、执行清单、verdict-highlight、五维评分、📌总结框

---

## 🔧 配置要求

**必需配置：**
- Python 3.8+
- yfinance库（数据采集，免费无需API key）
- Claude Code环境（AI分析和HTML生成）

**安装：**
```bash
pip install yfinance pandas numpy
```

---

> **免责声明：** 本系统所有分析仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。
