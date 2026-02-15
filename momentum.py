import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# ====================== 原有数据获取部分 ======================
lg = bs.login()
if lg.error_code != '0':
    print("登录失败")
    sys.exit(1)

end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=300)).strftime('%Y-%m-%d')
rs = bs.query_history_k_data_plus(
    "sz.399006",
    "date,close",
    start_date=start_date,
    end_date=end_date,
    frequency="d"
)

data_list = []
while (rs.error_code == '0') & rs.next():
    data_list.append(rs.get_row_data())

if not data_list:
    print("未获取到数据")
    sys.exit(1)

df_index = pd.DataFrame(data_list, columns=rs.fields)
df_index['close'] = df_index['close'].astype(float)
df_index['date'] = pd.to_datetime(df_index['date'])
df_index = df_index.sort_values('date')
df_index['return_20d'] = df_index['close'].pct_change(periods=20)

# 最新信号
latest_date = df_index['date'].iloc[-1].strftime('%Y-%m-%d')
latest_return = df_index['return_20d'].iloc[-1]

if latest_return > 0:
    signal = '买入'
    position = '满仓创业板ETF (159915)'
else:
    signal = '卖出/空仓'
    position = '空仓 (持有银华日利 511880)'

# ====================== 新增：计算胜率和连续亏损 ======================
# 生成交易信号序列（1=买入/持有，0=空仓）
df_index['signal'] = (df_index['return_20d'] > 0).astype(int)

# 计算策略每日收益率（第二天开盘执行，所以shift(1)）
df_index['strategy_return'] = df_index['signal'].shift(1) * df_index['close'].pct_change()

# 提取交易记录（信号发生变化的日子）
df_index['signal_change'] = df_index['signal'] != df_index['signal'].shift(1)
trades = df_index[df_index['signal_change']].copy()

# 计算每笔交易的收益率（从信号发生到下一次信号变化的累计收益）
trade_returns = []
for i in range(len(trades) - 1):
    start_date = trades.index[i]
    end_date = trades.index[i + 1]
    ret = (df_index.loc[end_date, 'close'] / df_index.loc[start_date, 'close']) - 1
    # 如果是空仓信号（signal=0），收益应为0（因为持有货币基金）
    if trades.iloc[i]['signal'] == 0:
        ret = 0.0
    trade_returns.append(ret)

# 计算最近10笔交易的胜率
recent_trades = trade_returns[-10:] if len(trade_returns) >= 10 else trade_returns
win_count = sum(1 for r in recent_trades if r > 0)
win_rate = win_count / len(recent_trades) if len(recent_trades) > 0 else 0.0

# 计算当前连续亏损次数
consecutive_losses = 0
for r in reversed(trade_returns):
    if r <= 0:
        consecutive_losses += 1
    else:
        break

# ====================== 生成HTML（方案一 + 监控指标） ======================
html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>创业板动量信号 + 监控</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            text-align: center;
            padding: 20px;
            background: linear-gradient(145deg, #f5f7fa 0%, #e9ecf0 100%);
            min-height: 100vh;
            margin: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 32px;
            padding: 30px 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1), 0 4px 12px rgba(0,0,0,0.05);
            max-width: 400px;
            margin: 0 auto;
            width: 100%;
            border: 1px solid rgba(255,255,255,0.5);
        }}
        h1 {{
            font-size: 22px;
            font-weight: 600;
            color: #1e293b;
            letter-spacing: 0.5px;
            margin-top: 0;
            margin-bottom: 20px;
        }}
        .signal {{
            font-size: 48px;
            font-weight: 800;
            margin: 20px 0 10px;
            padding: 20px;
            border-radius: 48px;
            transition: all 0.2s ease;
        }}
        .buy {{
            background: #dcfce7;
            color: #166534;
            box-shadow: 0 8px 0 #14532d;
        }}
        .sell {{
            background: #fee2e2;
            color: #991b1b;
            box-shadow: 0 8px 0 #7f1d1d;
        }}
        .position {{
            font-size: 18px;
            font-weight: 500;
            color: #334155;
            background: #f1f5f9;
            padding: 16px;
            border-radius: 24px;
            margin: 20px 0;
            border: 1px solid #cbd5e1;
        }}
        .info {{
            font-size: 16px;
            color: #475569;
            margin: 12px 0 8px;
            display: flex;
            justify-content: space-between;
            background: #ffffffcc;
            padding: 12px 16px;
            border-radius: 30px;
            border: 1px solid #d1d9e6;
        }}
        .monitor {{
            margin-top: 25px;
            padding-top: 20px;
            border-top: 2px dashed #94a3b8;
        }}
        .monitor-title {{
            font-size: 16px;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 12px;
            text-align: left;
        }}
        .monitor-item {{
            background: #e2e8f0;
            border-radius: 20px;
            padding: 12px 16px;
            margin: 8px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .monitor-label {{
            font-size: 14px;
            color: #334155;
        }}
        .monitor-value {{
            font-size: 20px;
            font-weight: 700;
        }}
        .good {{
            color: #166534;
        }}
        .warning {{
            color: #b45309;
        }}
        .danger {{
            color: #991b1b;
        }}
        .footer {{
            font-size: 14px;
            color: #64748b;
            margin-top: 25px;
            border-top: 1px dashed #cbd5e1;
            padding-top: 18px;
        }}
        .update-badge {{
            background: #0f172a;
            color: white;
            padding: 6px 14px;
            border-radius: 40px;
            font-size: 14px;
            font-weight: 500;
            display: inline-block;
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="update-badge">📊 实时信号 + 策略监控</div>
        <h1>创业板动量择时</h1>
        <div class="signal {'buy' if signal=='买入' else 'sell'}">{signal}</div>
        <div class="position">⚡ {position}</div>
        <div class="info">
            <span>📅 更新日期</span>
            <span><strong>{latest_date}</strong></span>
        </div>
        <div class="info">
            <span>📈 20日涨跌幅</span>
            <span><strong style="color:{'#16a34a' if latest_return>0 else '#dc2626'};">{latest_return:.2%}</strong></span>
        </div>

        <!-- 新增：策略监控指标 -->
        <div class="monitor">
            <div class="monitor-title">📋 策略健康度监控</div>
            <div class="monitor-item">
                <span class="monitor-label">最近10笔胜率</span>
                <span class="monitor-value {{
                    'good' if win_rate >= 0.5 else 'warning' if win_rate >= 0.4 else 'danger'
                }}">{win_rate:.1%}</span>
            </div>
            <div class="monitor-item">
                <span class="monitor-label">当前连续亏损</span>
                <span class="monitor-value {{
                    'good' if consecutive_losses <= 2 else 'warning' if consecutive_losses <= 4 else 'danger'
                }}">{consecutive_losses} 次</span>
            </div>
            <div style="font-size: 13px; color: #475569; text-align: left; margin-top: 12px; background: #f1f5f9; padding: 10px; border-radius: 16px;">
                💡 胜率低于40%或连续亏损超4次，可能处于震荡市，坚持纪律即可。
            </div>
        </div>

        <div class="footer">
            🤖 自动量化策略 · 每日14:30更新<br>
            ⏰ 交易时间 14:50 执行
        </div>
    </div>
</body>
</html>"""

# 写入文件
with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
