#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ETF资金流模拟版 - 用于系统稳定运行
import json
import random
from datetime import datetime

# 从您的资产池里随机选几个来生成建议
ASSET_POOL = ['有色金属', '电网设备', '半导体', '人工智能']

def generate_interventions():
    interventions = []
    if random.random() > 0.4:  # 60%概率生成建议
        asset = random.choice(ASSET_POOL)
        is_bull = random.choice([True, False])
        net_flow = round(random.uniform(0.5, 2.0), 1)
        factor = 1.1 if is_bull else 0.9
        direction = 'bull' if is_bull else 'bear'
        interventions.append({
            'asset': asset,
            'direction': direction,
            'strength': 3,
            'factor': factor,
            'reason': f"模拟数据：{asset}板块资金{ '净流入' if is_bull else '净流出'} {net_flow}亿",
            'source': 'flow_sim'
        })
    return interventions

def main():
    print("="*60)
    print("📊 ETF资金流抓取模块（模拟版 - 用于系统稳定运行）")
    print(f"⏳ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    interventions = generate_interventions()
    with open('flow_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    print(f"📈 生成 {len(interventions)} 条模拟干预建议")
    print("="*60)

if __name__ == "__main__":
    main()
