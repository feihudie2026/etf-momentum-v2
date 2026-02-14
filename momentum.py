import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
import sys

# 登录 baostock
lg = bs.login()
if lg.error_code != '0':
    print("登录失败")
    sys.exit(1)

# 获取创业板指（399006）近300天数据
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

# 决策
if latest_return > 0:
    signal = '买入'
    position = '满仓创业板ETF (159915)'
else:
    signal = '卖出/空仓'
    position = '空仓 (持有银华日利 511880)'

# 生成 HTML（方案一：毛玻璃卡片设计）
html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=yes">
    <title>创业板动量信号</title>
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
            font-size: 64px;
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
        <div class="update-badge">📊 实时信号</div>
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
