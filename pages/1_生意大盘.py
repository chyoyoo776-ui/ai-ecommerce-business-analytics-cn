# -*- coding: utf-8 -*-
"""生意大盘 — 平台经营总览"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import load_daily_business, fmt_wan, fmt_pct, pct_delta

st.set_page_config(page_title="生意大盘", page_icon="📊", layout="wide")
st.title("📊 生意大盘")
st.caption("平台核心经营指标监控 · 多渠道流量拆解")

df = load_daily_business()

# ---- 筛选器 ----
col_f1, col_f2 = st.columns([2, 1])
with col_f1:
    date_range = st.date_input(
        "选择日期范围",
        value=(df["date"].max() - pd.Timedelta(days=90), df["date"].max()),
        min_value=df["date"].min(),
        max_value=df["date"].max(),
    )
with col_f2:
    channels_sel = st.multiselect(
        "筛选渠道", options=df["channel"].unique().tolist(),
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
    f"📅 当前区间：{fdf['date'].min().date()} ~ {fdf['date'].max().date()}（共{period_days}天）　"
    f"对比区间（环比，非同比）：{prev_start.date()} ~ {prev_end.date()}"
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
c1.metric("GMV", fmt_wan(total_gmv), f"{pct_delta(total_gmv, prev_gmv)*100:+.1f}%" if pct_delta(total_gmv, prev_gmv) is not None else None,
          help="与上一个等长周期（环比）对比，非同比")
c2.metric("UV", f"{total_uv:,.0f}", f"{pct_delta(total_uv, prev_uv)*100:+.1f}%" if pct_delta(total_uv, prev_uv) is not None else None,
          help="与上一个等长周期（环比）对比，非同比")
c3.metric("支付转化率", fmt_pct(avg_cr), f"{(avg_cr-prev_cr)*100:+.2f}pp" if prev_uv else None,
          help="pp = 百分点差值，与上一个等长周期（环比）对比")
c4.metric("客单价 AOV", f"¥{avg_aov:,.0f}", f"{pct_delta(avg_aov, prev_aov)*100:+.1f}%" if pct_delta(avg_aov, prev_aov) is not None else None,
          help="与上一个等长周期（环比）对比，非同比")
c5.metric("退款率", fmt_pct(avg_refund), help="当前区间内按GMV加权的平均退款率")

st.divider()

# ---- GMV趋势图（双轴：GMV柱 + 转化率线） ----
daily_agg = fdf.groupby("date").agg(
    gmv=("gmv", "sum"), uv=("uv", "sum"), orders=("orders", "sum"),
    is_festival=("is_festival", "max"), festival_name=("festival_name", "max")
).reset_index()
daily_agg["conversion_rate"] = daily_agg["orders"] / daily_agg["uv"]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=daily_agg["date"], y=daily_agg["gmv"]/10000, name="GMV(万元)",
    marker_color=daily_agg["is_festival"].map({True: "#f59e0b", False: "#93c5fd"}),
))
fig.add_trace(go.Scatter(
    x=daily_agg["date"], y=daily_agg["conversion_rate"]*100, name="转化率(%)",
    yaxis="y2", line=dict(color="#059669", width=2),
))
fig.update_layout(
    title="每日 GMV 趋势（橙色柱=大促日）与转化率",
    yaxis=dict(title="GMV(万元)"),
    yaxis2=dict(title="转化率(%)", overlaying="y", side="right"),
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
    fig2 = px.bar(monthly_agg, x="month", y="gmv", title="月度 GMV 走势(元)",
                  color_discrete_sequence=["#2563eb"])
    fig2.update_layout(height=360)
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    ch_agg = fdf.groupby("channel").agg(gmv=("gmv", "sum"), uv=("uv", "sum")).reset_index()
    ch_agg["conversion_rate"] = fdf.groupby("channel").apply(
        lambda x: x["orders"].sum() / x["uv"].sum(), include_groups=False
    ).values
    fig3 = px.bar(ch_agg.sort_values("gmv"), x="gmv", y="channel", orientation="h",
                  title="各渠道 GMV 贡献", color="conversion_rate",
                  color_continuous_scale="Blues", labels={"gmv": "GMV(元)", "channel": ""})
    fig3.update_layout(height=360)
    st.plotly_chart(fig3, use_container_width=True)

# ---- 渠道效率对比表 ----
st.subheader("渠道效率对比")
ch_table = fdf.groupby("channel").agg(
    UV=("uv", "sum"), 订单数=("orders", "sum"), GMV=("gmv", "sum"), 退款率=("refund_rate", "mean")
).reset_index()
ch_table["转化率"] = (ch_table["订单数"] / ch_table["UV"] * 100).round(2).astype(str) + "%"
ch_table["客单价"] = (ch_table["GMV"] / ch_table["订单数"]).round(1)
ch_table["GMV"] = ch_table["GMV"].round(0)
ch_table["退款率"] = (ch_table["退款率"] * 100).round(2).astype(str) + "%"
ch_table = ch_table.rename(columns={"channel": "渠道"})
st.dataframe(
    ch_table[["渠道", "UV", "订单数", "GMV", "转化率", "客单价", "退款率"]],
    use_container_width=True, hide_index=True
)
