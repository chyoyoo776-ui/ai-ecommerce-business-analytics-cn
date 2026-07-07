# -*- coding: utf-8 -*-
"""AI 策略助手 — 一键生成结构化运营建议报告"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import load_sku_performance, load_brand_campaigns, load_daily_business, fmt_wan, fmt_pct

st.set_page_config(page_title="AI 策略助手", page_icon="🤖", layout="wide")
st.title("🤖 AI 策略助手")
st.caption("基于当前数据自动生成结构化运营建议 · 由 Claude API 驱动")

# 优先从 Streamlit secrets 读取共享 Key（部署到 Streamlit Cloud 时配置），
# 本地完全没有 secrets.toml 文件时，st.secrets 会直接抛异常，所以这里用 try/except 兜底
try:
    shared_key = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    shared_key = None

if shared_key:
    api_key = shared_key
    st.success("✅ 已使用平台内置的演示 Key，可直接生成建议", icon="🔑")
else:
    st.info("💡 需要在下方填入你的 Anthropic API Key 才能生成 AI 建议。Key 仅在本次会话中使用，不会被存储。", icon="🔑")
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")

sku = load_sku_performance()
camp = load_brand_campaigns()
daily = load_daily_business()

# ---- 选择分析范围 ----
max_date = sku["end_date"].max()
col1, col2, col3 = st.columns(3)
with col1:
    report_scope = st.selectbox("品牌/类目范围", ["全平台", "按品牌", "按类目"])
with col2:
    scope_value = None
    if report_scope == "按品牌":
        scope_value = st.selectbox("选择品牌", sorted(sku["brand"].unique().tolist()))
    elif report_scope == "按类目":
        scope_value = st.selectbox("选择类目", sorted(sku["category"].unique().tolist()))
with col3:
    window_option = st.selectbox(
        "分析时间窗口", ["最近7天", "最近30天", "最近90天", "全部历史数据"], index=1
    )

window_days_map = {"最近7天": 7, "最近30天": 30, "最近90天": 90, "全部历史数据": None}
window_days = window_days_map[window_option]
if window_days is not None:
    window_start = max_date - pd.Timedelta(days=window_days)
    st.caption(f"📅 本次分析范围：{window_start.date()} ~ {max_date.date()}（基于数据集最新日期往前推算，共{window_days}天）")
else:
    window_start = sku["start_date"].min()
    st.caption(f"📅 本次分析范围：{window_start.date()} ~ {max_date.date()}（全部历史数据）")

generate_btn = st.button("📝 一键生成运营建议报告", type="primary", use_container_width=True)


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

    # SKU 四象限统计
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


SYSTEM_PROMPT = """你是一名资深的品牌特卖电商平台运营分析师，擅长从数据中提炼可执行的运营策略。
你会收到平台的商品运营数据摘要,请基于数据生成一份结构化的《运营建议报告》,要求:

1. 分为四个板块：🔴需要立即处理、🟡建议关注、🟢资源加注建议、📦库存与清仓建议
2. 每一条建议都要引用具体数据（商品名/品牌/具体数字），不要说空话
3. 每条建议给出明确的操作动作（比如：建议降价X%、建议更换详情页图片、建议加大XX渠道曝光等）
4. 语言简洁专业，像真实运营周报一样，不要有多余的寒暄
5. 用中文回答，使用 Markdown 格式
"""

if generate_btn:
    if not api_key:
        st.error("请先填入 Anthropic API Key")
    else:
        with st.spinner("正在分析数据并生成建议..."):
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)
                data_context = build_data_context(report_scope, scope_value, window_start, max_date)

                if data_context is None:
                    st.warning("所选时间窗口内没有数据，请选择更长的时间窗口。")
                    st.stop()

                message = client.messages.create(
                    model="claude-sonnet-4-5",
                    max_tokens=2000,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": f"请基于以下数据生成运营建议报告：\n{data_context}"}]
                )
                report_text = message.content[0].text
                st.session_state["last_report"] = report_text
                st.session_state["last_context"] = data_context
            except Exception as e:
                st.error(f"生成失败: {e}")

if "last_report" in st.session_state:
    st.divider()
    st.markdown(st.session_state["last_report"])
    st.download_button(
        "下载报告 (Markdown)",
        st.session_state["last_report"],
        file_name="运营建议报告.md", mime="text/markdown"
    )
    with st.expander("查看喂给 AI 的原始数据摘要"):
        st.text(st.session_state["last_context"])

st.divider()
with st.expander("💬 或者：直接问数据问题（自由问答模式）"):
    user_q = st.text_input("输入你的问题，例如：哪个品牌的拖累款最多？")
    ask_btn = st.button("提问")
    if ask_btn and user_q:
        if not api_key:
            st.error("请先填入 API Key")
        else:
            with st.spinner("思考中..."):
                try:
                    from anthropic import Anthropic
                    client = Anthropic(api_key=api_key)
                    data_context = build_data_context(report_scope, scope_value, window_start, max_date)
                    if data_context is None:
                        st.warning("所选时间窗口内没有数据，请选择更长的时间窗口。")
                        st.stop()
                    message = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=800,
                        system=SYSTEM_PROMPT + "\n\n请直接回答用户问题，不需要输出完整报告格式。",
                        messages=[{"role": "user", "content": f"数据背景：\n{data_context}\n\n问题：{user_q}"}]
                    )
                    st.markdown(message.content[0].text)
                except Exception as e:
                    st.error(f"回答失败: {e}")

