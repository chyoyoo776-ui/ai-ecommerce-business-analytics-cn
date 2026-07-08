# -*- coding: utf-8 -*-
"""
AI 电商经营分析与商品诊断系统
主入口文件 — 运行方式: streamlit run app.py
"""

import streamlit as st
from utils import language_toggle, t

st.set_page_config(
    page_title="AI 电商经营分析与商品诊断系统",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

lang = language_toggle()

st.title(t("🛍️ AI 电商经营分析与商品诊断系统", "🛍️ AI-powered E-commerce Business Analytics & SKU Diagnosis System"))
st.caption(t("基于 Streamlit 与 Claude API 的电商经营看板和策略建议助手 · 作品集项目",
             "A Streamlit-based operations dashboard with Claude-powered strategy recommendations · Portfolio Project"))

st.markdown(t("""
### 项目背景

这个工具模拟了一个真实的**品牌特卖电商 App** 的完整经营场景 —— 涵盖运动户外与鞋靴两大类目下的
**21 个真实市场品牌**（耐克、阿迪达斯、安德玛、李宁、Vans、回力等），数据周期 **2024年7月 - 2025年6月**，
月均 GMV 约 **1,000 万元**。

在真实工作场景中，运营团队常见的痛点是：**BI 系统只能看到总流量、总 GMV，却无法定位具体是哪些商品在拖累转化率**。
这个项目正是为了解决这个问题而设计的。

---

### 三大功能模块

👈 **请从左侧导航栏进入各个功能页面**

| 模块 | 核心能力 |
|------|---------|
| 📊 **生意大盘** | 多渠道流量与 GMV 趋势监控，含经营健康度自动诊断 |
| 🔍 **商品诊断** | SKU 四象限分层，自动识别"高流量低转化"的拖累款商品 |
| 🤖 **AI 策略助手** | 一键生成运营建议报告 + GMV 增量测算器 |

---

### 数据说明

本项目全部数据均为**合成模拟数据**，基于真实业务逻辑与季节性规律建模生成（包含双11、618等真实大促节点），
不涉及任何真实企业的商业数据。
""", """
### Project Background

This tool simulates a real **brand flash-sale e-commerce App** business scenario — covering **21 real market
brands** (Nike, Adidas, Under Armour, Li-Ning, Vans, Warrior, etc.) across Sportswear & Outdoor and Footwear
categories, spanning **July 2024 – June 2025**, with average monthly GMV around **¥10M**.

A common pain point in real operations teams: **the internal BI system only shows total traffic and GMV,
with no way to pinpoint which specific products are dragging down conversion rate.** This project was built
to solve exactly that problem.

---

### Three Core Modules

👈 **Use the sidebar to navigate between pages**

| Module | Core Capability |
|--------|------------------|
| 📊 **Business Overview** | Multi-channel traffic & GMV trend monitoring, with automated health check |
| 🔍 **Product Diagnosis** | SKU four-quadrant segmentation to identify "high-traffic low-conversion" drag SKUs |
| 🤖 **AI Strategy Assistant** | One-click strategy report generation + GMV uplift calculator |

---

### Data Note

All data in this project is **synthetic**, modeled on realistic business logic and seasonality (including
real promotion dates like 11.11 and 618), and does not involve any real company's commercial data.
"""))

with st.sidebar:
    st.header(t("关于本项目", "About This Project"))
    st.markdown(t("""
    **技术栈**
    - Streamlit + Plotly
    - Pandas 数据处理
    - Anthropic Claude API

    **数据周期**
    2024-07 ~ 2025-06

    **覆盖品类**
    运动户外 · 鞋靴

    **覆盖品牌**
    21 个真实市场品牌
    """, """
    **Tech Stack**
    - Streamlit + Plotly
    - Pandas
    - Anthropic Claude API

    **Data Period**
    2024-07 ~ 2025-06

    **Categories**
    Sportswear & Outdoor · Footwear

    **Brands Covered**
    21 real market brands
    """))
