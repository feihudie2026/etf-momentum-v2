#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF资金流抓取模块（使用 AKShare）
获取 ETF 实时资金流向数据，生成干预建议
输出：flow_interventions.json
"""

import json
import akshare as ak
import pandas as pd
from datetime import datetime

# ====================== 资产映射（ETF代码 → 资产名称）======================
# 根据你的资产池建立映射，务必确保代码正确
ETF_ASSET_MAP = {
    '159915': '创业板',
    '510300': '沪深300',
    '512400': '有色金属',
    '159611': '电力',
    '518880': '黄金',
    '501018': '能源',
    '159995': '半导体',
    # 以下为新增加的ETF映射，请根据你的 ASSETS 列表补充
    '159949': '创业板50',
    '561360': '油气产业',
    '513310': '中韩半导体',
    '515980': '人工智能',
    '562500': '机器人',
    '159326': '电网设备',
    '517520': '黄金股',
    '159883': '医疗器械',
    '563690': '红利低波',
}

# 阈值配置
INFLOW_THRESHOLD = 1.0  # 净流入/出超过1亿元才考虑
CHANGE_THRESHOLD = 3.0  # 涨跌幅小于3%才视为“悄悄建仓/出货”

def fetch_etf_flow():
    """从 AKShare 获取 ETF 实时资金流向数据"""
    try:
        # 获取全市场ETF实时行情，包含资金流数据
        df = ak.fund_etf_spot_em()
        # 只保留我们关注的ETF
        df = df[df['代码'].isin(ETF_ASSET_MAP.keys())].copy()
        if df.empty:
            print("⚠️ 未找到关注的ETF数据")
            return []
        return df
    except Exception as e:
        print(f"❌ AKShare 数据获取失败: {e}")
        return pd.DataFrame()

def generate_interventions(df):
    """根据资金流数据生成干预建议"""
    interventions = []
    for _, row in df.iterrows():
        code = row['代码']
        name = row['名称']
        asset = ETF_ASSET_MAP.get(code)
        if not asset:
            continue

        # 主力净流入（单位：元），转为亿元
        net_inflow = row.get('主力净流入-净额', 0) / 1e8
        change = row.get('涨跌幅', 0)  # 返回的数值如 2.5 表示 2.5%

        # 规则：净流入 > 阈值 且 涨幅不大（主力悄悄建仓）
        if net_inflow > INFLOW_THRESHOLD and abs(change) < CHANGE_THRESHOLD:
            interventions.append({
                'asset': asset,
                'direction': 'bull',
                'strength': 4,
                'factor': 1.2,
                'reason': f"{name} 主力净流入 {net_inflow:.1f} 亿，涨幅 {change:.1f}%，可能主力建仓",
                'source': 'flow'
            })
        # 规则：净流出 > 阈值 且 跌幅不大（主力悄悄出货）
        elif net_inflow < -INFLOW_THRESHOLD and abs(change) < CHANGE_THRESHOLD:
            interventions.append({
                'asset': asset,
                'direction': 'bear',
                'strength': 4,
                'factor': 0.8,
                'reason': f"{name} 主力净流出 {abs(net_inflow):.1f} 亿，涨幅 {change:.1f}%，主力可能出货",
                'source': 'flow'
            })
    return interventions

def main():
    print("="*60)
    print("📊 ETF资金流抓取模块（AKShare）")
    print(f"⏳ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    df = fetch_etf_flow()
    if df.empty:
        print("⚠️ 无数据，退出")
        with open('flow_interventions.json', 'w', encoding='utf-8') as f:
            json.dump([], f)
        return

    print(f"✅ 获取到 {len(df)} 只ETF的数据")
    interventions = generate_interventions(df)

    # 保存到文件
    with open('flow_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)

    print(f"📈 生成 {len(interventions)} 条干预建议")
    print("="*60)

if __name__ == "__main__":
    main()
