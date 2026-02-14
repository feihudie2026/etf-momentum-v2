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

# 生成 HTML
html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>创业板动量择时信号</title>
    <style>
        body {{ font-family: Arial; text-align: center; padding: 50px; }}
        .signal {{ font-size: 48px; margin: 30px; }}
        .buy {{ color: green; }}
        .sell {{ color: red; }}
        .info {{ font-size: 18px; color: #555; }}
    </style>
</head>
<body>
    <h1>创业板动量择时信号</h1>
    <div class="info">更新日期：{latest_date} 14:30</div>
    <div class="info">20日涨跌幅：{latest_return:.2%}</div>
    <div class="signal {'buy' if signal=='买入' else 'sell'}">{signal}</div>
    <div class="info">{position}</div>
    <hr>
    <div>数据来源：baostock</div>
</body>
</html>"""

# 写入文件
with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
