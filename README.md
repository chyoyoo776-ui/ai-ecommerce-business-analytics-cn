# AI-powered E-commerce Business Analytics & SKU Diagnosis System 
AI 电商经营分析与商品诊断系统

A Streamlit-based e-commerce analytics dashboard with SKU diagnosis, business health check, GMV uplift estimation, and Claude-powered strategy recommendations.
基于 Streamlit 搭建的电商经营分析作品集项目，覆盖生意大盘、经营健康度检查、SKU 商品诊断、GMV 增量测算与 Claude API 驱动的 AI 策略建议。

## 项目简介

模拟真实品牌特卖闪购电商 App 的经营数据（2024-07 ~ 2025-06，月均 GMV 约1000万元），
覆盖运动户外与鞋靴两大类目下的 21 个真实市场品牌。包含三大功能模块：

1. **生意大盘**：多渠道流量与 GMV 趋势监控
2. **商品诊断**：SKU 四象限分层，识别"高流量低转化"拖累款
3. **AI 策略助手**：一键生成结构化运营建议报告（需 Anthropic API Key）

## 本地运行方式

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动应用

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`

### 3. 使用 AI 策略助手模块

需要一个 Anthropic API Key（在 https://console.anthropic.com 申请），
在页面内输入框填入即可，Key 只在当次会话使用，不会被保存到任何文件。

## 项目结构

```
yipincang_app/
├── app.py                      # 主入口
├── utils.py                    # 数据加载与工具函数
├── requirements.txt
├── data/
│   ├── daily_business.csv      # 每日经营数据（按渠道拆分）
│   ├── brand_campaigns.csv     # 品牌场次数据
│   ├── sku_performance.csv     # SKU 商品运营明细
│   └── product_catalog.csv     # 商品基础目录
└── pages/
    ├── 1_Business_Overview.py
    ├── 2_Product_Diagnosis.py
    └── 3_AI_Assistant.py
```

## 数据说明

全部数据为合成模拟数据，基于真实业务逻辑建模（季节性、周内波动、双11/618等大促节点），
不涉及任何真实企业数据。三张核心表的 GMV 口径通过自底向上聚合（SKU → 场次 → 每日）
保证完全一致，不存在跨表对不上的情况。
