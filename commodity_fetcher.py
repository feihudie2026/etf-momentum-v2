#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大宗商品抓取模块（SunSirs）
获取原油、黄金、铜等商品价格，生成干预建议
输出：commodity_interventions.json
"""

import requests
import json
import time
from datetime import datetime
import pandas as pd

# SunSirs 商品价格数据接口
SUNSIRS_URL = "https://www.sunsirs.com/api/spotprice"

# 商品映射表（SunSirs 商品ID和对应的资产）
COMMODITY_MAP = [
    {'name': 'Crude oil', 'id': 'crude_oil', 'asset': '能源', 'factor': 1.2},
    {'name': 'Gold', 'id': 'gold', 'asset': '黄金', 'factor': 1.15},
    {'name': 'Silver', 'id': 'silver', 'asset': '黄金', 'factor': 1.1},
    {'name': 'Copper', 'id': 'copper', 'asset': '有色金属', 'factor': 1.2},
    {'name': 'Tin ingot', 'id': 'tin', 'asset': '有色金属', 'factor': 1.15},
]

def fetch_commodity_prices(retries=3):
    """从 SunSirs 获取大宗商品价格数据 [citation:6]"""
    for attempt in range(retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.sunsirs.com/'
            }
            params = {
                'lang': 'en',
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            resp = requests.get(SUNSIRS_URL, params=params, headers=headers, timeout=15)
            data = resp.json()
            
            if data and 'commodities' in data:
                return data['commodities']
        except Exception as e:
            print(f"❌ 商品数据抓取失败（尝试 {attempt+1}/{retries}）: {e}")
        time.sleep(2)
    return None

def generate_interventions(commodities):
    """根据商品价格变化生成干预建议"""
    if not commodities:
        return []
    
    interventions = []
    for comm in COMMODITY_MAP:
        # 在返回数据中查找对应商品
        found = next((c for c in commodities if c.get('ename') == comm['name'] or c.get('id') == comm['id']), None)
        if not found:
            continue
        
        change_str = found.get('change', '0%')
        change_val = float(change_str.strip('%'))
        
        # 根据涨跌幅度生成干预
        if change_val > 3:
            interventions.append({
                'asset': comm['asset'],
                'direction': 'bull',
                'strength': 4,
                'factor': comm['factor'],
                'reason': f"{comm['name']} 价格大涨 {change_val:.1f}%",
                'source': 'commodity'
            })
        elif change_val > 1.5:  # 中等涨幅
            interventions.append({
                'asset': comm['asset'],
                'direction': 'bull',
                'strength': 3,
                'factor': comm['factor'] * 0.9,
                'reason': f"{comm['name']} 价格上涨 {change_val:.1f}%",
                'source': 'commodity'
            })
        elif change_val < -3:
            interventions.append({
                'asset': comm['asset'],
                'direction': 'bear',
                'strength': 4,
                'factor': 1 / comm['factor'],  # 反向因子
                'reason': f"{comm['name']} 价格大跌 {abs(change_val):.1f}%",
                'source': 'commodity'
            })
        elif change_val < -1.5:
            interventions.append({
                'asset': comm['asset'],
                'direction': 'bear',
                'strength': 3,
                'factor': 0.9,
                'reason': f"{comm['name']} 价格下跌 {abs(change_val):.1f}%",
                'source': 'commodity'
            })
    
    return interventions

def main():
    print("="*60)
    print("📊 大宗商品抓取模块（SunSirs）")
    print(f"⏳ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    commodities = fetch_commodity_prices()
    interventions = generate_interventions(commodities)
    
    with open('commodity_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    
    print(f"📈 生成 {len(interventions)} 条干预建议")
    print("="*60)

if __name__ == "__main__":
    main()
