# -*- coding: utf-8 -*-
"""
壹品仓 · 商品运营智能驾驶舱 — 合成数据生成器 v2
真实品牌矩阵版本，自底向上生成（SKU → 场次 → 平台每日），保证三张表 GMV 口径完全一致。
"""

import numpy as np
import pandas as pd
from datetime import date, timedelta
import random

random.seed(42)
np.random.seed(42)

START_DATE = date(2024, 7, 1)
END_DATE = date(2025, 6, 30)
ALL_DATES = pd.date_range(START_DATE, END_DATE, freq="D")
N_DAYS = len(ALL_DATES)

CHANNELS = ["线下门店导流", "短信营销", "微信推文", "私域社群", "App自然流量"]
CHANNEL_BASE_SHARE = {
    "线下门店导流": 0.22, "短信营销": 0.13, "微信推文": 0.15,
    "私域社群": 0.18, "App自然流量": 0.32,
}
# 不同渠道的转化率相对系数：私域/短信触达的是已购买过的老客，转化率通常更高；
# App自然流量含大量首次浏览新客，转化率相对较低
CHANNEL_CR_MULTIPLIER = {
    "线下门店导流": 0.95, "短信营销": 1.22, "微信推文": 1.05,
    "私域社群": 1.38, "App自然流量": 0.82,
}

FESTIVALS = {
    "2024-08-08": (1.4, "周年庆预热"), "2024-09-09": (1.3, "金秋焕新节"),
    "2024-10-21": (1.6, "双11预售"), "2024-11-11": (2.8, "双11爆发"),
    "2024-11-12": (1.6, "双11返场"), "2024-12-12": (1.9, "双12大促"),
    "2025-01-20": (1.7, "年货节"), "2025-02-14": (1.3, "情人节"),
    "2025-03-08": (1.5, "38女王节"), "2025-04-15": (1.2, "换季焕新"),
    "2025-05-01": (1.4, "五一大促"), "2025-06-18": (2.4, "618大促"),
}
FESTIVAL_DATES = {pd.Timestamp(k): v for k, v in FESTIVALS.items()}

BRANDS = [
    {"brand": "耐克", "category": "运动户外", "tier": "国际一线", "catalog_size": 90, "price_range": (199, 1299), "traffic_idx": 1.6},
    {"brand": "阿迪达斯", "category": "运动户外", "tier": "国际一线", "catalog_size": 85, "price_range": (189, 1199), "traffic_idx": 1.5},
    {"brand": "安德玛", "category": "运动户外", "tier": "国际一线", "catalog_size": 55, "price_range": (159, 899), "traffic_idx": 1.1},
    {"brand": "Reebok", "category": "运动户外", "tier": "国际一线", "catalog_size": 45, "price_range": (149, 799), "traffic_idx": 0.85},
    {"brand": "Speedo", "category": "运动户外", "tier": "国际专业", "catalog_size": 35, "price_range": (99, 599), "traffic_idx": 0.65},
    {"brand": "李宁", "category": "运动户外", "tier": "国产一线", "catalog_size": 70, "price_range": (129, 799), "traffic_idx": 1.2},
    {"brand": "斯凯奇", "category": "运动户外", "tier": "国际大众", "catalog_size": 60, "price_range": (179, 699), "traffic_idx": 1.0},
    {"brand": "Jeep", "category": "运动户外", "tier": "户外垂类", "catalog_size": 50, "price_range": (159, 899), "traffic_idx": 0.8},
    {"brand": "探拓", "category": "运动户外", "tier": "户外垂类", "catalog_size": 40, "price_range": (99, 599), "traffic_idx": 0.6},
    {"brand": "拓路者", "category": "运动户外", "tier": "户外垂类", "catalog_size": 38, "price_range": (89, 549), "traffic_idx": 0.55},
    {"brand": "TFO", "category": "运动户外", "tier": "户外垂类", "catalog_size": 32, "price_range": (79, 499), "traffic_idx": 0.45},
    {"brand": "Vans", "category": "鞋靴", "tier": "国际潮牌", "catalog_size": 55, "price_range": (219, 699), "traffic_idx": 1.15},
    {"brand": "回力", "category": "鞋靴", "tier": "国民经典", "catalog_size": 45, "price_range": (59, 299), "traffic_idx": 0.95},
    {"brand": "奥康", "category": "鞋靴", "tier": "国产大众", "catalog_size": 60, "price_range": (129, 599), "traffic_idx": 0.9},
    {"brand": "红蜻蜓", "category": "鞋靴", "tier": "国产大众", "catalog_size": 55, "price_range": (119, 549), "traffic_idx": 0.85},
    {"brand": "奥卡索", "category": "鞋靴", "tier": "国产大众", "catalog_size": 42, "price_range": (109, 499), "traffic_idx": 0.6},
    {"brand": "朴西", "category": "鞋靴", "tier": "新锐品牌", "catalog_size": 35, "price_range": (99, 459), "traffic_idx": 0.55},
    {"brand": "西遇", "category": "鞋靴", "tier": "新锐品牌", "catalog_size": 30, "price_range": (89, 399), "traffic_idx": 0.45},
    {"brand": "百田森", "category": "鞋靴", "tier": "新锐品牌", "catalog_size": 28, "price_range": (79, 359), "traffic_idx": 0.4},
    {"brand": "康莉", "category": "鞋靴", "tier": "新锐品牌", "catalog_size": 26, "price_range": (69, 329), "traffic_idx": 0.35},
    {"brand": "ZHR", "category": "鞋靴", "tier": "新锐品牌", "catalog_size": 24, "price_range": (69, 299), "traffic_idx": 0.32},
]

