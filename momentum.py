# -*- coding: utf-8 -*-
"""
科创50ETF回调监控 (ATR倍数)
数据源: AKShare
输出: docs/index.html
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ====================== 参数配置 ======================
ETF_CODE = "588000"           # 科创50ETF代码
ETF_NAME = "科创50ETF"        # 显示名称
LOOKBACK_HIGH = 60            # 高点观察周期（日）
ATR_PERIOD = 14               # ATR计算周期
OUTPUT_HTML = "docs/index.html"   # 输出网页路径

# ====================== 数据获取 ======================
def fetch_etf_data(etf_code, days=200):
    """从AKShare获取ETF日线数据（前复权）"""
    try:
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        df = ak.fund_etf_hist_em(symbol=etf_code, period="daily",
                                 start_date=start, end_date=end, adjust="qfq")
        if df is None or df.empty:
            raise ValueError("未获取到数据")
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '收盘': 'close',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume'
        })
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values('date', inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df
    except Exception as e:
        print(f"数据获取失败: {e}")
        return None

def calculate_atr(df, period=14):
    """计算ATR"""
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

# ====================== 主程序 ======================
def main():
    print("="*50)
    print("科创50ETF 回调监控 (ATR策略)")
    print("数据源: AKShare")
    print("="*50)
    
    df = fetch_etf_data(ETF_CODE, days=LOOKBACK_HIGH + ATR_PERIOD + 20)
    if df is None or len(df) < LOOKBACK_HIGH + ATR_PERIOD:
        print("数据不足，无法计算")
        return

    # 计算60日最高价（滚动窗口）
    df['high_60d'] = df['close'].rolling(window=LOOKBACK_HIGH).max()
    # 计算ATR
    df['atr'] = calculate_atr(df, ATR_PERIOD)
    
    # 最新数据
    latest = df.iloc[-1]
    current_price = latest['close']
    high_60d = latest['high_60d']
    current_atr = latest['atr']
    drawdown = high_60d - current_price
    atr_drawdown_ratio = drawdown / current_atr if current_atr != 0 else 0

    # 信号判断
    if atr_drawdown_ratio >= 2.0:
        signal_level = "strong_buy"
        signal_text = "超卖，可考虑买入"
        signal_advice = f"从高点回调 {drawdown:.3f} 元，相当于 {atr_drawdown_ratio:.1f} 倍ATR，处于深度超卖区域，可分批建仓。"
    elif atr_drawdown_ratio >= 1.0:
        signal_level = "buy"
        signal_text = "关注回调"
        signal_advice = f"从高点回调 {drawdown:.3f} 元，相当于 {atr_drawdown_ratio:.1f} 倍ATR，接近超卖，可关注止跌信号。"
    else:
        signal_level = "hold"
        signal_text = "正常区间"
        signal_advice = f"回调幅度 {atr_drawdown_ratio:.1f} 倍ATR，未达超卖阈值，建议观望。"

    # 生成HTML网页
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{ETF_NAME} 回调监控</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(145deg, #f0f2f5 0%, #e6e9f0 100%);
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh;
        }}
        .card {{
            background: rgba(255,255,255,0.9);
            backdrop-filter: blur(8px);
            border-radius: 36px;
            padding: 30px 25px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            max-width: 450px;
            width: 100%;
        }}
        h1 {{
            font-size: 24px;
            text-align: center;
            color: #1e293b;
            margin-bottom: 10px;
        }}
        .badge {{
            background: #0f172a;
            color: white;
            padding: 6px 14px;
            border-radius: 40px;
            font-size: 14px;
            display: inline-block;
            margin-bottom: 15px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin: 20px 0;
        }}
        .info-item {{
            background: #ffffffcc;
            border: 1px solid #cbd5e1;
            border-radius: 24px;
            padding: 12px;
            text-align: center;
        }}
        .info-label {{
            font-size: 14px;
            color: #475569;
        }}
        .info-value {{
            font-size: 28px;
            font-weight: 700;
            margin-top: 5px;
            color: #0f172a;
        }}
        .signal {{
            font-size: 48px;
            font-weight: 800;
            padding: 20px;
            border-radius: 48px;
            text-align: center;
            margin: 20px 0;
        }}
        .strong-buy {{
            background: #1e7e34;
            color: white;
            box-shadow: 0 8px 0 #0f4d1f;
        }}
        .buy {{
            background: #4caf50;
            color: white;
            box-shadow: 0 8px 0 #2e7d32;
        }}
        .hold {{
            background: #3b82f6;
            color: white;
            box-shadow: 0 8px 0 #1e40af;
        }}
        .advice {{
            background: #f1f5f9;
            padding: 16px;
            border-radius: 24px;
            margin: 20px 0;
            font-size: 16px;
            color: #1e293b;
            line-height: 1.5;
            border: 1px solid #cbd5e1;
        }}
        .footer {{
            font-size: 14px;
            color: #64748b;
            text-align: center;
            margin-top: 20px;
            border-top: 1px dashed #cbd5e1;
            padding-top: 18px;
        }}
    </style>
</head>
<body>
<div class="card">
    <div style="display: flex; justify-content: space-between;">
        <span class="badge">📊 策略：高点回调 {LOOKBACK_HIGH}日 | ATR {ATR_PERIOD}日</span>
        <span class="badge" style="background:#334155;">更新 {datetime.now().strftime('%Y-%m-%d %H:%M')}</span>
    </div>
    <h1>{ETF_NAME}</h1>

    <div class="info-grid">
        <div class="info-item">
            <div class="info-label">最新价</div>
            <div class="info-value">{current_price:.3f}</div>
        </div>
        <div class="info-item">
            <div class="info-label">{LOOKBACK_HIGH}日最高</div>
            <div class="info-value">{high_60d:.3f}</div>
        </div>
        <div class="info-item">
            <div class="info-label">ATR({ATR_PERIOD})</div>
            <div class="info-value">{current_atr:.3f}</div>
        </div>
        <div class="info-item">
            <div class="info-label">回调 ATR 倍数</div>
            <div class="info-value" style="color: {'#dc2626' if atr_drawdown_ratio >= 1 else '#16a34a'}">{atr_drawdown_ratio:.1f}x</div>
        </div>
    </div>

    <div class="signal {signal_level}">{signal_text}</div>
    <div class="advice">
        📌 {signal_advice}
        <br><br>
        💡 规则：从{LOOKBACK_HIGH}日内最高点回撤 ≥2倍ATR → 超卖买入信号；1~2倍 → 关注；＜1倍 → 正常。
    </div>

    <div class="footer">
        🤖 数据来源：AKShare (东方财富) · 每日收盘后自动更新<br>
        ⚠️ 仅供参考，不构成投资建议
    </div>
</div>
</body>
</html>
"""

    # 写入文件
    import os
    os.makedirs('docs', exist_ok=True)
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # 打印到控制台
    print(f"\n{ETF_NAME} 回调监控报告")
    print(f"当前价格: {current_price:.3f}")
    print(f"{LOOKBACK_HIGH}日最高价: {high_60d:.3f}")
    print(f"ATR({ATR_PERIOD}): {current_atr:.3f}")
    print(f"回调幅度: {drawdown:.3f} 元")
    print(f"回调ATR倍数: {atr_drawdown_ratio:.1f}x")
    print(f"信号: {signal_text}")
    print("="*50)
    print(f"网页已生成: {OUTPUT_HTML}")

if __name__ == "__main__":
    main()
