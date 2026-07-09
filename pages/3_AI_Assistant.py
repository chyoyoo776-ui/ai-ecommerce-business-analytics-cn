# -*- coding: utf-8 -*-
"""AI 策略助手 — 结构化经营复盘框架 + GMV 增量测算器"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from utils import load_sku_performance, load_brand_campaigns, load_daily_business, fmt_wan, fmt_pct

st.set_page_config(page_title="AI 策略助手", page_icon="🤖", layout="wide")
st.title("🤖 AI 策略助手")
st.caption("基于当前数据自动生成结构化运营建议 · 由 Claude API 驱动")

st.info(
    "本页将经营异常和商品诊断结果转化为结构化运营建议，并通过 GMV uplift 测算评估潜在收益，"
    "同时给出后续追踪指标和 A/B Test 验证方向。**AI 助手采用固定的结构化经营复盘框架，而不是开放式生成泛泛建议。**"
)

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

# ============================================================
# 模块一：一键生成结构化运营建议报告
# ============================================================
st.subheader("📝 一键生成运营建议报告")
st.caption("报告将按照六个板块输出：核心经营问题 → 原因假设 → 优先行动建议 → 预期影响 → 追踪指标 → 验证实验，对应完整的经营复盘闭环。")

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
    window_option = st.selectbox("分析时间窗口", ["最近7天", "最近30天", "最近90天", "全部历史数据"], index=1)

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
你会收到平台的商品运营数据摘要，请基于数据生成一份《结构化经营复盘报告》。

报告必须严格按以下六个板块输出，标题使用二级标题（##），不要增减或调换顺序：

## 1. 核心经营问题 Key Business Issue
用1-2句话概括当前数据中最值得关注的经营问题，必须引用具体数字。

## 2. 原因假设 Root Cause Hypothesis
基于数据推测问题可能的成因（如商品内容、定价、库存、流量质量等），说明依据。

## 3. 优先行动建议 Priority Actions
列出3-5条具体可执行的动作，每条必须引用具体商品名/品牌/数字，并按优先级排序。

## 4. 预期影响 Expected Impact
定性或定量描述如果执行上述动作，预计能带来什么变化（转化率提升、GMV增量等）。

## 5. 追踪指标 Metrics to Track
列出后续应该持续监控的3-5个指标，说明监控周期。

## 6. 建议验证实验 Suggested A/B Test
给出一个具体的A/B测试方案，包含：假设、对照组、实验组、主指标、辅助指标、护栏指标、观察周期。

要求：语言简洁专业，像真实运营周报一样，不要有多余的寒暄；用中文回答，使用 Markdown 格式。
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
                    max_tokens=2200,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": f"请基于以下数据生成结构化经营复盘报告：\n{data_context}"}]
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
else:
    with st.expander("📄 未生成报告？先看一份示例报告结构"):
        st.markdown("""
## 1. 核心经营问题 Key Business Issue
本周期内识别出 18 个高流量低转化 SKU，合计占平台总流量的 27.3%，是当前转化效率的主要拖累来源。

## 2. 原因假设 Root Cause Hypothesis
其中 62% 的问题商品存在"定价偏高"标记，31% 存在详情页图文质量偏弱的问题，推测转化承接不足主要来自价格竞争力和内容质量两方面。

## 3. 优先行动建议 Priority Actions
1. 【安德玛轻量运动背包】流量Top1但转化率仅1.7%，建议优先复核定价并更换主图
2. 【Reebok极简运动裤】退款率高于均值1.3倍，建议排查尺码描述准确性
3. ……

## 4. 预期影响 Expected Impact
若上述TOP5拖累款转化率提升0.5个百分点，预计可带来约¥12万潜在GMV增量（可用下方测算器验证）。

## 5. 追踪指标 Metrics to Track
CTR、CVR、GMV、退款率，建议观察周期7-14天。

## 6. 建议验证实验 Suggested A/B Test
假设：优化商品标题与主图可提升高流量低转化SKU的转化率。对照组维持原内容，实验组使用优化后内容，主指标为CVR，护栏指标为退款率与投诉率，观察周期7-14天。

*（以上为示例结构，实际内容由 AI 基于当前筛选数据生成）*
""")

st.divider()

# ============================================================
# 模块二：GMV 增量测算器
# ============================================================
st.subheader("🧮 拖累款转化率提升 · GMV 增量测算器")
st.markdown("""
本测算用于评估**"高流量低转化 SKU 优化"**可能带来的 GMV 增量。假设通过标题、主图、价格力或库存优化，
将目标 SKU 的转化率提升一定百分点，则可用以下公式估算潜在 GMV 增量：

