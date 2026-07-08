# -*- coding: utf-8 -*-
"""AI 策略助手 — 一键生成结构化运营建议报告 + GMV 增量测算器"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import load_sku_performance, load_brand_campaigns, load_daily_business, fmt_wan, fmt_pct, language_toggle, t

st.set_page_config(page_title="AI 策略助手", page_icon="🤖", layout="wide")
lang = language_toggle()
st.title(t("🤖 AI 策略助手", "🤖 AI Strategy Assistant"))
st.caption(t("基于当前数据自动生成结构化运营建议 · 由 Claude API 驱动",
             "Auto-generates structured operational recommendations · Powered by Claude API"))

# 优先从 Streamlit secrets 读取共享 Key（部署到 Streamlit Cloud 时配置），
# 本地完全没有 secrets.toml 文件时，st.secrets 会直接抛异常，所以这里用 try/except 兜底
try:
    shared_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    shared_key = None

if shared_key:
    api_key = shared_key
    st.success(t("✅ 已使用平台内置的演示 Key，可直接生成建议", "✅ Using the built-in demo key — ready to generate"), icon="🔑")
else:
    st.info(t("💡 需要在下方填入你的 Anthropic API Key 才能生成 AI 建议。Key 仅在本次会话中使用，不会被存储。",
              "💡 Enter your Anthropic API Key below to generate AI suggestions. The key is only used for this session and never stored."), icon="🔑")
    api_key = st.text_input(t("Anthropic API Key", "Anthropic API Key"), type="password", placeholder="sk-ant-...")

sku = load_sku_performance()
camp = load_brand_campaigns()
daily = load_daily_business()

# ============================================================
# 模块一：一键生成运营建议报告
# ============================================================
st.subheader(t("📝 一键生成运营建议报告", "📝 One-Click Strategy Report"))

max_date = sku["end_date"].max()
col1, col2, col3 = st.columns(3)
with col1:
    scope_options_zh = ["全平台", "按品牌", "按类目"]
    scope_options_en = ["All Platform", "By Brand", "By Category"]
    scope_idx = st.selectbox(t("品牌/类目范围", "Brand/Category Scope"),
                              range(3), format_func=lambda i: t(scope_options_zh[i], scope_options_en[i]))
    report_scope = scope_options_zh[scope_idx]  # 内部统一用中文键，避免影响数据筛选逻辑
with col2:
    scope_value = None
    if report_scope == "按品牌":
        scope_value = st.selectbox(t("选择品牌", "Select Brand"), sorted(sku["brand"].unique().tolist()))
    elif report_scope == "按类目":
        scope_value = st.selectbox(t("选择类目", "Select Category"), sorted(sku["category"].unique().tolist()))
with col3:
    window_options_zh = ["最近7天", "最近30天", "最近90天", "全部历史数据"]
    window_options_en = ["Last 7 days", "Last 30 days", "Last 90 days", "All history"]
    window_idx = st.selectbox(t("分析时间窗口", "Analysis Window"),
                               range(4), index=1, format_func=lambda i: t(window_options_zh[i], window_options_en[i]))
    window_option = window_options_zh[window_idx]

window_days_map = {"最近7天": 7, "最近30天": 30, "最近90天": 90, "全部历史数据": None}
window_days = window_days_map[window_option]
if window_days is not None:
    window_start = max_date - pd.Timedelta(days=window_days)
    st.caption(t(f"📅 本次分析范围：{window_start.date()} ~ {max_date.date()}（基于数据集最新日期往前推算，共{window_days}天）",
                 f"📅 Analysis range: {window_start.date()} ~ {max_date.date()} (last {window_days} days from the dataset's latest date)"))
else:
    window_start = sku["start_date"].min()
    st.caption(t(f"📅 本次分析范围：{window_start.date()} ~ {max_date.date()}（全部历史数据）",
                 f"📅 Analysis range: {window_start.date()} ~ {max_date.date()} (all historical data)"))

generate_btn = st.button(t("📝 一键生成运营建议报告", "📝 Generate Strategy Report"), type="primary", use_container_width=True)


def build_data_context(scope, value, window_start=None, window_end=None):
    """根据分析范围+时间窗口构建喂给AI的结构化数据摘要"""
    if scope == "按品牌":
        s = sku[sku["brand"] == value]
        c = camp[camp["brand"] == value]
    elif scope == "按类目":
        s = sku[sku["category"] == value]
        c = camp[camp["category"] == value]
    else:
        s = sku
        c = camp

    if window_start is not None:
        s = s[(s["start_date"] >= window_start) & (s["start_date"] <= window_end)]
        c = c[(c["start_date"] >= window_start) & (c["start_date"] <= window_end)]

    if s.empty:
        return None

    agg = s.groupby(["sku_id", "product_name", "brand"]).agg(
        uv=("uv", "sum"), orders=("orders", "sum"), gmv=("gmv", "sum"),
        refund=("refund_rate", "mean"), sell_through=("sell_through_rate", "mean"),
        overpriced=("overpriced_flag", "max"), weak_listing=("weak_listing_flag", "max"),
    ).reset_index()
    agg["cr"] = agg["orders"] / agg["uv"]
    uv_med, cr_med = agg["uv"].median(), agg["cr"].median()

    drag = agg[(agg["uv"] >= uv_med) & (agg["cr"] < cr_med)].sort_values("uv", ascending=False).head(10)
    stars = agg[(agg["uv"] >= uv_med) & (agg["cr"] >= cr_med)].sort_values("gmv", ascending=False).head(5)
    low_sell_through = agg[agg["sell_through"] < agg["sell_through"].quantile(0.2)].sort_values("gmv", ascending=False).head(10)

    recent_campaigns = c.sort_values("start_date", ascending=False).head(8)

    context = f"""
