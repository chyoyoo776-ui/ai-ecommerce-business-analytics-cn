# -*- coding: utf-8 -*-
"""商品诊断 — SKU 四象限分层，识别拖累款"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import load_sku_performance, load_brand_campaigns, fmt_wan, fmt_pct

st.set_page_config(page_title="商品诊断", page_icon="🔍", layout="wide")
st.title("🔍 商品诊断 · SKU 分层")
st.caption("识别高流量低转化的\"拖累款\"商品，定位问题根因")

st.info(
    "本页基于\"流量 × 转化率\"四象限框架进行商品诊断，识别高流量低转化拖累款，"
    "并辅助判断问题可能来自商品内容、价格力、库存状态或售后风险。"
)

with st.container(border=True):
    st.markdown("""
**💡Why this matters**

在电商经营中，低 GMV 商品不一定最优先处理。更值得优先处理的是**"高流量低转化"商品**，
因为它们已经获得曝光，但没有有效转化，说明可能存在商品内容、价格、库存或活动利益点问题。
优化这类 SKU 往往比给低流量商品增加曝光更具短期 GMV 提升潜力。
""")

sku = load_sku_performance()

# ---- 筛选器 ----
col0, col1, col2, col3 = st.columns([1.3, 1, 1, 1])
with col0:
    date_range = st.date_input(
        "场次开始日期范围",
        value=(sku["start_date"].min(), sku["start_date"].max()),
        min_value=sku["start_date"].min(),
        max_value=sku["start_date"].max(),
    )
with col1:
    category_sel = st.multiselect("类目", sku["category"].unique().tolist(),
                                   default=sku["category"].unique().tolist())
with col2:
    brand_options = sku[sku["category"].isin(category_sel)]["brand"].unique().tolist()
    brand_sel = st.multiselect("品牌", brand_options, default=brand_options)
with col3:
    camp_type_sel = st.multiselect("场次类型", sku["campaign_type"].unique().tolist(),
                                    default=sku["campaign_type"].unique().tolist())

if len(date_range) == 2:
    d_start, d_end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    date_mask = (sku["start_date"] >= d_start) & (sku["start_date"] <= d_end)
else:
    date_mask = pd.Series(True, index=sku.index)

fsku = sku[
    date_mask &
    sku["category"].isin(category_sel) &
    sku["brand"].isin(brand_sel) &
    sku["campaign_type"].isin(camp_type_sel)
].copy()

if fsku.empty:
    st.warning("当前筛选条件下没有数据，请调整日期范围或筛选项。")
    st.stop()

st.caption(f"当前分析范围：{date_mask.sum()} 条场次-商品记录，覆盖场次开始日期 {date_range[0]} ~ {date_range[1] if len(date_range)==2 else ''}")

# 按SKU聚合（同一SKU可能出现在多场活动中，取汇总表现）
sku_agg = fsku.groupby(["sku_id", "product_name", "brand", "category", "sub_category"]).agg(
    total_uv=("uv", "sum"), total_orders=("orders", "sum"), total_gmv=("gmv", "sum"),
    avg_ctr=("ctr", "mean"), avg_refund=("refund_rate", "mean"),
    avg_sell_through=("sell_through_rate", "mean"),
    overpriced_flag=("overpriced_flag", "max"), weak_listing_flag=("weak_listing_flag", "max"),
    n_campaigns=("campaign_id", "nunique"),
).reset_index()
sku_agg["conversion_rate"] = sku_agg["total_orders"] / sku_agg["total_uv"]

# ---- 四象限阈值 ----
uv_median = sku_agg["total_uv"].median()
cr_median = sku_agg["conversion_rate"].median()

def quadrant_code(row):
    high_uv = row["total_uv"] >= uv_median
    high_cr = row["conversion_rate"] >= cr_median
    if high_uv and not high_cr:
        return "drag"
    elif high_uv and high_cr:
        return "star"
    elif not high_uv and high_cr:
        return "potential"
    else:
        return "edge"

QUADRANT_LABELS = {
    "drag": "🔴 拖累款(高流量低转化)", "star": "🟢 明星款(高流量高转化)",
    "potential": "🔵 潜力款(低流量高转化)", "edge": "⚪ 边缘款(低流量低转化)",
}

sku_agg["quadrant_code"] = sku_agg.apply(quadrant_code, axis=1)
sku_agg["quadrant"] = sku_agg["quadrant_code"].map(QUADRANT_LABELS)

# ---- KPI 概览 ----
n_drag = (sku_agg["quadrant_code"] == "drag").sum()
drag_uv_share = sku_agg.loc[sku_agg["quadrant_code"] == "drag", "total_uv"].sum() / sku_agg["total_uv"].sum()
n_star = (sku_agg["quadrant_code"] == "star").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric("分析 SKU 总数", f"{len(sku_agg):,}")
c2.metric("🔴 拖累款数量", f"{n_drag}", f"占总流量 {drag_uv_share*100:.1f}%", delta_color="off")
c3.metric("🟢 明星款数量", f"{n_star}")
c4.metric("平均动销率", fmt_pct(sku_agg["avg_sell_through"].mean()))

st.divider()

# ---- 四象限散点图（核心图） ----
st.subheader("四象限分析：UV × 转化率")
fig = px.scatter(
    sku_agg, x="total_uv", y="conversion_rate", color="quadrant", size="total_gmv",
    hover_data={"product_name": True, "brand": True, "total_gmv": ":.0f", "avg_refund": ":.2%"},
    color_discrete_map={
        QUADRANT_LABELS["drag"]: "#ef4444", QUADRANT_LABELS["star"]: "#22c55e",
        QUADRANT_LABELS["potential"]: "#3b82f6", QUADRANT_LABELS["edge"]: "#9ca3af",
    },
    labels={"total_uv": "累计UV", "conversion_rate": "转化率"},
    height=550,
)
fig.add_vline(x=uv_median, line_dash="dash", line_color="gray", annotation_text="UV中位数")
fig.add_hline(y=cr_median, line_dash="dash", line_color="gray", annotation_text="转化率中位数")
fig.update_yaxes(tickformat=".1%")
st.plotly_chart(fig, use_container_width=True)

# ---- 象限行动对照表 ----
st.markdown("#### 📋 四象限业务动作对照表")
quadrant_table = pd.DataFrame([
    ["🟢 明星款", "高流量高转化", "表现优秀", "保持资源、优先补货、扩大曝光"],
    ["🔴 拖累款", "高流量低转化", "流量承接不足", "优先优化标题、主图、价格力、库存"],
    ["🔵 潜力款", "低流量高转化", "有转化潜力，曝光不足", "增加曝光、参与活动、资源倾斜"],
    ["⚪ 边缘款", "低流量低转化", "边缘商品，投入产出比低", "控制资源投入、观察或考虑清退"],
], columns=["象限", "特征", "含义", "建议动作"])
st.dataframe(quadrant_table, use_container_width=True, hide_index=True)

# ---- 拖累款诊断表 ----
st.subheader("🔴 拖累款商品清单 · 问题诊断")
drag_skus = sku_agg[sku_agg["quadrant_code"] == "drag"].copy()
drag_skus = drag_skus.sort_values("total_uv", ascending=False)

def diagnose(row):
    reasons = []
    if row["overpriced_flag"]:
        reasons.append("定价偏高")
    if row["weak_listing_flag"]:
        reasons.append("图文/详情页质量弱")
    if row["avg_ctr"] < fsku["ctr"].median() * 0.8:
        reasons.append("点击率偏低")
    if row["avg_refund"] > fsku["refund_rate"].median() * 1.3:
        reasons.append("退款率偏高")
    return "、".join(reasons) if reasons else "需人工复核"

drag_skus["疑似问题"] = drag_skus.apply(diagnose, axis=1)

display_cols = drag_skus[[
    "product_name", "brand", "category", "total_uv", "conversion_rate",
    "total_gmv", "avg_refund", "疑似问题"
]].rename(columns={
    "product_name": "商品名", "brand": "品牌", "category": "类目",
    "total_uv": "累计UV", "conversion_rate": "转化率", "total_gmv": "GMV",
    "avg_refund": "退款率"
})
display_cols["转化率"] = (display_cols["转化率"] * 100).round(2).astype(str) + "%"
display_cols["退款率"] = (display_cols["退款率"] * 100).round(2).astype(str) + "%"
display_cols["GMV"] = display_cols["GMV"].round(0)

st.dataframe(display_cols.head(30), use_container_width=True, hide_index=True)

st.download_button(
    "下载完整拖累款清单 (CSV)",
    drag_skus.to_csv(index=False, encoding="utf-8-sig"),
    file_name="拖累款商品清单.csv", mime="text/csv"
)

# ---- 品牌/类目层 四象限分布 ----
st.divider()
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("各品牌拖累款占比")
    brand_quad = sku_agg.groupby(["brand", "quadrant_code"]).size().reset_index(name="count")
    brand_total = sku_agg.groupby("brand").size().reset_index(name="total")
    brand_quad = brand_quad.merge(brand_total, on="brand")
    brand_quad["pct"] = brand_quad["count"] / brand_quad["total"]
    drag_by_brand = brand_quad[brand_quad["quadrant_code"] == "drag"].sort_values("pct", ascending=False)
    fig4 = px.bar(drag_by_brand.head(12), x="pct", y="brand", orientation="h",
                  labels={"pct": "拖累款占比", "brand": ""}, color="pct",
                  color_continuous_scale="Reds")
    fig4.update_xaxes(tickformat=".0%")
    fig4.update_layout(height=420)
    st.plotly_chart(fig4, use_container_width=True)

with col_b:
    st.subheader("动销率 vs 折扣率")
    fdf2 = fsku.groupby(["sku_id", "product_name"]).agg(
        discount_rate=("discount_rate", "mean"), sell_through=("sell_through_rate", "mean"),
        stock=("stock_qty", "mean"), gmv=("gmv", "sum")
    ).reset_index()
    fig5 = px.scatter(fdf2, x="discount_rate", y="sell_through", size="stock",
                       hover_data=["product_name"],
                       labels={"discount_rate": "折扣率", "sell_through": "动销率"},
                       color="sell_through", color_continuous_scale="RdYlGn", height=420)
    fig5.update_xaxes(tickformat=".0%")
    fig5.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig5, use_container_width=True)
    st.caption("气泡越大代表库存越高 — 左下方大气泡为\"高折扣仍低动销\"的清仓风险库存")

with st.expander("📐 拖累款判定逻辑说明"):
    st.markdown("""
    - **判定逻辑**：流量高于中位数、但转化率低于中位数的商品，代表平台已经给了曝光资源，
      但商品本身未能承接住流量，是资源错配的直接体现。
    - **诊断维度**参考真实业务场景中的常见转化率影响因素：定价合理性、详情页质量、点击率、退款率，
      通过多因子交叉判断疑似问题根因，而不是单一指标下结论。
    - **品牌维度**的拖累款占比排名可以直接用于资源分配决策：占比持续偏高的品牌需要约谈或调整供给结构。
    """)