> **潜在GMV增量 = 流量(UV) × 转化率提升幅度(pct) × 客单价(AOV)**
""")
st.warning("⚠️ 该工具不是预测模型，仅用于帮助业务团队简化评估优化优先级和机会空间。")

# 复用商品诊断页同样的四象限逻辑，锁定"拖累款"清单供测算选用
sku_agg_calc = sku.groupby(["sku_id", "product_name", "brand", "category"]).agg(
    total_uv=("uv", "sum"), total_orders=("orders", "sum"), total_gmv=("gmv", "sum"),
).reset_index()
sku_agg_calc["cr"] = sku_agg_calc["total_orders"] / sku_agg_calc["total_uv"]
uv_med_c, cr_med_c = sku_agg_calc["total_uv"].median(), sku_agg_calc["cr"].median()
drag_calc = sku_agg_calc[(sku_agg_calc["total_uv"] >= uv_med_c) & (sku_agg_calc["cr"] < cr_med_c)].copy()
drag_calc["aov"] = drag_calc["total_gmv"] / drag_calc["total_orders"].replace(0, pd.NA)
drag_calc = drag_calc.dropna(subset=["aov"]).sort_values("total_uv", ascending=False)

calc_mode = st.radio("测算对象", ["单个拖累款 SKU", "全部拖累款汇总"], horizontal=True)

cc1, cc2 = st.columns(2)

if calc_mode == "单个拖累款 SKU":
    with cc1:
        sku_label_map = {f"{row.product_name}（{row.brand}）": row.sku_id for row in drag_calc.itertuples()}
        picked_label = st.selectbox("选择拖累款 SKU", list(sku_label_map.keys()))
        picked = drag_calc[drag_calc["sku_id"] == sku_label_map[picked_label]].iloc[0]
        traffic = st.number_input("流量 UV", value=int(picked["total_uv"]), min_value=0)
        aov_input = st.number_input("客单价 AOV (¥)", value=round(float(picked["aov"]), 1), min_value=0.0)
    with cc2:
        current_cr = st.number_input("当前转化率 (%)", value=round(float(picked["cr"])*100, 2), min_value=0.0, max_value=100.0)
        cr_lift = st.number_input("目标提升幅度 (百分点 pct)", value=0.5, min_value=0.0, max_value=50.0, step=0.1)

    uplift_orders = traffic * (cr_lift / 100)
    uplift_gmv = traffic * (cr_lift / 100) * aov_input

    st.divider()
    r1, r2, r3 = st.columns(3)
    r1.metric("当前转化率", f"{current_cr:.2f}%")
    r2.metric("目标转化率", f"{current_cr + cr_lift:.2f}%", f"+{cr_lift:.1f}pp")
    r3.metric("潜在 GMV 增量", f"¥{uplift_gmv:,.0f}", help="= UV × 转化率提升幅度 × AOV")
    st.info(f"预计新增订单约 **{uplift_orders:.0f}** 单，带来约 **¥{uplift_gmv:,.0f}** 的潜在 GMV 增量。")

else:
    with cc1:
        cr_lift = st.number_input("目标提升幅度 (百分点 pct)", value=0.5, min_value=0.0, max_value=50.0, step=0.1, key="bulk_lift")
        st.caption(f"当前共识别 {len(drag_calc)} 个拖累款 SKU（全平台，全部历史数据）")
    with cc2:
        st.metric("拖累款合计流量 UV", f"{drag_calc['total_uv'].sum():,.0f}")
        st.metric("拖累款平均客单价", f"¥{drag_calc['aov'].mean():,.0f}")

    drag_calc["uplift_gmv"] = drag_calc["total_uv"] * (cr_lift / 100) * drag_calc["aov"]
    total_uplift = drag_calc["uplift_gmv"].sum()

    st.divider()
    st.metric("全部拖累款潜在 GMV 增量总和", f"¥{total_uplift:,.0f}", help="= Σ (每个SKU的 UV × 转化率提升幅度 × AOV)")

    top_uplift = drag_calc.sort_values("uplift_gmv", ascending=False).head(10)
    display_df = top_uplift[["product_name", "brand", "total_uv", "cr", "aov", "uplift_gmv"]].rename(columns={
        "product_name": "商品名", "brand": "品牌", "total_uv": "流量UV",
        "cr": "当前转化率", "aov": "客单价", "uplift_gmv": "预计GMV增量",
    })
    display_df["当前转化率"] = (display_df["当前转化率"] * 100).round(2).astype(str) + "%"
    display_df["预计GMV增量"] = display_df["预计GMV增量"].round(0)
    st.caption("增量贡献 TOP10 拖累款")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

st.divider()

# ============================================================
# 模块三：后续追踪指标 Follow-up Tracking Metrics
# ============================================================
st.subheader("📈 后续追踪指标 Follow-up Tracking Metrics")
st.caption("策略执行之后，用什么指标证明它是否有效？——这是复盘闭环中最容易被忽略的一环。")

tracking_table = pd.DataFrame([
    ["优化拖累款标题/主图", "CTR、CVR、GMV、退款率", "7-14天"],
    ["调整价格/折扣", "CVR、AOV、毛利率、GMV", "7-14天"],
    ["增加潜力款曝光", "UV、CTR、CVR、GMV贡献占比", "7天"],
    ["优化活动资源分配", "活动ROI、GMV、订单量", "整个活动周期"],
    ["AI建议落地情况", "建议采纳率、报告生成耗时、行动完成率", "每周复盘"],
], columns=["策略", "追踪指标", "评估周期"])
st.dataframe(tracking_table, use_container_width=True, hide_index=True)

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
                        system=SYSTEM_PROMPT + "\n\n如果用户是在追问细节，可以直接回答问题，不必输出完整六段式报告格式。",
                        messages=[{"role": "user", "content": f"数据背景：\n{data_context}\n\n问题：{user_q}"}]
                    )
                    st.markdown(message.content[0].text)
                except Exception as e:
                    st.error(f"回答失败: {e}")
