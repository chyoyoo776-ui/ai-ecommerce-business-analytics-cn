# -*- coding: utf-8 -*-
"""数据加载与通用工具函数"""

import pandas as pd
import streamlit as st
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


@st.cache_data
def load_daily_business():
    df = pd.read_csv(DATA_DIR / "daily_business.csv", parse_dates=["date"])
    return df


@st.cache_data
def load_brand_campaigns():
    df = pd.read_csv(DATA_DIR / "brand_campaigns.csv", parse_dates=["start_date", "end_date"])
    return df


@st.cache_data
def load_sku_performance():
    df = pd.read_csv(DATA_DIR / "sku_performance.csv", parse_dates=["start_date", "end_date"])
    return df


@st.cache_data
def load_product_catalog():
    df = pd.read_csv(DATA_DIR / "product_catalog.csv")
    return df


def fmt_wan(x):
    """格式化为'万元'"""
    return f"{x/10000:,.1f}万"


def fmt_pct(x):
    return f"{x*100:.2f}%"


def pct_delta(current, previous):
    if previous == 0 or pd.isna(previous):
        return None
    return (current - previous) / previous