SUBCATS = {
    "运动户外": ["冲锋衣", "速干T恤", "登山鞋", "运动裤", "运动背包", "羽绒服", "训练鞋", "泳装", "瑜伽服", "户外凉鞋"],
    "鞋靴": ["运动休闲鞋", "帆布鞋", "皮鞋", "靴子", "凉鞋", "板鞋", "跑步鞋", "工装鞋"],
}
ADJECTIVES = ["轻氧", "微风", "暖阳", "极简", "云感", "轻量", "经典", "新季", "百搭", "舒适款",
              "都市", "光感", "透气", "防滑", "减震", "户外款", "限定", "复古", "科技感", "耐磨"]


def seasonality_factor(d: pd.Timestamp) -> float:
    days_elapsed = (d - pd.Timestamp(START_DATE)).days
    growth = 1.0 + 0.16 * (days_elapsed / N_DAYS)
    weekday_factor = {0: 0.92, 1: 0.90, 2: 0.93, 3: 0.97, 4: 1.08, 5: 1.22, 6: 1.15}[d.weekday()]
    month_factor = {1: 1.08, 2: 0.88, 3: 1.05, 4: 1.00, 5: 1.02, 6: 1.10,
                    7: 0.95, 8: 1.00, 9: 1.05, 10: 1.08, 11: 1.28, 12: 1.15}[d.month]
    festival_mult = FESTIVAL_DATES[d][0] if d in FESTIVAL_DATES else 1.0
    return growth * weekday_factor * month_factor * festival_mult


def build_catalog(brand_cfg):
    brand, category = brand_cfg["brand"], brand_cfg["category"]
    subcats = SUBCATS[category]
    lo, hi = brand_cfg["price_range"]
    catalog = []
    for i in range(brand_cfg["catalog_size"]):
        subcat = random.choice(subcats)
        name = f"{brand}{random.choice(ADJECTIVES)}{subcat}"
        quality_score = float(np.clip(np.random.beta(5, 3), 0.05, 0.99))
        price_tier = np.random.choice(["低价", "中价", "高价"], p=[0.35, 0.45, 0.20])
        if price_tier == "低价":
            price = np.random.uniform(lo, lo + (hi - lo) * 0.30)
        elif price_tier == "中价":
            price = np.random.uniform(lo + (hi - lo) * 0.30, lo + (hi - lo) * 0.65)
        else:
            price = np.random.uniform(lo + (hi - lo) * 0.65, hi)
        overpriced_flag = np.random.random() < 0.15
        weak_listing_flag = np.random.random() < 0.12
        catalog.append({
            "sku_id": f"{brand}_{i+1:04d}", "product_name": name, "brand": brand,
            "category": category, "sub_category": subcat, "base_price": round(price, 0),
            "quality_score": round(quality_score, 3), "price_tier": price_tier,
            "overpriced_flag": overpriced_flag, "weak_listing_flag": weak_listing_flag,
        })
    return pd.DataFrame(catalog)


