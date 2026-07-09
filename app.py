# -*- coding: utf-8 -*-
"""
AI 电商经营分析与商品诊断系统
主入口文件 — 运行方式: streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="AI 电商经营分析与商品诊断系统",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🛍️ AI 电商经营分析与商品诊断系统")
st.caption("基于 Streamlit 与 Claude API 的电商经营看板和策略建议助手 · 作品集项目")

st.markdown("### 🎯 业务问题 Business Problem")
st.info(
    "品牌特卖电商平台在经营复盘中常遇到一个问题：**GMV 下滑时，传统 BI 看板只能看到整体销售额、流量和转化率的变化，"
    "但难以快速判断问题到底来自流量不足、商品转化承接不足、客单价下降，还是部分 SKU 拖累。**\n\n"
    "本项目模拟一个真实的品牌特卖电商经营场景，构建一个 AI 辅助的经营分析系统，"
    "用于**识别经营异常、定位问题商品、生成策略建议，并测算潜在 GMV 提升空间**。"
)

st.markdown(t(
    "## 🔗 分析链路 Analysis Workflow",
    "## 🔗 Analysis Workflow"
))

st.info(t(
    "**业务问题 → 指标体系 → 异常识别 → 商品诊断 → 策略建议 → 预期影响 → 后续追踪**",
    "**Business Problem → KPI Framework → Anomaly Detection → SKU Diagnosis → Strategy Recommendation → Expected Impact → Follow-up Tracking**"
))

st.markdown(t(
    "本项目遵循一个完整的经营分析闭环，目标不是单纯展示数据，而是帮助业务团队从 GMV 波动中定位问题、制定策略并验证效果。",
    "This project follows a structured business analytics workflow. The goal is not only to visualize data, but to help business teams diagnose GMV changes, prioritize actions, and validate business impact."
))

workflow_steps = [
    {
        "zh_title": "1. 业务问题",
        "en_title": "1. Business Problem",
        "zh_desc": "GMV 下滑时，传统 BI 看板通常只能看到整体销售额、流量和转化率变化，但难以快速判断问题到底来自流量不足、商品转化承接不足、客单价下降，还是部分 SKU 拖累。",
        "en_desc": "When GMV declines, traditional BI dashboards often show overall sales, traffic, and conversion changes, but do not clearly explain whether the issue comes from traffic, conversion, AOV, or underperforming SKUs."
    },
    {
        "zh_title": "2. 指标体系",
        "en_title": "2. KPI Framework",
        "zh_desc": "将 GMV 拆解为流量、订单量、转化率、客单价和退款率等核心指标，建立经营复盘的基础分析框架。",
        "en_desc": "Decompose GMV into key drivers such as traffic, orders, conversion rate, AOV, and refund rate to build the foundation for business review."
    },
    {
        "zh_title": "3. 异常识别",
        "en_title": "3. Anomaly Detection",
        "zh_desc": "在当前时间与渠道筛选条件下，识别 GMV 下滑、订单下降、转化率下降、流量与订单背离等经营异常。",
        "en_desc": "Identify business issues such as GMV decline, order drop, conversion rate decrease, and traffic-order mismatch under selected time and channel filters."
    },
    {
        "zh_title": "4. 商品诊断",
        "en_title": "4. SKU Diagnosis",
        "zh_desc": "基于“流量 × 转化率”四象限框架，识别高流量低转化拖累款，并进一步判断问题可能来自价格力、商品内容、库存状态或退款风险。",
        "en_desc": "Use a traffic × conversion quadrant framework to identify high-traffic low-conversion drag SKUs and diagnose potential issues in pricing, content, inventory, or refund risk."
    },
    {
        "zh_title": "5. 策略建议",
        "en_title": "5. Strategy Recommendation",
        "zh_desc": "基于经营异常和商品诊断结果，生成结构化经营复盘草稿与优先行动建议。",
        "en_desc": "Generate structured business review drafts and prioritized action recommendations based on KPI anomalies and SKU diagnosis results."
    },
    {
        "zh_title": "6. 预期影响",
        "en_title": "6. Expected Impact",
        "zh_desc": "通过 GMV uplift 测算器，估算转化率优化可能带来的潜在 GMV 增量，帮助判断策略优先级。",
        "en_desc": "Estimate potential GMV uplift from conversion rate improvement to help evaluate business opportunity size and action priority."
    },
    {
        "zh_title": "7. 后续追踪",
        "en_title": "7. Follow-up Tracking",
        "zh_desc": "定义后续监控指标和 A/B Test 验证方案，例如 CTR、CVR、GMV、退款率、活动 ROI 等，形成策略闭环。",
        "en_desc": "Define follow-up metrics and A/B test plans, such as CTR, CVR, GMV, refund rate, and campaign ROI, to close the strategy evaluation loop."
    },
]

for i in range(0, len(workflow_steps), 2):
    cols = st.columns(2)
    for col, step in zip(cols, workflow_steps[i:i + 2]):
        with col:
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #E5E7EB;
                    border-radius: 12px;
                    padding: 18px 18px 14px 18px;
                    margin-bottom: 14px;
                    background-color: #FFFFFF;
                    min-height: 155px;
                ">
                    <h4 style="margin-top: 0; margin-bottom: 10px;">
                        {t(step["zh_title"], step["en_title"])}
                    </h4>
                    <p style="color: #4B5563; line-height: 1.55; margin-bottom: 0;">
                        {t(step["zh_desc"], step["en_desc"])}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

st.divider()

st.markdown("")
st.markdown("### 📖 页面导览 Page Guide")

with st.container(border=True):
    st.markdown("""
**📊 生意大盘（Business Overview）**
：当前经营表现是否健康？问题主要出现在 GMV、流量、转化率还是客单价？
对应链路：指标体系 → 异常识别 → 初步归因
""")

with st.container(border=True):
    st.markdown("""
**🔍 商品诊断（Product Diagnosis）**
：哪些 SKU 正在拖累转化？问题可能来自价格、内容、库存还是退款风险？
对应链路：原因归因 → 问题定位
""")

with st.container(border=True):
    st.markdown("""
**🤖 AI 策略助手（AI Assistant）**
：基于当前异常和商品诊断，下一步应该采取什么策略？预期能带来多少 GMV 增量？如何验证效果？
对应链路：策略建议 → 预期影响 → 后续追踪
""")

st.divider()

st.markdown("### 关于本项目")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("""
    **数据背景**
    模拟真实品牌特卖闪购电商 App，覆盖运动户外与鞋靴两大类目下的 **21 个真实市场品牌**
    （耐克、阿迪达斯、安德玛、李宁、Vans、回力等），数据周期 **2024年12月 - 2025年12月**，
    月均 GMV 约 1,000 万元。

    全部数据均为**合成模拟数据**，基于真实业务逻辑与季节性规律建模生成
    （包含双11、618等真实大促节点），不涉及任何真实企业的商业数据。
    """)
with col_b:
    st.markdown("""
    **技术栈**
    - Streamlit + Plotly 数据看板
    - Pandas 数据处理与聚合
    - Anthropic Claude API 驱动 AI 策略生成
    """)

with st.sidebar:
    st.header("关于本项目")
    st.markdown("""
    **数据周期**
    2024-12 ~ 2025-12

    **覆盖品类**
    运动户外 · 鞋靴

    **覆盖品牌**
    21 个真实市场品牌
    """)
