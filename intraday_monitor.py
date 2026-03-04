#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
盘中监控模块（新浪实时行情版）
每天上午11:30运行，检查价格异常波动
输出：intraday_alerts.json
"""

import requests
import json
from datetime import datetime

# 资产与ETF代码映射（与你的资产池一致）
ETF_MAP = {
    '159915': '创业板',
    '510300': '沪深300',
    '512400': '有色金属',
    '159611': '电力',
    '518880': '黄金',
    '501018': '能源',
    '159995': '半导体',
}

def get_realtime_prices(codes):
    """获取多个ETF的实时行情（新浪接口）"""
    # 新浪接口要求前缀：深市 sz，沪市 sh
    code_str = ','.join([('sz' + code if code.startswith('15') or code.startswith('30') else 'sh' + code) for code in codes])
    url = f"https://hq.sinajs.cn/list={code_str}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://finance.sina.com.cn'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        lines = resp.text.strip().split('\n')
        data = {}
        for line in lines:
            if not line.startswith('var'):
                continue
            # 解析 var hq_str_sz159915="...";
            parts = line.split('="')
            if len(parts) < 2:
                continue
            code = parts[0].split('_')[-1]  # 提取代码
            values = parts[1].strip('";').split(',')
            if len(values) < 30:
                continue
            name = values[0]
            try:
                price = float(values[3])   # 当前价
                pre_close = float(values[2])  # 昨收
                change = price - pre_close
                pct = change / pre_close * 100 if pre_close != 0 else 0
            except:
                continue
            data[code] = {
                'name': name,
                'price': price,
                'pct': pct,
                'time': values[30] if len(values) > 30 else ''
            }
        return data
    except Exception as e:
        print(f"❌ 获取实时行情失败: {e}")
        return {}

def main():
    print("="*60)
    print("📈 盘中监控模块（新浪实时行情）")
    print(f"⏳ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    codes = list(ETF_MAP.keys())
    prices = get_realtime_prices(codes)
    
    alerts = []
    for code, info in prices.items():
        pct = info['pct']
        asset = ETF_MAP.get(code, code)
        if abs(pct) > 3:  # 涨跌幅超过3%预警
            alerts.append({
                'type': '价格异动',
                'level': 'medium',
                'msg': f"{info['name']} 上午涨跌幅 {pct:.1f}%，波动较大",
                'asset': asset,
                'direction': 'bull' if pct > 0 else 'bear',
                'factor': 1.1 if pct > 0 else 0.9
            })
    
    # 保存预警到文件
    with open('intraday_alerts.json', 'w', encoding='utf-8') as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)
    
    print(f"📊 共生成 {len(alerts)} 条盘中预警，已保存至 intraday_alerts.json")
    print("="*60)

if __name__ == "__main__":
    main()
