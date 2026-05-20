#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Phase 2: AI分析层（美股版）
Step 0-8 强制执行配置，适配美股市场语境。
"""

ANALYSIS_STEPS = [
    {
        "step": "Step 0",
        "name": "任务锁定",
        "min_lines": 10,
        "required_fields": ["标的", "周期", "数据截止日", "研究状态", "风格预判"],
        "prompt": """
生成任务锁定表格，包含：
- 标的（公司名、Ticker、交易所NYSE/NASDAQ）
- 周期（短线/中线/长线）
- 数据截止日（YYYY-MM-DD）
- 研究状态（首次覆盖/持续跟踪）
- 风格预判（配置型/交易型/左侧博弈型）
"""
    },
    {
        "step": "Step 1",
        "name": "宏观与周期定位",
        "min_lines": 50,
        "mcp_searches": [
            "{industry} industry outlook 2026 market size",
            "{company} sector trends Fed rate impact"
        ],
        "prompt": """
必须包含：
1a. 经济周期映射（美联储利率周期、美国经济阶段、公司所处周期）
1b. 政策与环境扫描（Fed货币政策、财政政策、监管环境、地缘政治）
1c. 核心矛盾提炼（一句话判断：XX vs YY）

使用搜索结果中的行业趋势和宏观数据。
"""
    },
    {
        "step": "Step 2",
        "name": "产业链深度拆解与趋势验证",
        "min_lines": 100,
        "mcp_searches": [
            "{company} competitors market share",
            "{industry} supply chain upstream downstream"
        ],
        "prompt": """
必须包含：
2a. 题材来源判断（行业驱动 or 公司特有催化剂）
2b. 产业链图谱（全球视角：上游→中游→下游，标注地理分布）
2c. 业务线拆解与趋势三要素（表格+打分：供需格局、价格锚点、海外验证）
2d. 价值链利润分布分析（表格：上游/中游/下游的毛利率、净利率）

使用搜索结果中的竞争对手和产业链数据。
"""
    },
    {
        "step": "Step 3",
        "name": "公司筛选与质量评分",
        "min_lines": 50,
        "prompt": """
必须包含：
3a. 正面筛选清单（6项标准：市值门槛、行业地位、业务护城河、业绩增长、估值位置、管理层信号）
3b. 不碰清单（负面排查：SEC调查、持续亏损无转机、做空报告、内部人大量减持）
3c. 质量评分（100分制，6个维度：基本面质量30分、产业匹配度20分、业绩弹性20分、估值与位置15分、资金与交易结构10分、治理与风险5分）

使用yfinance数据中的财务数据和股东结构。
"""
    },
    {
        "step": "Step 4",
        "name": "业绩弹性测算",
        "min_lines": 80,
        "prompt": """
必须包含：
4a. 分业务弹性树（用代码块呈现，格式：公司→业务A→业务B→当前估值→结论）
4b. 价格敏感度公式（至少3个公式，格式：关键变量每变动X% → 年EPS影响$Y）
4c. 情景分析（表格：Bear/Base/Bull，包含触发条件、Revenue区间、EPS区间、对应PE）

使用yfinance数据中的营收构成和财务数据。货币单位使用USD。
"""
    },
    {
        "step": "Step 5",
        "name": "风险分析与逻辑破坏条件",
        "min_lines": 40,
        "prompt": """
必须包含：
5a. 风险清单（表格：风险类型、具体场景、影响程度、发生概率）
    至少包含：行业周期、竞争格局、做空压力(short interest)、期权隐含波动率、监管风险(SEC/FTC)、汇率风险、地缘政治
5b. 逻辑破坏条件（5个止损信号，每条需可量化或可观测）
    示例：EPS连续2季miss、short interest超过20%、核心高管离职、反垄断诉讼
"""
    },
    {
        "step": "Step 6",
        "name": "估值-赔率与买卖时机",
        "min_lines": 100,
        "mcp_searches": [
            "{company} analyst price target 2026 Wall Street"
        ],
        "prompt": """
必须包含：
6a. 估值方法选择（成长型用PE/PEG/EV-Revenue、价值型用PE/PB/DCF、周期型用EV-EBITDA）
6a+. 资金面分析（表格：机构持仓变化、ETF资金流、内部人交易、做空比率）
6a++. 技术面分析（表格：价格位置、均线系统、成交量、RSI、关键价格位）
6b. 三档目标价（表格：短期/中期/长期，包含时间窗口、目标价$、估值依据、核心假设、触发条件、Risk/Reward）
6c. 盈亏比量化（当前位置：向下空间XX%、向上空间XX%、Risk/Reward X:X）

使用搜索结果中的华尔街研报，使用yfinance数据中的K线和机构持仓。
"""
    },
    {
        "step": "Step 7",
        "name": "对标与对比分析",
        "min_lines": 60,
        "mcp_searches": [
            "{company} vs {competitor} comparison valuation"
        ],
        "prompt": """
必须包含：
7a. 案例类比法（表格：本票 vs Peer A vs Peer B，对比维度：产业周期、Revenue Growth、Margins、估值水平、确定性、弹性来源）
7b. 增长引擎切换分析（如果适用，表格：原引擎 vs 新引擎，对比维度：TAM、Revenue占比、Margin Profile、竞争格局）

使用搜索结果中的同行数据。对标公司优先选全球范围的直接竞争者。
"""
    },
    {
        "step": "Step 8",
        "name": "跟踪计划与综合结论",
        "min_lines": 50,
        "prompt": """
必须包含：
8a. 分层跟踪锚点（表格：Earnings Call(季度)、月度数据、事件驱动，包含跟踪内容和数据来源）
8b. 执行清单（短线：触发条件、失效条件；中线：3财务+3事件催化）
8c. 综合结论（强制格式）：
    - 一句话判断：当前更像___（趋势/修复/博弈）
    - 风险等级：低/中/高/极高
    - 风格标签：配置型/交易型/左侧博弈型
    - 操作建议：核心配置/择时参与/仅观察
8d. 五维综合评分（100分制）：
    - 基本面（40%）：产业逻辑15% + 业绩弹性15% + 财务质量10%
    - 资金面（20%）：机构持仓8% + 内部人交易7% + 做空比率5%
    - 技术面（15%）：位置判断6% + 趋势判断5% + 量价配合4%
    - 情绪面（15%）：市场热度6% + 拥挤度5% + 预期差4%
    - 事件催化（10%）：政策催化4% + 业绩催化3% + 事件催化3%
"""
    }
]
