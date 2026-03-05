#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
北向资金抓取模块（AASTOCKS）
获取北向资金历史成交数据，推算净流入趋势
输出：north_interventions.json
"""

import requests
import json
import time
from datetime import datetime, timedelta
import pandas as pd

# AASTOCKS 北向资金历史数据接口
AASTOCKS_URL = "https://data.aastocks.com/datafeed/northbound/GetHistoryData?symbol=ALL"

def fetch_north_flow(retries=3):
    """从 AASTOCKS 获取北向资金历史数据，失败时重试"""
    for attempt in range(retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://www.aastocks.com/'
            }
            resp = requests.get(AASTOCKS_URL, headers=headers, timeout=15)
            data = resp.json()
            
            # 解析数据，获取最近5个交易日
            if data and 'data' in data:
                history = data['data']
                # 计算最近3日平均成交额作为净流入的近似值（实际净流入需要更复杂计算）
                total_volume = 0
                count = 0
                for item in history[:5]:  # 取最近5日
                    volume = item.get('turnover', 0)  # 成交额（亿元）
                    total_volume += volume
                    count += 1
                
                if count > 0:
                    avg_volume = total_volume / count
                    return {'avg_turnover': avg_volume, 'raw_data': history[:3]}
            print(f"⚠️ 北向资金数据格式异常，尝试 {attempt+1}/{retries}")
        except Exception as e:
            print(f"❌ 北向资金抓取失败（尝试 {attempt+1}/{retries}）: {e}")
        time.sleep(2)
    return None

def generate_interventions(flow_data):
    """生成干预建议"""
    if not flow_data:
        return []
    
    avg_volume = flow_data['avg_turnover']
    interventions = []
    
    # 根据成交额判断资金活跃度（阈值需根据历史数据调整）
    if avg_volume > 1200:  # 成交额大于1200亿视为活跃
        interventions.append({
            'asset': '沪深300',
            'direction': 'bull',
            'strength': 4,
            'factor': 1.1,
            'reason': f"北向资金近期活跃，日均成交额 {avg_volume:.0f} 亿",
            'source': 'north'
        })
    elif avg_volume < 800:  # 成交额小于800亿视为低迷
        interventions.append({
            'asset': '沪深300',
            'direction': 'bear',
            'strength': 3,
            'factor': 0.95,
            'reason': f"北向资金成交额下降至 {avg_volume:.0f} 亿，交投清淡",
            'source': 'north'
        })
    return interventions

def main():
    print("="*60)
    print("📊 北向资金抓取模块（AASTOCKS）")
    print(f"⏳ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    data = fetch_north_flow()
    interventions = generate_interventions(data)
    
    with open('north_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    
    print(f"📈 生成 {len(interventions)} 条干预建议")
    print("="*60)

if __name__ == "__main__":
    main()
