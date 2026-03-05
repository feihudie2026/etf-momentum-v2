#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 大宗商品模拟版 - 用于系统稳定运行
import json
import random
from datetime import datetime

COMMODITY_MAP = [
    {'name': '原油', 'asset': '能源', 'factor': 1.2},
    {'name': '黄金', 'asset': '黄金', 'factor': 1.15},
    {'name': '铜', 'asset': '有色金属', 'factor': 1.2},
]

def generate_interventions():
    interventions = []
    if random.random() > 0.5:  # 50%概率生成建议
        comm = random.choice(COMMODITY_MAP)
        is_bull = random.choice([True, False])
        change = round(random.uniform(1.5, 4.5), 1)
        direction = 'bull' if is_bull else 'bear'
        factor = comm['factor'] if is_bull else 1 / comm['factor']
        interventions.append({
            'asset': comm['asset'],
            'direction': direction,
            'strength': 3,
            'factor': round(factor, 2),
            'reason': f"模拟数据：{comm['name']}价格{ '上涨' if is_bull else '下跌'} {change}%",
            'source': 'commodity_sim'
        })
    return interventions

def main():
    print("="*60)
    print("📊 大宗商品抓取模块（模拟版 - 用于系统稳定运行）")
    print(f"⏳ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    interventions = generate_interventions()
    with open('commodity_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    print(f"📈 生成 {len(interventions)} 条模拟干预建议")
    print("="*60)

if __name__ == "__main__":
    main()
