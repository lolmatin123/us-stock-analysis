# 美股深度研究系统 · US Stock Analysis Skill

> Claude Code Skill · 基于 yfinance 免费数据 · 生成专业美股基本面分析 HTML 报告

## 功能概述

三层架构自动生成美股深度研究报告：

- **Phase 1** — yfinance 并发采集 22 个数据块（30-60 秒）
- **Phase 2** — AI 执行 Step 0-8 完整基本面分析框架
- **Phase 3** — AI 手写 HTML，生成可交互报告（K线图、饼图、五维评分）

报告包含：K线走势（120日）、营收构成、关键财务指标、产业链SVG图谱、弹性测算、风险分析、估值目标价、对标分析、综合结论。绿涨红跌，支持深色/浅色切换。

## 使用方式

### 1. 安装依赖

```bash
pip install yfinance pandas numpy
```

### 2. 注册 Skill

在 `~/.claude/CLAUDE.md` 中添加：

```markdown
### us-stock-analysis (美股深度研究系统)
- Location: `~/.claude/skills/us-stock-analysis/`
- Skill definition: `~/.claude/skills/us-stock-analysis/SKILL.md`
- Trigger: 当用户说"分析AAPL"、"analyze TSLA"、"美股分析"时触发
- Usage: 三层架构，基于yfinance免费数据，生成美股基本面分析HTML报告
- Run: `cd ~/.claude/skills/us-stock-analysis && python3 us_stock_report.py <TICKER>`
```

### 3. 触发分析

在 Claude Code 中直接说：

```
分析 AAPL
analyze TSLA
美股分析 NVDA
```

Claude 会自动完成三阶段全流程，最终在浏览器中打开报告。

## 文件结构

```
us-stock-analysis/
├── SKILL.md                # Skill 定义（Claude Code 读取）
├── us_stock_report.py      # Phase 1：yfinance 并发数据采集
├── requirements.txt        # 依赖：yfinance, pandas, numpy
├── config.yaml             # yfinance 超时/重试配置
├── 分析框架.md              # Step 0-8 美股版分析方法论
├── HTML手写参考.md          # HTML 组件速查
├── src/
│   └── analyzer.py         # Phase 2 Step 0-8 配置
├── shared/
│   ├── template_base.css   # 报告 CSS 模板（绿涨红跌）
│   └── template_base.js    # ECharts K线/饼图模板
└── output/                 # 生成文件（gitignore）
    ├── data_<TICKER>.json  # Phase 1 原始数据
    ├── 个股研究-<名称>.md   # Phase 2 分析报告
    └── 个股研究-<名称>.html # Phase 3 可视化报告
```

## 技术亮点

- **速度**：ThreadPoolExecutor 并发采集，3-6 秒完成（vs A股版 3-5 分钟）
- **免费**：基于 yfinance，无需任何 API Key
- **美股适配**：绿涨红跌、USD、Fed利率/做空率/期权IV分析
- **完整框架**：Step 0-8 覆盖宏观→产业链→质量→弹性→风险→估值→对标→结论

## 示例报告

| 股票 | 结论 | 评分 |
|------|------|------|
| AMKR (Amkor Technology) | 择时参与，$60-65建仓，目标$80 | 70/100 B+ |
| AMBQ (Ambiq Micro) | 仅观察，等回调至$55-65 | 70/100 B+ |

## 免责声明

本系统所有分析仅供研究参考，不构成投资建议。投资有风险，决策需谨慎。

---

## 致谢

本项目基于 [@mingli30119](https://github.com/mingli30119) 的 [stock-analysis](https://github.com/mingli30119/stock-analysis)（A股深度研究系统）移植适配而来，核心三层架构、分析框架（Step 0-8）、HTML 报告样式均源自原作者设计，在此表示感谢。
