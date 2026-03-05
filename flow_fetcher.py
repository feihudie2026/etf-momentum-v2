#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ETF资金流抓取模块（东方财富 Choice）
获取 ETF 主力资金流向数据，生成干预建议
输出：flow_interventions.json
"""

import requests
import json
import time
from datetime import datetime
import pandas as pd

# ETF代码与资产名称映射（请根据您的 ASSETS 列表补全）
ETF_ASSET_MAP = {
    '159915': '创业板',
    '510300': '沪深300',
    '512400': '有色金属',
    '159611': '电力',
    '518880': '黄金',
    '501018': '能源',
    '159995': '半导体',
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

# 东方财富 Choice 数据接口模板
EM_API_TEMPLATE = "https://emdatah5.eastmoney.com/dc/zjlx/stock?fc=1.{code}&fn=基金"

def fetch_etf_flow(etf_code, retries=2):
    """从东方财富获取单个ETF的资金流向数据"""
    for attempt in range(retries):
        try:
            url = EM_API_TEMPLATE.format(code=etf_code)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://data.eastmoney.com/'
            }
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            # 解析3日/5日/10日主力资金流向 [citation:1]
            if data and 'data' in data:
                # 提取最近的主力资金数据
                flow_data = data['data']
                # 返回净流入（万元），转为亿元
                net_3d = flow_data.get('net3', 0) / 10000  # 3日主力净流入
                net_5d = flow_data.get('net5', 0) / 10000  # 5日主力净流入
                net_10d = flow_data.get('net10', 0) / 10000  # 10日主力净流入
                
                return {
                    'code': etf_code,
                    'net_3d': net_3d,
                    'net_5d': net_5d,
                    'net_10d': net_10d,
                    'latest_net': net_5d  # 默认用5日作为判断基准
                }
        except Exception as e:
            print(f"⚠️ {etf_code} 抓取失败（尝试 {attempt+1}/{retries}）: {e}")
        time.sleep(1)
    return None

def generate_interventions():
    """遍历所有ETF，生成干预建议"""
    interventions = []
    
    for code, asset in ETF_ASSET_MAP.items():
        flow = fetch_etf_flow(code)
        if not flow:
            continue
        
        net = flow['latest_net']  # 单位：亿元
        
        # 规则：净流入 > 1亿 → 利多
        if net > 1:
            interventions.append({
                'asset': asset,
                'direction': 'bull',
                'strength': 3 + min(int(net), 3),  # 净流入越多强度越高
                'factor': 1.1 + min(net * 0.05, 0.2),  # 最多提升到1.3
                'reason': f"ETF {code} 近5日主力净流入 {net:.1f} 亿",
                'source': 'flow'
            })
        # 规则：净流出 > 1亿 → 利空
        elif net < -1:
            interventions.append({
                'asset': asset,
                'direction': 'bear',
                'strength': 3 + min(abs(net), 3),
                'factor': 0.9 - min(abs(net) * 0.05, 0.2),  # 最低降到0.7
                'reason': f"ETF {code} 近5日主力净流出 {abs(net):.1f} 亿",
                'source': 'flow'
            })
    
    return interventions

def main():
    print("="*60)
    print("📊 ETF资金流抓取模块（东方财富 Choice）")
    print(f"⏳ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    interventions = generate_interventions()
    
    with open('flow_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    
    print(f"📈 生成 {len(interventions)} 条干预建议")
    print("="*60)

if __name__ == "__main__":
    main()