catalogs = {b["brand"]: build_catalog(b) for b in BRANDS}

CAMPAIGN_TYPES = ["常规场次", "大促联动", "清仓专场", "新品首发"]
CAMPAIGN_TYPE_WEIGHTS = [0.45, 0.20, 0.15, 0.20]
span_days = (END_DATE - START_DATE).days

campaign_schedule = []
campaign_id_counter = 1
for b in BRANDS:
    brand = b["brand"]
    n_camp = int(np.clip(10 + b["traffic_idx"] * 14 + np.random.normal(0, 2), 6, 30))
    offsets = np.sort(np.random.choice(range(3, span_days - 7), size=n_camp, replace=False))
    for off in offsets:
        start_d = START_DATE + timedelta(days=int(off))
        duration = random.choice([3, 4, 4, 5, 5, 6, 7])
        end_d = min(start_d + timedelta(days=duration), END_DATE)
        campaign_type = np.random.choice(CAMPAIGN_TYPES, p=CAMPAIGN_TYPE_WEIGHTS)
        festival_tag = ""
        matched_festival_date = None
        for f_date, (gf, fname) in FESTIVAL_DATES.items():
            if start_d <= f_date.date() <= end_d:
                festival_tag = fname
                campaign_type = "大促联动"
                matched_festival_date = f_date
                break
        campaign_schedule.append({
            "campaign_id": f"CAMP{campaign_id_counter:05d}", "brand": brand, "category": b["category"],
            "tier": b["tier"], "traffic_idx": b["traffic_idx"], "start_date": start_d, "end_date": end_d,
            "duration_days": duration, "campaign_type": campaign_type, "festival_tag": festival_tag,
            "festival_date": matched_festival_date,
        })
        campaign_id_counter += 1

campaign_schedule = pd.DataFrame(campaign_schedule)
print(f"共排期 {len(campaign_schedule)} 场活动，覆盖 {len(BRANDS)} 个品牌")

BASE_CR = 0.038
sku_perf_rows = []

