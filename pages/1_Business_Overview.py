# -*- coding: utf-8 -*-
"""生意大盘 — 平台经营总览"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import load_daily_business, load_sku_performance, fmt_wan, fmt_pct, pct_delta

st.set_page_config(page_title="生意大盘", page_icon="📊", layout="wide")
st.title("📊 生意大盘")
st.caption("平台核心经营指标监控 · 多渠道流量拆解")

st.info(
    "本页在当前时间/渠道筛选条件下进行经营健康度检查，将 GMV 表现拆解为流量、转化率、订单量和客单价，"
    "并与上一周期对比识别异常波动，最终给出综合诊断结论。"
)

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

with st.expander("📐 指标拆解逻辑"):
    st.markdown("GMV = UV × 转化率 × 客单价(AOV)　——　这是本页所有异常判断的基础分解公式。任意一环出现明显波动，都会向下传导影响GMV。")

st.divider()

# ============================================================
# 经营健康度检查 Business Health Check
# ============================================================
st.subheader("🩺 经营健康度检查")
st.caption("基于当前筛选条件，对 GMV / 流量 / 转化率 / 客单价 / 订单量进行环比波动检查，并识别流量-转化背离和高流量低转化SKU问题。")

alerts = []  # (severity, title, message, next_action)

gmv_chg = pct_delta(total_gmv, prev_gmv)
cr_chg = pct_delta(avg_cr, prev_cr)
aov_chg = pct_delta(avg_aov, prev_aov)
orders_chg = pct_delta(total_orders, prev_orders)
uv_chg = pct_delta(total_uv, prev_uv)

# --- 第一层：KPI 环比波动检查 ---
if gmv_chg is not None and gmv_chg < -0.15:
    alerts.append(("high", f"🔴 GMV 环比下降 {abs(gmv_chg)*100:.1f}%",
                    "GMV 较上一周期明显下降。",
                    "建议进一步检查流量、转化率和客单价三项，定位主要拖累因子。"))
if cr_chg is not None and cr_chg < -0.10:
    alerts.append(("medium", f"🟡 转化率环比下降 {abs(cr_chg)*100:.1f}%",
                    "转化效率下降，可能与商品承接、价格力、库存或流量质量有关。",
                    "建议前往「商品诊断」页排查高流量低转化SKU，检查详情页与价格竞争力。"))
if aov_chg is not None and aov_chg < -0.10:
    alerts.append(("medium", f"🟡 客单价环比下降 {abs(aov_chg)*100:.1f}%",
                    "客单价明显下降，需关注是否折扣力度过大或高客单商品占比降低。",
                    "建议检查近期活动折扣深度，评估是否可优化满减/折扣结构。"))
if orders_chg is not None and orders_chg < -0.15:
    alerts.append(("high", f"🔴 订单量环比下降 {abs(orders_chg)*100:.1f}%",
                    "订单量明显下降，建议检查是否有活动资源减少或流量下滑导致。",
                    "建议核对本周期活动排期是否较上周期减少，评估是否需补充场次资源。"))

# --- 第二层：流量-转化背离检查 ---
traffic_mismatch = False
if uv_chg is not None and uv_chg > 0.20 and (orders_chg is None or orders_chg < 0.05):
    traffic_mismatch = True
    alerts.append(("medium", "🟡 流量-转化背离",
                    f"流量环比增长 {uv_chg*100:.1f}%，但订单量仅增长 {(orders_chg*100 if orders_chg is not None else 0):.1f}%，"
                    "说明新增流量未被有效转化。",
                    "建议检查流量来源质量、商品价格力、页面卖点和库存状态。"))

# --- 第三层：SKU 问题识别（联动商品诊断页）---
sku_all = load_sku_performance()
sku_in_range = sku_all[(sku_all["start_date"] >= start) & (sku_all["start_date"] <= end)]
n_problem_sku = 0
drag_uv_share_range = 0
if len(sku_in_range) > 10:
    s_agg = sku_in_range.groupby("sku_id").agg(uv=("uv", "sum"), orders=("orders", "sum")).reset_index()
    s_agg["cr"] = s_agg["orders"] / s_agg["uv"]
    uv_t = s_agg["uv"].quantile(0.7)
    cr_t = s_agg["cr"].quantile(0.3)
    problem_mask = (s_agg["uv"] >= uv_t) & (s_agg["cr"] <= cr_t)
    n_problem_sku = problem_mask.sum()
    drag_uv_share_range = s_agg.loc[problem_mask, "uv"].sum() / s_agg["uv"].sum() if s_agg["uv"].sum() else 0
    if n_problem_sku > 0:
        alerts.append(("high", f"🔴 发现 {n_problem_sku} 个高流量低转化 SKU",
                        f"这些商品获得了较高曝光（占当前范围总流量 {drag_uv_share_range*100:.1f}%），但转化率低于当前范围均值。",
                        "建议前往「商品诊断」页获取完整清单，优先检查商品标题、主图、价格力和库存状态。"))

# --- 健康度评分 ---
score = 100
for sev, _, _, _ in alerts:
    score -= 20 if sev == "high" else (10 if sev == "medium" else 5)
score = max(score, 0)
score_label = "🟢 健康" if score >= 80 else ("🟡 需要关注" if score >= 50 else "🔴 需要立即处理")

sh1, sh2 = st.columns([1, 3])
with sh1:
    st.metric("经营健康度评分", f"{score} / 100", score_label, delta_color="off")
with sh2:
    if alerts:
        n_high = sum(1 for a in alerts if a[0] == "high")
        n_med = sum(1 for a in alerts if a[0] == "medium")
        st.warning(f"当前筛选范围下发现 {n_high} 个高优先级问题、{n_med} 个中优先级问题，详见下方诊断卡片。")
    else:
        st.success("当前筛选范围下未发现明显异常，各项核心指标表现平稳。")

for sev, title, msg, action in alerts:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(f"📌 现象：{msg}")
        st.caption(f"👉 建议下一步：{action}")

if n_problem_sku > 0:
    st.page_link("pages/2_Product_Diagnosis.py", label="👉 前往「商品诊断」页查看完整拖累款清单")

# ---- 第三层：综合诊断结论（模板化输出）----
st.markdown("#### 🧩 综合诊断结论")
causes = []
actions = set()

if gmv_chg is not None and gmv_chg < -0.05:
    if orders_chg is not None and orders_chg < -0.10:
        causes.append("订单量下降")
        actions.add("活动资源投放节奏与承接页面")
    if cr_chg is not None and cr_chg < -0.08:
        causes.append("商品转化承接不足")
        actions.add("高流量低转化SKU的标题、主图、价格力和库存状态")
    if aov_chg is not None and aov_chg < -0.08:
        causes.append("客单价下降")
        actions.add("折扣力度与商品结构")
    if traffic_mismatch:
        causes.append("新增流量未被有效转化")
        actions.add("流量来源质量与落地页体验")
    if n_problem_sku > 5:
        causes.append(f"存在{n_problem_sku}个高流量低转化SKU拖累")
        actions.add("商品诊断页中的拖累款清单")

    if causes:
        cause_text = "、".join(causes)
        action_text = "、".join(actions)
        st.error(f"**综合判断**：当前 GMV 下滑主要与 **{cause_text}** 有关。建议优先排查 **{action_text}**。")
    else:
        st.warning("**综合判断**：GMV 出现下滑，但各分项指标波动幅度均未超过预警阈值，建议结合具体品牌/渠道进一步下钻排查。")
elif gmv_chg is not None and gmv_chg > 0.05:
    st.success(f"**综合判断**：当前 GMV 较上一周期增长 {gmv_chg*100:.1f}%，核心指标表现健康，建议保持当前活动资源投放节奏。")
else:
    st.info("**综合判断**：当前 GMV 表现基本平稳，环比波动在正常区间内，暂无需要重点处理的经营异常。")

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

with st.expander("📎 渠道指标怎么解读"):
    st.markdown("""
    - **私域社群**渠道转化率通常显著高于大盘均值，说明私域用户信任度和购买意愿更强，
      是加大内容投入与专属优惠券发放的优先渠道。
    - **大促日**（橙色柱）GMV 呈脉冲式增长，但客单价通常略有下降，说明大促期间价格敏感型用户占比提升。
    - 若某渠道流量占比高但转化率明显偏低，需要进一步排查该渠道引流页面与目标用户是否匹配。
    """)
