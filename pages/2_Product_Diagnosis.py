# -*- coding: utf-8 -*-
"""商品诊断 — SKU 四象限分层，识别拖累款"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import load_sku_performance, load_brand_campaigns, fmt_wan, fmt_pct, language_toggle, t

st.set_page_config(page_title="商品诊断", page_icon="🔍", layout="wide")
lang = language_toggle()
st.title(t("🔍 商品诊断 · SKU 分层", "🔍 Product Diagnosis · SKU Segmentation"))
st.caption(t("识别高流量低转化的\"拖累款\"商品，定位问题根因", "Identify high-traffic low-conversion \"drag SKUs\" and diagnose root causes"))

sku = load_sku_performance()

# ---- 筛选器 ----
col0, col1, col2, col3 = st.columns([1.3, 1, 1, 1])
with col0:
    date_range = st.date_input(
        t("场次开始日期范围", "Campaign Start Date Range"),
        value=(sku["start_date"].min(), sku["start_date"].max()),
        min_value=sku["start_date"].min(),
        max_value=sku["start_date"].max(),
    )
with col1:
    category_sel = st.multiselect(t("类目", "Category"), sku["category"].unique().tolist(),
                                   default=sku["category"].unique().tolist())
with col2:
    brand_options = sku[sku["category"].isin(category_sel)]["brand"].unique().tolist()
    brand_sel = st.multiselect(t("品牌", "Brand"), brand_options, default=brand_options)
with col3:
    camp_type_sel = st.multiselect(t("场次类型", "Campaign Type"), sku["campaign_type"].unique().tolist(),
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
    st.warning(t("当前筛选条件下没有数据，请调整日期范围或筛选项。", "No data under the current filters — please adjust the date range or filters."))
    st.stop()

st.caption(t(
    f"当前分析范围：{date_mask.sum()} 条场次-商品记录，覆盖场次开始日期 {date_range[0]} ~ {date_range[1] if len(date_range)==2 else ''}",
    f"Current scope: {date_mask.sum()} campaign-SKU records, campaign start dates {date_range[0]} ~ {date_range[1] if len(date_range)==2 else ''}"
))

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
# 内部用语言无关的代码存储象限（drag/star/potential/edge），显示时再按当前语言翻译，
# 避免中英文切换导致后续基于中文字符串的筛选/比较逻辑失效
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
    "drag": t("🔴 拖累款(高流量低转化)", "🔴 Drag SKU (High Traffic, Low CVR)"),
    "star": t("🟢 明星款(高流量高转化)", "🟢 Star SKU (High Traffic, High CVR)"),
    "potential": t("🔵 潜力款(低流量高转化)", "🔵 Potential SKU (Low Traffic, High CVR)"),
    "edge": t("⚪ 边缘款(低流量低转化)", "⚪ Edge SKU (Low Traffic, Low CVR)"),
}

sku_agg["quadrant_code"] = sku_agg.apply(quadrant_code, axis=1)
sku_agg["quadrant"] = sku_agg["quadrant_code"].map(QUADRANT_LABELS)

# ---- KPI 概览 ----
n_drag = (sku_agg["quadrant_code"] == "drag").sum()
drag_uv_share = sku_agg.loc[sku_agg["quadrant_code"] == "drag", "total_uv"].sum() / sku_agg["total_uv"].sum()
n_star = (sku_agg["quadrant_code"] == "star").sum()

c1, c2, c3, c4 = st.columns(4)
c1.metric(t("分析 SKU 总数", "SKUs Analyzed"), f"{len(sku_agg):,}")
c2.metric(t("🔴 拖累款数量", "🔴 Drag SKUs"), f"{n_drag}", t(f"占总流量 {drag_uv_share*100:.1f}%", f"{drag_uv_share*100:.1f}% of total traffic"), delta_color="off")
c3.metric(t("🟢 明星款数量", "🟢 Star SKUs"), f"{n_star}")
c4.metric(t("平均动销率", "Avg. Sell-Through Rate"), fmt_pct(sku_agg["avg_sell_through"].mean()))

st.divider()

# ---- 四象限散点图（核心图） ----
st.subheader(t("四象限分析：UV × 转化率", "Four-Quadrant Analysis: UV × Conversion Rate"))
fig = px.scatter(
    sku_agg, x="total_uv", y="conversion_rate", color="quadrant", size="total_gmv",
    hover_data={"product_name": True, "brand": True, "total_gmv": ":.0f", "avg_refund": ":.2%"},
    color_discrete_map={
        QUADRANT_LABELS["drag"]: "#ef4444", QUADRANT_LABELS["star"]: "#22c55e",
        QUADRANT_LABELS["potential"]: "#3b82f6", QUADRANT_LABELS["edge"]: "#9ca3af",
    },
    labels={"total_uv": t("累计UV", "Total UV"), "conversion_rate": t("转化率", "Conversion Rate")},
    height=550,
)
fig.add_vline(x=uv_median, line_dash="dash", line_color="gray", annotation_text=t("UV中位数", "UV Median"))
fig.add_hline(y=cr_median, line_dash="dash", line_color="gray", annotation_text=t("转化率中位数", "CVR Median"))
fig.update_yaxes(tickformat=".1%")
st.plotly_chart(fig, use_container_width=True)

# ---- 拖累款诊断表 ----
st.subheader(t("🔴 拖累款商品清单 · 问题诊断", "🔴 Drag SKU List · Root-Cause Diagnosis"))
drag_skus = sku_agg[sku_agg["quadrant_code"] == "drag"].copy()
drag_skus = drag_skus.sort_values("total_uv", ascending=False)

def diagnose(row):
    reasons = []
    if row["overpriced_flag"]:
        reasons.append(t("定价偏高", "Overpriced"))
    if row["weak_listing_flag"]:
        reasons.append(t("图文/详情页质量弱", "Weak listing content"))
    if row["avg_ctr"] < fsku["ctr"].median() * 0.8:
        reasons.append(t("点击率偏低", "Low CTR"))
    if row["avg_refund"] > fsku["refund_rate"].median() * 1.3:
        reasons.append(t("退款率偏高", "High refund rate"))
    return ("、" if lang == "zh" else ", ").join(reasons) if reasons else t("需人工复核", "Needs manual review")

col_issue = t("疑似问题", "Suspected Issue")
drag_skus[col_issue] = drag_skus.apply(diagnose, axis=1)

col_name, col_brand, col_cat = t("商品名", "Product"), t("品牌", "Brand"), t("类目", "Category")
col_uv, col_cr, col_gmv, col_refund = t("累计UV", "Total UV"), t("转化率", "CVR"), t("GMV", "GMV"), t("退款率", "Refund Rate")

display_cols = drag_skus[[
    "product_name", "brand", "category", "total_uv", "conversion_rate",
    "total_gmv", "avg_refund", col_issue
]].rename(columns={
    "product_name": col_name, "brand": col_brand, "category": col_cat,
    "total_uv": col_uv, "conversion_rate": col_cr, "total_gmv": col_gmv,
    "avg_refund": col_refund
})
display_cols[col_cr] = (display_cols[col_cr] * 100).round(2).astype(str) + "%"
display_cols[col_refund] = (display_cols[col_refund] * 100).round(2).astype(str) + "%"
display_cols[col_gmv] = display_cols[col_gmv].round(0)

st.dataframe(display_cols.head(30), use_container_width=True, hide_index=True)

st.download_button(
    t("下载完整拖累款清单 (CSV)", "Download Full Drag-SKU List (CSV)"),
    drag_skus.to_csv(index=False, encoding="utf-8-sig"),
    file_name="drag_skus.csv", mime="text/csv"
)

# ---- 品牌/类目层 四象限分布 ----
st.divider()
col_a, col_b = st.columns(2)
with col_a:
    st.subheader(t("各品牌拖累款占比", "Drag-SKU Share by Brand"))
    brand_quad = sku_agg.groupby(["brand", "quadrant_code"]).size().reset_index(name="count")
    brand_total = sku_agg.groupby("brand").size().reset_index(name="total")
    brand_quad = brand_quad.merge(brand_total, on="brand")
    brand_quad["pct"] = brand_quad["count"] / brand_quad["total"]
    drag_by_brand = brand_quad[brand_quad["quadrant_code"] == "drag"].sort_values("pct", ascending=False)
    fig4 = px.bar(drag_by_brand.head(12), x="pct", y="brand", orientation="h",
                  labels={"pct": t("拖累款占比", "Drag-SKU Share"), "brand": ""}, color="pct",
                  color_continuous_scale="Reds")
    fig4.update_xaxes(tickformat=".0%")
    fig4.update_layout(height=420)
    st.plotly_chart(fig4, use_container_width=True)

with col_b:
    st.subheader(t("动销率 vs 折扣率", "Sell-Through Rate vs. Discount Rate"))
    fdf2 = fsku.groupby(["sku_id", "product_name"]).agg(
        discount_rate=("discount_rate", "mean"), sell_through=("sell_through_rate", "mean"),
        stock=("stock_qty", "mean"), gmv=("gmv", "sum")
    ).reset_index()
    fig5 = px.scatter(fdf2, x="discount_rate", y="sell_through", size="stock",
                       hover_data=["product_name"],
                       labels={"discount_rate": t("折扣率", "Discount Rate"), "sell_through": t("动销率", "Sell-Through Rate")},
                       color="sell_through", color_continuous_scale="RdYlGn", height=420)
    fig5.update_xaxes(tickformat=".0%")
    fig5.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig5, use_container_width=True)
    st.caption(t("气泡越大代表库存越高 — 左下方大气泡为\"高折扣仍低动销\"的清仓风险库存",
                 "Larger bubbles indicate higher stock — large bubbles in the lower-left are clearance-risk inventory (\"deep discount, still low sell-through\")"))