for _, camp in campaign_schedule.iterrows():
    brand = camp["brand"]
    catalog = catalogs[brand]
    duration = camp["duration_days"]
    traffic_idx = camp["traffic_idx"]

    sku_lo = max(int(len(catalog) * 0.35), 8)
    sku_hi = max(int(len(catalog) * 0.75), sku_lo + 5)
    n_sku = min(random.randint(sku_lo, sku_hi), len(catalog))
    sampled = catalog.sample(n=n_sku, replace=False)

    base_uv_per_brand = 3200 * traffic_idx
    festival_boost = FESTIVAL_DATES[camp["festival_date"]][0] if camp["festival_tag"] else 1.0
    camp_total_uv = max(int(base_uv_per_brand * duration * festival_boost * np.random.normal(1, 0.12)), 300)

    alpha = np.random.uniform(0.3, 0.6, size=len(sampled))
    weights = np.random.dirichlet(alpha)

    for (_, sku), w in zip(sampled.iterrows(), weights):
        sku_uv = max(int(camp_total_uv * w), 10)
        base_ctr = 0.18 + 0.22 * sku["quality_score"]
        if sku["weak_listing_flag"]:
            base_ctr *= 0.55
        ctr = float(np.clip(base_ctr * np.random.normal(1, 0.10), 0.04, 0.55))

        base_cr = 0.022 + 0.055 * sku["quality_score"]
        if sku["overpriced_flag"]:
            base_cr *= 0.42
        if sku["weak_listing_flag"]:
            base_cr *= 0.70
        type_cr_mult = {"常规场次": 1.0, "大促联动": 1.30, "清仓专场": 1.45, "新品首发": 0.65}[camp["campaign_type"]]
        conversion_rate = float(np.clip(base_cr * type_cr_mult * np.random.normal(1, 0.12), 0.002, 0.32))

        discount_rate = {
            "常规场次": np.random.uniform(0.10, 0.30), "大促联动": np.random.uniform(0.20, 0.45),
            "清仓专场": np.random.uniform(0.40, 0.65), "新品首发": np.random.uniform(0.00, 0.15),
        }[camp["campaign_type"]]
        final_price = sku["base_price"] * (1 - discount_rate)
        if sku["overpriced_flag"]:
            final_price *= 1.12

        orders = int(sku_uv * conversion_rate)
        gmv = orders * final_price
        stock_qty = int(np.random.uniform(40, 600) * (1.3 if sku["price_tier"] == "低价" else 0.85))
        sell_through_rate = float(np.clip(orders / max(stock_qty, 1), 0.0, 1.0))

        base_refund = 0.075
        if sku["overpriced_flag"]:
            base_refund += 0.035
        if sku["weak_listing_flag"]:
            base_refund += 0.025
        refund_rate = float(np.clip(np.random.normal(base_refund, 0.018), 0.01, 0.30))

        sku_perf_rows.append({
            "campaign_id": camp["campaign_id"], "brand": brand, "category": sku["category"],
            "sub_category": sku["sub_category"], "sku_id": sku["sku_id"], "product_name": sku["product_name"],
            "campaign_type": camp["campaign_type"], "start_date": camp["start_date"].strftime("%Y-%m-%d"),
            "end_date": camp["end_date"].strftime("%Y-%m-%d"), "duration_days": duration,
            "base_price": sku["base_price"], "final_price": round(final_price, 1),
            "discount_rate": round(discount_rate, 3), "stock_qty": stock_qty, "uv": sku_uv,
            "ctr": round(ctr, 4), "conversion_rate": round(conversion_rate, 4), "orders": orders,
            "gmv": round(gmv, 2), "sell_through_rate": round(sell_through_rate, 4),
            "refund_rate": round(refund_rate, 4), "overpriced_flag": sku["overpriced_flag"],
            "weak_listing_flag": sku["weak_listing_flag"],
        })

sku_performance = pd.DataFrame(sku_perf_rows)
print(f"sku_performance: {len(sku_performance)} 行")

agg = sku_performance.groupby("campaign_id").agg(
    uv=("uv", "sum"), orders=("orders", "sum"), gmv=("gmv", "sum"),
    refund_rate=("refund_rate", "mean"), sku_count=("sku_id", "count"),
).reset_index()
agg["conversion_rate"] = (agg["orders"] / agg["uv"]).round(4)
agg["aov"] = (agg["gmv"] / agg["orders"].replace(0, np.nan)).round(2)
agg["new_buyer_ratio"] = np.random.uniform(0.15, 0.45, size=len(agg)).round(4)

brand_campaigns = campaign_schedule.merge(agg, on="campaign_id", how="left")
brand_campaigns["start_date"] = pd.to_datetime(brand_campaigns["start_date"]).dt.strftime("%Y-%m-%d")
brand_campaigns["end_date"] = pd.to_datetime(brand_campaigns["end_date"]).dt.strftime("%Y-%m-%d")
brand_campaigns = brand_campaigns.drop(columns=["traffic_idx", "festival_date"])
brand_campaigns.to_csv("data/brand_campaigns.csv", index=False, encoding="utf-8-sig")
print(f"brand_campaigns: {len(brand_campaigns)} 行 | 总GMV(万) = {brand_campaigns['gmv'].sum()/10000:.1f}")

sku_performance.to_csv("data/sku_performance.csv", index=False, encoding="utf-8-sig")

all_catalog = pd.concat(catalogs.values(), ignore_index=True)
all_catalog.to_csv("data/product_catalog.csv", index=False, encoding="utf-8-sig")