【分析范围】{scope}: {value or '全平台'}
【分析时间窗口】{window_start.date() if window_start is not None else s['start_date'].min().date()} ~ {window_end.date() if window_end is not None else s['start_date'].max().date()}

【整体规模】
- SKU总数: {len(agg)}
- 总GMV: {agg['gmv'].sum():,.0f}元
- 平均转化率: {agg['cr'].mean()*100:.2f}%
- 平均动销率: {agg['sell_through'].mean()*100:.1f}%
- 平均退款率: {agg['refund'].mean()*100:.2f}%

【拖累款TOP10（高流量低转化）】
{drag[['product_name','brand','uv','cr','gmv','overpriced','weak_listing']].to_string(index=False)}

【明星款TOP5（高流量高转化）】
{stars[['product_name','brand','uv','cr','gmv']].to_string(index=False)}

【低动销TOP10（清仓风险库存）】
{low_sell_through[['product_name','brand','sell_through','gmv']].to_string(index=False)}

【近期场次表现】
{recent_campaigns[['brand','campaign_type','gmv','conversion_rate','new_buyer_ratio']].to_string(index=False)}
"""
    return context


SYSTEM_PROMPT_ZH = """你是一名资深的品牌特卖电商平台运营分析师，擅长从数据中提炼可执行的运营策略。
你会收到平台的商品运营数据摘要,请基于数据生成一份结构化的《运营建议报告》,要求:

1. 分为四个板块：🔴需要立即处理、🟡建议关注、🟢资源加注建议、📦库存与清仓建议
2. 每一条建议都要引用具体数据（商品名/品牌/具体数字），不要说空话
3. 每条建议给出明确的操作动作（比如：建议降价X%、建议更换详情页图片、建议加大XX渠道曝光等）
4. 语言简洁专业，像真实运营周报一样，不要有多余的寒暄
5. 用中文回答，使用 Markdown 格式
"""

SYSTEM_PROMPT_EN = """You are a senior operations analyst at a brand flash-sale e-commerce platform, skilled at
turning data into actionable strategy. You will receive a structured data summary of product performance.
Generate a structured "Operations Strategy Report" with these requirements:

