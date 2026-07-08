# -*- coding: utf-8 -*-
"""生意大盘 — 平台经营总览"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import load_daily_business, load_sku_performance, fmt_wan, fmt_pct, pct_delta, language_toggle, t

st.set_page_config(page_title="生意大盘", page_icon="📊", layout="wide")
lang = language_toggle()
st.title(t("📊 生意大盘", "📊 Business Overview"))
st.caption(t("平台核心经营指标监控 · 多渠道流量拆解", "Core KPI monitoring · Multi-channel traffic breakdown"))

df = load_daily_business()

# ---- 筛选器 ----
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    date_range = st.date_input(
        t("选择日期范围", "Select date range"),
        value=(df["date"].max() - pd.Timedelta(days=90), df["date"].max()),
        min_value=df["date"].min(),
        max_value=df["date"].max(),
    )
with col_f2:
    channels_sel = st.multiselect(
        t("筛选渠道", "Filter channel"), options=df["channel"].unique().tolist(),
        default=df["channel"].unique().tolist()
    )

if len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    mask = (df["date"] >= start) & (df["date"] <= end) & (df["channel"].isin(channels_sel))
    fdf = df[mask].copy()
else:
    fdf = df[df["channel"].isin(channels_sel)].copy()

# 环比对比（跟"紧邻的上一个等长周期"比较，不是同比）
period_days = (fdf["date"].max() - fdf["date"].min()).days + 1
prev_start = fdf["date"].min() - pd.Timedelta(days=period_days)
prev_end = fdf["date"].min() - pd.Timedelta(days=1)
prev_df = df[(df["date"] >= prev_start) & (df["date"] <= prev_end) & (df["channel"].isin(channels_sel))]

st.caption(
    t(f"📅 当前区间：{fdf['date'].min().date()} ~ {fdf['date'].max().date()}（共{period_days}天）　"
      f"对比区间（环比，非同比）：{prev_start.date()} ~ {prev_end.date()}",
      f"📅 Current period: {fdf['date'].min().date()} ~ {fdf['date'].max().date()} ({period_days} days)　"
      f"Compared to (prior equal-length period, NOT year-over-year): {prev_start.date()} ~ {prev_end.date()}")
)

# ---- KPI 卡片 ----
total_gmv = fdf["gmv"].sum()
total_uv = fdf["uv"].sum()
total_orders = fdf["orders"].sum()
avg_cr = total_orders / total_uv if total_uv else 0
avg_aov = total_gmv / total_orders if total_orders else 0
avg_refund = (fdf["refund_rate"] * fdf["gmv"]).sum() / total_gmv if total_gmv else 0

prev_gmv = prev_df["gmv"].sum()
prev_uv = prev_df["uv"].sum()
prev_orders = prev_df["orders"].sum()
prev_cr = prev_orders / prev_uv if prev_uv else 0
prev_aov = prev_gmv / prev_orders if prev_orders else 0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(t("GMV", "GMV"), fmt_wan(total_gmv) if lang == "zh" else f"¥{total_gmv/10000:,.1f}K",
          f"{pct_delta(total_gmv, prev_gmv)*100:+.1f}%" if pct_delta(total_gmv, prev_gmv) is not None else None,
          help=t("与上一个等长周期（环比）对比，非同比", "Compared to prior equal-length period (period-over-period, not YoY)"))
c2.metric(t("UV", "UV"), f"{total_uv:,.0f}", f"{pct_delta(total_uv, prev_uv)*100:+.1f}%" if pct_delta(total_uv, prev_uv) is not None else None,
          help=t("与上一个等长周期（环比）对比，非同比", "Compared to prior equal-length period (period-over-period, not YoY)"))
c3.metric(t("支付转化率", "Conversion Rate"), fmt_pct(avg_cr), f"{(avg_cr-prev_cr)*100:+.2f}pp" if prev_uv else None,
          help=t("pp = 百分点差值，与上一个等长周期（环比）对比", "pp = percentage points, vs. prior equal-length period"))
c4.metric(t("客单价 AOV", "AOV"), f"¥{avg_aov:,.0f}", f"{pct_delta(avg_aov, prev_aov)*100:+.1f}%" if pct_delta(avg_aov, prev_aov) is not None else None,
          help=t("与上一个等长周期（环比）对比，非同比", "Compared to prior equal-length period (period-over-period, not YoY)"))
c5.metric(t("退款率", "Refund Rate"), fmt_pct(avg_refund), help=t("当前区间内按GMV加权的平均退款率", "GMV-weighted average refund rate in the current period"))

st.divider()

# ============================================================
# 经营健康度检查 Business Health Check
# ============================================================
st.subheader(t("🩺 经营健康度检查", "🩺 Business Health Check"))
st.caption(t(
    "本模块基于当前筛选条件（时间/渠道），对所选范围内的经营表现进行健康度检查，"
    "识别 GMV 下滑、转化率下降、流量与订单背离、高流量低转化商品等问题。",
    "This module performs a business health check under the current filters (date/channel), "
    "identifying issues such as GMV decline, conversion rate drop, traffic-order mismatch, "
    "and high-traffic low-conversion SKUs."
))

alerts = []

# --- 第一层：KPI 环比波动检查 ---
gmv_chg = pct_delta(total_gmv, prev_gmv)
cr_chg = pct_delta(avg_cr, prev_cr)
aov_chg = pct_delta(avg_aov, prev_aov)
orders_chg = pct_delta(total_orders, prev_orders)
uv_chg = pct_delta(total_uv, prev_uv)

if gmv_chg is not None and gmv_chg < -0.15:
    alerts.append(("high", t(f"🔴 GMV 环比下降 {gmv_chg*100:.1f}%", f"🔴 GMV declined {gmv_chg*100:.1f}% period-over-period"),
                    t("当前筛选范围下，GMV 较上一周期明显下降，建议进一步检查流量、转化率和客单价变化。",
                      "GMV dropped notably vs. the prior period. Check traffic, conversion rate, and AOV changes.")))
if cr_chg is not None and cr_chg < -0.10:
    alerts.append(("medium", t(f"🟡 转化率环比下降 {abs(cr_chg)*100:.1f}%", f"🟡 Conversion rate declined {abs(cr_chg)*100:.1f}% period-over-period"),
                    t("转化效率下降，可能与商品承接、价格力、库存或流量质量有关。",
                      "Conversion efficiency dropped — possibly related to product content, pricing, stock, or traffic quality.")))
if aov_chg is not None and aov_chg < -0.10:
    alerts.append(("medium", t(f"🟡 客单价环比下降 {abs(aov_chg)*100:.1f}%", f"🟡 AOV declined {abs(aov_chg)*100:.1f}% period-over-period"),
                    t("客单价明显下降，需关注是否折扣力度过大或高客单商品占比降低。",
                      "AOV dropped notably — check discount depth or shift away from higher-priced items.")))
if orders_chg is not None and orders_chg < -0.15:
    alerts.append(("high", t(f"🔴 订单量环比下降 {abs(orders_chg)*100:.1f}%", f"🔴 Order volume declined {abs(orders_chg)*100:.1f}% period-over-period"),
                    t("订单量明显下降，建议检查是否有活动资源减少或流量下滑导致。",
                      "Order volume dropped notably — check for reduced campaign resources or traffic decline.")))

# --- 第二层：流量-转化背离检查 ---
if uv_chg is not None and uv_chg > 0.20 and (orders_chg is None or orders_chg < 0.05):
    alerts.append(("medium", t("🟡 流量-转化背离", "🟡 Traffic-Conversion Mismatch"),
                    t(f"当前筛选条件下，流量环比增长 {uv_chg*100:.1f}%，但订单量仅增长 "
                      f"{(orders_chg*100 if orders_chg is not None else 0):.1f}%，说明新增流量未被有效转化。"
                      "建议检查流量来源质量、商品价格力、页面卖点和库存状态。",
                      f"Traffic grew {uv_chg*100:.1f}% period-over-period, but orders only grew "
                      f"{(orders_chg*100 if orders_chg is not None else 0):.1f}%, meaning new traffic isn't converting well. "
                      "Check traffic source quality, pricing, page appeal, and stock levels.")))

# --- 第三层：SKU 问题识别（联动商品诊断页）---
sku_all = load_sku_performance()
sku_in_range = sku_all[(sku_all["start_date"] >= start) & (sku_all["start_date"] <= end)]
n_problem_sku = 0
if len(sku_in_range) > 10:
    s_agg = sku_in_range.groupby("sku_id").agg(uv=("uv", "sum"), orders=("orders", "sum")).reset_index()
    s_agg["cr"] = s_agg["orders"] / s_agg["uv"]
    uv_t = s_agg["uv"].quantile(0.7)
    cr_t = s_agg["cr"].quantile(0.3)
    n_problem_sku = ((s_agg["uv"] >= uv_t) & (s_agg["cr"] <= cr_t)).sum()
    if n_problem_sku > 0:
        alerts.append(("high", t(f"🔴 发现 {n_problem_sku} 个高流量低转化 SKU", f"🔴 Found {n_problem_sku} high-traffic low-conversion SKUs"),
                        t("这些商品获得了较高曝光，但转化率低于当前范围均值，建议优先检查商品标题、主图、价格力和库存状态。"
                          "→ 详见「商品诊断」页面获取完整清单。",
                          "These SKUs received high exposure but underperform on conversion. Check titles, main images, "
                          "pricing, and stock. → See the Product Diagnosis page for the full list.")))

# --- 健康度评分 ---
score = 100
for sev, _, _ in alerts:
    score -= 20 if sev == "high" else (10 if sev == "medium" else 5)
score = max(score, 0)
score_label = t("🟢 健康", "🟢 Healthy") if score >= 80 else (t("🟡 需要关注", "🟡 Needs Attention") if score >= 50 else t("🔴 需要立即处理", "🔴 Needs Immediate Action"))

sh1, sh2 = st.columns([1, 3])
with sh1:
    st.metric(t("经营健康度评分", "Business Health Score"), f"{score} / 100", score_label, delta_color="off")
with sh2:
    if alerts:
        n_high = sum(1 for a in alerts if a[0] == "high")
        n_med = sum(1 for a in alerts if a[0] == "medium")
        st.info(t(f"当前筛选范围下发现 {n_high} 个高优先级问题、{n_med} 个中优先级问题。",
                   f"Found {n_high} high-priority and {n_med} medium-priority issues under current filters."))
    else:
        st.success(t("当前筛选范围下未发现明显异常，各项核心指标表现平稳。",
                       "No significant issues detected under current filters — core metrics are stable."))

for sev, title, msg in alerts:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(msg)

if n_problem_sku > 0:
    st.page_link("pages/2_Product_Diagnosis.py", label=t("👉 前往「商品诊断」页查看完整拖累款清单", "👉 Go to Product Diagnosis for the full drag-SKU list"))

st.divider()

# ---- GMV趋势图（双轴：GMV柱 + 转化率线） ----
daily_agg = fdf.groupby("date").agg(
    gmv=("gmv", "sum"), uv=("uv", "sum"), orders=("orders", "sum"),
    is_festival=("is_festival", "max"), festival_name=("festival_name", "max")
).reset_index()
daily_agg["conversion_rate"] = daily_agg["orders"] / daily_agg["uv"]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=daily_agg["date"], y=daily_agg["gmv"]/10000, name=t("GMV(万元)", "GMV(¥0K)"),
    marker_color=daily_agg["is_festival"].map({True: "#f59e0b", False: "#93c5fd"}),
))
fig.add_trace(go.Scatter(
    x=daily_agg["date"], y=daily_agg["conversion_rate"]*100, name=t("转化率(%)", "Conversion Rate(%)"),
    yaxis="y2", line=dict(color="#059669", width=2),
))
fig.update_layout(
    title=t("每日 GMV 趋势（橙色柱=大促日）与转化率", "Daily GMV Trend (orange = promo day) & Conversion Rate"),
    yaxis=dict(title=t("GMV(万元)", "GMV(¥0K)")),
    yaxis2=dict(title=t("转化率(%)", "Conversion Rate(%)"), overlaying="y", side="right"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
    height=420, hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True)

# ---- 月度趋势 + 渠道拆分 ----
col_a, col_b = st.columns(2)

with col_a:
    monthly = df[df["channel"].isin(channels_sel)].copy()
    monthly["month"] = monthly["date"].dt.to_period("M").astype(str)
    monthly_agg = monthly.groupby("month").agg(gmv=("gmv", "sum")).reset_index()
    monthly_agg["mom"] = monthly_agg["gmv"].pct_change()
    fig2 = px.bar(monthly_agg, x="month", y="gmv", title=t("月度 GMV 走势(元)", "Monthly GMV Trend(¥)"),
                  color_discrete_sequence=["#2563eb"])
    fig2.update_layout(height=360)
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    ch_agg = fdf.groupby("channel").agg(gmv=("gmv", "sum"), uv=("uv", "sum")).reset_index()
    ch_agg["conversion_rate"] = fdf.groupby("channel").apply(
        lambda x: x["orders"].sum() / x["uv"].sum(), include_groups=False
    ).values
    fig3 = px.bar(ch_agg.sort_values("gmv"), x="gmv", y="channel", orientation="h",
                  title=t("各渠道 GMV 贡献", "GMV Contribution by Channel"), color="conversion_rate",
                  color_continuous_scale="Blues", labels={"gmv": t("GMV(元)", "GMV(¥)"), "channel": ""})
    fig3.update_layout(height=360)
    st.plotly_chart(fig3, use_container_width=True)

# ---- 渠道效率对比表 ----
st.subheader(t("渠道效率对比", "Channel Efficiency Comparison"))
col_uv, col_orders, col_gmv, col_refund = t("UV", "UV"), t("订单数", "Orders"), t("GMV", "GMV"), t("退款率", "Refund Rate")
ch_table = fdf.groupby("channel").agg(
    **{col_uv: ("uv", "sum"), col_orders: ("orders", "sum"), col_gmv: ("gmv", "sum"), col_refund: ("refund_rate", "mean")}
).reset_index()
col_cr, col_aov = t("转化率", "CVR"), t("客单价", "AOV")
ch_table[col_cr] = (ch_table[col_orders] / ch_table[col_uv] * 100).round(2).astype(str) + "%"
ch_table[col_aov] = (ch_table[col_gmv] / ch_table[col_orders]).round(1)
ch_table[col_gmv] = ch_table[col_gmv].round(0)
ch_table[col_refund] = (ch_table[col_refund] * 100).round(2).astype(str) + "%"
ch_table = ch_table.rename(columns={"channel": t("渠道", "Channel")})
st.dataframe(
    ch_table[[t("渠道", "Channel"), col_uv, col_orders, col_gmv, col_cr, col_aov, col_refund]],
    use_container_width=True, hide_index=True
)
