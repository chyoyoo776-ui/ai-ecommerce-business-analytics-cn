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

st.markdown("### 🔗 分析链路 Analysis Workflow")
st.markdown("""
本项目遵循完整的经营分析闭环：

1. **业务问题**  
   识别品牌特卖电商场景下 GMV 下滑的可能原因。

2. **指标体系**  
   将 GMV 拆解为流量、转化率、订单量和客单价。

3. **经营健康度检查**  
   在当前时间/渠道筛选条件下识别 KPI 异常波动。

4. **商品诊断**  
   基于“流量 × 转化率”四象限框架识别高流量低转化拖累款。

5. **策略建议**  
   接入 Claude API，基于经营异常和商品诊断结果生成结构化运营建议。

6. **预期影响**  
   通过 GMV uplift 测算评估转化率优化带来的潜在增量。

7. **后续追踪**  
   定义后续监控指标和 A/B Test 验证方案，形成策略闭环。
""")

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