daily_campaign_gmv = {}
daily_campaign_uv = {}
for _, camp in brand_campaigns.iterrows():
    d0 = pd.Timestamp(camp["start_date"])
    d1 = pd.Timestamp(camp["end_date"])
    days = pd.date_range(d0, d1, freq="D")
    n = len(days)
    if n == 0 or pd.isna(camp["gmv"]):
        continue
    weights = np.array([1.0] + [1.15] * max(n - 2, 0) + ([0.9] if n > 1 else []))[:n]
    weights = weights / weights.sum()
    for day, w in zip(days, weights):
        daily_campaign_gmv[day] = daily_campaign_gmv.get(day, 0) + camp["gmv"] * w
        daily_campaign_uv[day] = daily_campaign_uv.get(day, 0) + camp["uv"] * w

rows = []
BASELINE_UV = 9000
BASELINE_CR = 0.018
BASELINE_AOV = 175

for d in ALL_DATES:
    sf = seasonality_factor(d)
    camp_gmv = daily_campaign_gmv.get(d, 0.0)
    camp_uv = daily_campaign_uv.get(d, 0.0)

    baseline_uv = max(int(BASELINE_UV * sf * np.random.normal(1, 0.06)), 500)
    baseline_orders = int(baseline_uv * BASELINE_CR * np.random.normal(1, 0.08))
    baseline_gmv = baseline_orders * BASELINE_AOV * np.random.normal(1, 0.05)

    day_total_uv = camp_uv + baseline_uv
    day_total_gmv = camp_gmv + max(baseline_gmv, 0)
    est_aov = 170 if camp_gmv == 0 else (camp_gmv / max(daily_campaign_uv.get(d, 1) * 0.05, 1))
    day_total_orders = max(int(day_total_gmv / max(est_aov, 60)), baseline_orders)

    is_festival = d in FESTIVAL_DATES
    festival_name = FESTIVAL_DATES[d][1] if is_festival else ""

    # 先确定各渠道 UV（按流量份额）
    ch_uv_map = {}
    for ch in CHANNELS:
        ch_share = CHANNEL_BASE_SHARE[ch] * np.random.normal(1, 0.08)
        ch_uv_map[ch] = max(int(day_total_uv * ch_share), 30)

    # 再按"UV × 渠道转化系数"分配当日总订单量，保证不同渠道转化率有真实差异
    raw_weights = {ch: ch_uv_map[ch] * CHANNEL_CR_MULTIPLIER[ch] * np.random.normal(1, 0.06) for ch in CHANNELS}
    weight_sum = sum(raw_weights.values())

    for ch in CHANNELS:
        ch_uv = ch_uv_map[ch]
        order_share = raw_weights[ch] / weight_sum if weight_sum > 0 else 1 / len(CHANNELS)
        ch_orders = max(int(day_total_orders * order_share), 1)
        ch_cr = float(np.clip(ch_orders / max(ch_uv, 1), 0.005, 0.30))
        ch_aov = (day_total_gmv / max(day_total_orders, 1)) * np.random.normal(1, 0.06)
        ch_gmv = ch_orders * ch_aov
        refund_rate = float(np.clip(np.random.normal(0.082, 0.014), 0.02, 0.20))

        rows.append({
            "date": d.strftime("%Y-%m-%d"), "channel": ch, "is_festival": is_festival,
            "festival_name": festival_name, "uv": ch_uv, "orders": ch_orders,
            "gmv": round(max(ch_gmv, 0), 2), "conversion_rate": round(ch_cr, 4),
            "aov": round(ch_aov, 2), "refund_rate": round(refund_rate, 4),
        })

daily_business = pd.DataFrame(rows)
daily_business.to_csv("data/daily_business.csv", index=False, encoding="utf-8-sig")

tmp = daily_business.copy()
tmp["month"] = pd.to_datetime(tmp["date"]).dt.to_period("M")
print("\n月度GMV(万元):")
print((tmp.groupby("month")["gmv"].sum() / 10000).round(1))
print(f"\n平台总GMV(万元): {daily_business['gmv'].sum()/10000:.1f}")
print(f"品牌场次总GMV(万元): {brand_campaigns['gmv'].sum()/10000:.1f}  <- 应显著小于平台总GMV(因为还有非活动自然浏览部分)")
print("\n✅ 数据生成完成，SKU/场次口径已通过groupby保证一致")