1. Organize into four sections: 🔴 Immediate Action Needed, 🟡 Worth Monitoring, 🟢 Resource Reallocation, 📦 Inventory & Clearance
2. Every recommendation must cite specific data (product name/brand/exact numbers) — no vague statements
3. Every recommendation must include a clear action (e.g., "reduce price by X%", "replace product images", "increase exposure on channel X")
4. Keep the tone concise and professional, like a real weekly ops report — no filler greetings
5. Answer in English, using Markdown format
"""

SYSTEM_PROMPT = t(SYSTEM_PROMPT_ZH, SYSTEM_PROMPT_EN)

if generate_btn:
    if not api_key:
        st.error(t("请先填入 Anthropic API Key", "Please enter your Anthropic API Key first"))
    else:
        with st.spinner(t("正在分析数据并生成建议...", "Analyzing data and generating recommendations...")):
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
                data_context = build_data_context(report_scope, scope_value, window_start, max_date)

                if data_context is None:
                    st.warning(t("所选时间窗口内没有数据，请选择更长的时间窗口。", "No data in the selected window — please choose a longer window."))
                    st.stop()

                message = client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=2000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": t(f"请基于以下数据生成运营建议报告：\n{data_context}",
                                                              f"Please generate a strategy report based on this data:\n{data_context}")}]
                )
                report_text = message.content[0].text
                st.session_state["last_report"] = report_text
                st.session_state["last_context"] = data_context
            except Exception as e:
                st.error(t(f"生成失败: {e}", f"Generation failed: {e}"))

if "last_report" in st.session_state:
    st.divider()
    st.markdown(st.session_state["last_report"])
    st.download_button(
        t("下载报告 (Markdown)", "Download Report (Markdown)"),
        st.session_state["last_report"],
        file_name="strategy_report.md", mime="text/markdown"
    )
    with st.expander(t("查看喂给 AI 的原始数据摘要", "View raw data context sent to the AI")):
        st.text(st.session_state["last_context"])

st.divider()

# ============================================================
# 模块二：GMV 增量测算器
# ============================================================
st.subheader(t("🧮 拖累款转化率提升 · GMV 增量测算器", "🧮 GMV Uplift Calculator for Conversion Improvement"))
st.caption(t(
    "测算逻辑：潜在GMV增量 = 流量(UV) × 转化率提升幅度(pct) × 客单价(AOV)。"
    "用于量化「如果把拖累款的转化率问题解决了，能带来多少增量」，是向业务方争取资源投入的量化依据。",
    "Formula: Potential GMV Uplift = Traffic (UV) × Conversion Rate Lift (pct) × AOV. "
    "Used to quantify \"how much GMV upside exists if we fix drag-SKU conversion issues\" — "
    "a data-driven case for requesting resources."
))

# 复用商品诊断页同样的四象限逻辑，锁定"拖累款"清单供测算选用
sku_agg_calc = sku.groupby(["sku_id", "product_name", "brand", "category"]).agg(
    total_uv=("uv", "sum"), total_orders=("orders", "sum"), total_gmv=("gmv", "sum"),
).reset_index()
sku_agg_calc["cr"] = sku_agg_calc["total_orders"] / sku_agg_calc["total_uv"]
uv_med_c, cr_med_c = sku_agg_calc["total_uv"].median(), sku_agg_calc["cr"].median()
drag_calc = sku_agg_calc[(sku_agg_calc["total_uv"] >= uv_med_c) & (sku_agg_calc["cr"] < cr_med_c)].copy()
drag_calc["aov"] = drag_calc["total_gmv"] / drag_calc["total_orders"].replace(0, pd.NA)
drag_calc = drag_calc.dropna(subset=["aov"]).sort_values("total_uv", ascending=False)

calc_mode = st.radio(
    t("测算对象", "Calculation Target"),
    [t("单个拖累款 SKU", "Single drag SKU"), t("全部拖累款汇总", "All drag SKUs combined")],
    horizontal=True
)

cc1, cc2 = st.columns(2)

if calc_mode == t("单个拖累款 SKU", "Single drag SKU"):
    with cc1:
        sku_label_map = {f"{row.product_name}（{row.brand}）": row.sku_id for row in drag_calc.itertuples()}
        picked_label = st.selectbox(t("选择拖累款 SKU", "Select a drag SKU"), list(sku_label_map.keys()))
        picked = drag_calc[drag_calc["sku_id"] == sku_label_map[picked_label]].iloc[0]
        traffic = st.number_input(t("流量 UV", "Traffic (UV)"), value=int(picked["total_uv"]), min_value=0)
        aov_input = st.number_input(t("客单价 AOV (¥)", "AOV (¥)"), value=round(float(picked["aov"]), 1), min_value=0.0)
    with cc2:
        current_cr = st.number_input(t("当前转化率 (%)", "Current CVR (%)"), value=round(float(picked["cr"])*100, 2), min_value=0.0, max_value=100.0)
        cr_lift = st.number_input(t("目标提升幅度 (百分点 pct)", "Target Lift (percentage points)"), value=0.5, min_value=0.0, max_value=50.0, step=0.1)

    uplift_orders = traffic * (cr_lift / 100)
    uplift_gmv = traffic * (cr_lift / 100) * aov_input

    st.divider()
    r1, r2, r3 = st.columns(3)
    r1.metric(t("当前转化率", "Current CVR"), f"{current_cr:.2f}%")
    r2.metric(t("目标转化率", "Target CVR"), f"{current_cr + cr_lift:.2f}%", f"+{cr_lift:.1f}pp")
    r3.metric(t("潜在 GMV 增量", "Potential GMV Uplift"), f"¥{uplift_gmv:,.0f}",
              help=t("= UV × 转化率提升幅度 × AOV", "= UV × Conversion Lift × AOV"))
    st.info(t(f"预计新增订单约 **{uplift_orders:.0f}** 单，带来约 **¥{uplift_gmv:,.0f}** 的潜在 GMV 增量。",
              f"Estimated **{uplift_orders:.0f}** additional orders, generating approximately **¥{uplift_gmv:,.0f}** in potential GMV uplift."))

else:
    with cc1:
        cr_lift = st.number_input(t("目标提升幅度 (百分点 pct)", "Target Lift (percentage points)"), value=0.5, min_value=0.0, max_value=50.0, step=0.1, key="bulk_lift")
        st.caption(t(f"当前共识别 {len(drag_calc)} 个拖累款 SKU（全平台，全部历史数据）", f"{len(drag_calc)} drag SKUs identified (all platform, all history)"))
    with cc2:
        st.metric(t("拖累款合计流量 UV", "Total Drag-SKU Traffic"), f"{drag_calc['total_uv'].sum():,.0f}")
        st.metric(t("拖累款平均客单价", "Average AOV of Drag SKUs"), f"¥{drag_calc['aov'].mean():,.0f}")

    drag_calc["uplift_gmv"] = drag_calc["total_uv"] * (cr_lift / 100) * drag_calc["aov"]
    total_uplift = drag_calc["uplift_gmv"].sum()

    st.divider()
    st.metric(t("全部拖累款潜在 GMV 增量总和", "Total Potential GMV Uplift (all drag SKUs)"), f"¥{total_uplift:,.0f}",
              help=t("= Σ (每个SKU的 UV × 转化率提升幅度 × AOV)", "= Σ (each SKU's UV × Conversion Lift × AOV)"))

    top_uplift = drag_calc.sort_values("uplift_gmv", ascending=False).head(10)
    display_df = top_uplift[["product_name", "brand", "total_uv", "cr", "aov", "uplift_gmv"]].rename(columns={
        "product_name": t("商品名", "Product"), "brand": t("品牌", "Brand"),
        "total_uv": t("流量UV", "Traffic"), "cr": t("当前转化率", "Current CVR"),
        "aov": t("客单价", "AOV"), "uplift_gmv": t("预计GMV增量", "Est. GMV Uplift"),
    })
    display_df[t("当前转化率", "Current CVR")] = (display_df[t("当前转化率", "Current CVR")] * 100).round(2).astype(str) + "%"
    display_df[t("预计GMV增量", "Est. GMV Uplift")] = display_df[t("预计GMV增量", "Est. GMV Uplift")].round(0)
    st.caption(t("增量贡献 TOP10 拖累款", "Top 10 SKUs by potential GMV uplift"))
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()
with st.expander(t("💬 或者：直接问数据问题（自由问答模式）", "💬 Or: Ask a free-form data question")):
    user_q = st.text_input(t("输入你的问题，例如：哪个品牌的拖累款最多？", "Type your question, e.g. Which brand has the most drag SKUs?"))
    ask_btn = st.button(t("提问", "Ask"))
    if ask_btn and user_q:
        if not api_key:
            st.error(t("请先填入 API Key", "Please enter your API Key first"))
        else:
            with st.spinner(t("思考中...", "Thinking...")):
                try:
                    from anthropic import Anthropic
                    client = Anthropic(api_key=api_key)
                    data_context = build_data_context(report_scope, scope_value, window_start, max_date)
                    if data_context is None:
                        st.warning(t("所选时间窗口内没有数据，请选择更长的时间窗口。", "No data in the selected window — please choose a longer window."))
                        st.stop()
                    message = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=800,
                        system=SYSTEM_PROMPT + t("\n\n请直接回答用户问题，不需要输出完整报告格式。",
                                                   "\n\nAnswer the user's question directly, no need for the full report format."),
                        messages=[{"role": "user", "content": t(f"数据背景：\n{data_context}\n\n问题：{user_q}",
                                                                  f"Data context:\n{data_context}\n\nQuestion: {user_q}")}]
                    )
                    st.markdown(message.content[0].text)
                except Exception as e:
                    st.error(t(f"回答失败: {e}", f"Failed to answer: {e}"))

