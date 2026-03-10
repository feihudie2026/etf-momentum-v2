import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import json
import time
from collections import defaultdict
from mootdx.quotes import Quotes

# ====================== 配置参数 ======================
# 使用通达信数据源（ETF必须带市场后缀 .SZ 或 .SH）
ASSETS = [
    {"name": "中韩半导体ETF", "etf_code": "513310.SH"},
    {"name": "电网设备ETF",   "etf_code": "159326.SZ"},
    {"name": "有色金属ETF",   "etf_code": "512400.SZ"},
    {"name": "黄金ETF",       "etf_code": "518880.SH"},
    {"name": "油气产业ETF",   "etf_code": "561360.SH"},
    {"name": "沪深300ETF",    "etf_code": "510300.SH"},
    {"name": "创业板50ETF",   "etf_code": "159949.SZ"},
    {"name": "红利低波ETF",   "etf_code": "563690.SH"},
    {"name": "黄金股ETF",     "etf_code": "517520.SH"},
    {"name": "人工智能ETF",   "etf_code": "515980.SH"},
    {"name": "机器人ETF",     "etf_code": "562500.SH"},
    # 可继续添加其他ETF
]

ETF_SAFE = "511880"                # 空仓时持有的货币ETF
MOMENTUM_PERIOD = 20                # 动量周期（日）
BUY_THRESHOLD = 0.08                # 买入阈值
SELL_THRESHOLD = 0.02               # 卖出阈值

ADX_PERIOD = 14
ADX_TREND_THRESHOLD = 25            # 低于此值视为震荡市，强制空仓
MARKET_INDEX = "sz.399006"          # 创业板指，用于计算市场状态（仍用 baostock）

# ====================== 通达信数据获取函数 ======================
def fetch_etf_data_tdx(etf_code, days=600):
    """
    从通达信获取 ETF 净值数据（使用 mootdx）
    etf_code: 如 '513310.SH'（带市场后缀）
    """
    try:
        client = Quotes.factory(market='std', bestip=True)
        # 去掉市场后缀，如 '513310.SH' -> '513310'
        code = etf_code.split('.')[0]
        # 获取日线数据
        df = client.bars(
            symbol=code,
            frequency=9,    # 9 = 日线
            offset=days,
            start=0
        )
        if df is None or df.empty:
            return None
        # 转换列名和格式
        df = df.reset_index().rename(columns={'index': 'date'})
        df['date'] = pd.to_datetime(df['date'])
        # 确保浮点类型
        for col in ['close', 'high', 'low']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df[['date', 'close', 'high', 'low']].dropna()
        return df
    except Exception as e:
        print(f"通达信数据获取失败 {etf_code}: {e}")
        return None

# ====================== 指数数据获取（用于ADX和健康度，仍用baostock）======================
def fetch_index_data_baostock(index_code, days=600):
    """使用 baostock 获取指数日线数据"""
    try:
        lg = bs.login()
        if lg.error_code != '0':
            raise Exception("baostock 登录失败")
        end = datetime.now().strftime('%Y-%m-%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        rs = bs.query_history_k_data_plus(
            index_code,
            "date,close,high,low",
            start_date=start,
            end_date=end,
            frequency="d"
        )
        data = []
        while (rs.error_code == '0') & rs.next():
            data.append(rs.get_row_data())
        bs.logout()
        if not data:
            return None
        df = pd.DataFrame(data, columns=['date','close','high','low'])
        for col in ['close','high','low']:
            df[col] = pd.to_numeric(df[col])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"baostock 获取 {index_code} 失败: {e}")
        return None

# ====================== 计算 ADX ======================
def calc_adx(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    up_move = high - high.shift()
    down_move = low.shift() - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    plus_di = 100 * (pd.Series(plus_dm).rolling(period).mean() / atr)
    minus_di = 100 * (pd.Series(minus_dm).rolling(period).mean() / atr)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.rolling(period).mean()
    return adx

# ====================== 获取市场 ADX ======================
market_df = fetch_index_data_baostock(MARKET_INDEX, days=600)
if market_df is None or len(market_df) < ADX_PERIOD + 50:
    print("无法获取市场指数数据，ADX 过滤将失效")
    market_adx = None
else:
    adx_series = calc_adx(market_df, ADX_PERIOD)
    market_adx = adx_series.iloc[-1]

# ====================== 获取所有资产的最新动量 ======================
asset_momentums = []
latest_date = None

for asset in ASSETS:
    df = fetch_etf_data_tdx(asset["etf_code"], days=600)
    if df is None or len(df) < MOMENTUM_PERIOD + 1:
        print(f"警告：{asset['name']} 数据不足，跳过")
        continue
    # 计算20日和10日涨幅
    df['return_20d'] = df['close'].pct_change(periods=MOMENTUM_PERIOD)
    df['return_10d'] = df['close'].pct_change(periods=10)
    latest = df.iloc[-1]
    momentum = latest['return_20d']
    momentum_10d = latest['return_10d'] if len(df) >= 11 else None
    last_close = latest['close']
    asset_momentums.append({
        "name": asset["name"],
        "etf_code": asset["etf_code"],
        "momentum": momentum,
        "momentum_10d": momentum_10d,
        "close": last_close,
        "date": latest['date'].strftime('%Y-%m-%d')
    })
    if latest_date is None:
        latest_date = latest['date'].strftime('%Y-%m-%d')

# ====================== 读取人工干预事件 ======================
def load_events():
    config_path = 'events_config.json'
    if not os.path.exists(config_path):
        return []
    with open(config_path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return []

events = load_events()
today_str = datetime.now().strftime('%Y-%m-%d')
current_events = [e for e in events if e.get('start_date', '') <= today_str <= e.get('end_date', '')]

event_factors = {}
event_force = {}

for e in current_events:
    for asset_name in e.get('affected_assets', []):
        if 'factor' in e:
            event_factors[asset_name] = event_factors.get(asset_name, 1.0) * e['factor']
        if 'force_ratio' in e:
            event_force[asset_name] = e['force_ratio']

for asset in asset_momentums:
    name = asset['name']
    asset['adjusted_momentum'] = asset['momentum'] * event_factors.get(name, 1.0)

asset_momentums.sort(key=lambda x: x['adjusted_momentum'], reverse=True)

# ====================== 轮动决策 ======================
best = None
forced_asset = None
forced_ratio = 0
for name, ratio in event_force.items():
    if any(a['name'] == name for a in asset_momentums):
        forced_asset = name
        forced_ratio = ratio
        break

if forced_asset:
    best = next(a for a in asset_momentums if a['name'] == forced_asset)
    signal = f"人工干预：配置 {best['name']}"
    position = f"配置 {best['etf_code']} ({best['name']}) {forced_ratio:.0%} 仓位"
    best_etf = best['etf_code']
else:
    if asset_momentums:
        top = asset_momentums[0]
        market_ok = (market_adx is not None and market_adx >= ADX_TREND_THRESHOLD) or (market_adx is None)
        if top['adjusted_momentum'] > BUY_THRESHOLD and market_ok:
            best = top
        elif top['adjusted_momentum'] > SELL_THRESHOLD and market_ok:
            best = top
        else:
            best = None

    if best:
        if best['adjusted_momentum'] > BUY_THRESHOLD:
            signal = f"强烈买入 {best['name']}"
        else:
            signal = f"谨慎持有 {best['name']}"
        position = f"全仓 {best['etf_code']} ({best['name']})"
        best_etf = best['etf_code']
    else:
        reason = []
        if market_adx is not None and market_adx < ADX_TREND_THRESHOLD:
            reason.append("市场震荡")
        if asset_momentums and asset_momentums[0]['momentum'] <= SELL_THRESHOLD:
            reason.append("最强动量过低")
        reason_str = " / ".join(reason) if reason else "无合适标的"
        signal = f"空仓 ({reason_str})"
        position = f"全仓 {ETF_SAFE} (银华日利)"
        best_etf = ETF_SAFE

# ====================== 策略健康度评估 ======================
def calculate_health_score():
    df_market = fetch_index_data_baostock(MARKET_INDEX, days=800)
    if df_market is None or len(df_market) < 200:
        return 50, 0, 0, 0, 0
    df_market['return_20d'] = df_market['close'].pct_change(periods=20)
    df_market['signal'] = (df_market['return_20d'] > 0).astype(int)
    df_market['strategy_return'] = df_market['signal'].shift(1) * df_market['close'].pct_change()
    df_market['nav'] = (1 + df_market['strategy_return']).cumprod()
    df_market['signal_change'] = df_market['signal'] != df_market['signal'].shift(1)
    trades = df_market[df_market['signal_change']].copy()
    trade_returns = []
    for i in range(len(trades)-1):
        start = trades.index[i]
        end = trades.index[i+1]
        ret = (df_market.loc[end, 'close'] / df_market.loc[start, 'close']) - 1
        if trades.iloc[i]['signal'] == 0:
            ret = 0.0
        trade_returns.append(ret)
    recent = trade_returns[-10:] if len(trade_returns) >= 10 else trade_returns
    win_rate = sum(1 for r in recent if r > 0) / len(recent) if recent else 0
    cons_loss = 0
    for r in reversed(trade_returns):
        if r <= 0:
            cons_loss += 1
        else:
            break
    peak = df_market['nav'].expanding().max()
    drawdown = (df_market['nav'] - peak) / peak
    current_drawdown = drawdown.iloc[-1]
    ret_series = df_market['strategy_return'].dropna()
    if len(ret_series) > 0:
        excess_ret = ret_series.mean() * 252 - 0.02
        vol = ret_series.std() * np.sqrt(252)
        sharpe = excess_ret / vol if vol != 0 else 0
    else:
        sharpe = 0

    score = 0
    if win_rate >= 0.4: score += 30
    elif win_rate >= 0.35: score += 20
    elif win_rate >= 0.3: score += 10
    else: score += 0

    if cons_loss <= 2: score += 25
    elif cons_loss <= 4: score += 15
    elif cons_loss <= 5: score += 5
    else: score += 0

    if current_drawdown >= -0.05: score += 25
    elif current_drawdown >= -0.10: score += 15
    elif current_drawdown >= -0.15: score += 5
    else: score += 0

    if sharpe >= 1.0: score += 20
    elif sharpe >= 0.5: score += 10
    elif sharpe >= 0: score += 5
    else: score += 0

    return score, win_rate, cons_loss, current_drawdown, sharpe

health_score, health_win_rate, health_cons_loss, health_drawdown, health_sharpe = calculate_health_score()

if health_score >= 70:
    health_status = "健康"
    health_color = "green"
    health_advice = "策略运行正常，按信号执行。"
elif health_score >= 40:
    health_status = "警惕"
    health_color = "orange"
    health_advice = "近期表现偏弱，密切关注回撤，但暂不停止。"
else:
    health_status = "警告"
    health_color = "red"
    health_advice = "⚠️ 策略可能失效，建议暂停交易，进入观察模式！"

# ====================== 动态仓位建议 =======================
if best and best_etf != ETF_SAFE:
    mom = best['adjusted_momentum']
    if mom > 0.15:
        suggested_position = "80-100%"
    elif mom > 0.08:
        suggested_position = "50-80%"
    elif mom > 0.02:
        suggested_position = "20-50%"
    else:
        suggested_position = "0%"
else:
    suggested_position = "0%"

# ====================== 读取干预建议（模拟版，可保留后续接入真实因子）======================
def load_interventions(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except:
        return []

news = load_interventions('news_interventions.json')
north = load_interventions('north_interventions.json')
flow = load_interventions('flow_interventions.json')
commodity = load_interventions('commodity_interventions.json')
all_suggestions = news + north + flow + commodity

asset_groups = defaultdict(list)
for s in all_suggestions:
    asset = s.get('asset')
    if asset:
        asset_groups[asset].append(s)

def merge_asset_suggestions(suggestions):
    if not suggestions:
        return None
    bull_count = sum(1 for s in suggestions if s.get('direction') == 'bull')
    bear_count = sum(1 for s in suggestions if s.get('direction') == 'bear')
    total_strength = 0
    weighted_factor_sum = 0
    for s in suggestions:
        strength = s.get('strength', 3)
        factor = s.get('factor', 1.0)
        total_strength += strength
        weighted_factor_sum += strength * factor
    avg_strength = total_strength / len(suggestions) if total_strength > 0 else 3
    avg_factor = weighted_factor_sum / total_strength if total_strength > 0 else 1.0
    if bull_count > 0 and bear_count > 0:
        if bull_count > bear_count:
            direction = 'bull'
            bear_strength = sum(s.get('strength',3) for s in suggestions if s.get('direction')=='bear')
            conflict_ratio = bear_strength / total_strength if total_strength>0 else 0
            avg_factor = avg_factor * (1 - conflict_ratio * 0.3)
        elif bear_count > bull_count:
            direction = 'bear'
            bull_strength = sum(s.get('strength',3) for s in suggestions if s.get('direction')=='bull')
            conflict_ratio = bull_strength / total_strength if total_strength>0 else 0
            avg_factor = avg_factor * (1 + conflict_ratio * 0.3)
        else:
            return None
    else:
        direction = 'bull' if bull_count > 0 else 'bear'
    reasons = [s.get('reason', '') for s in suggestions if s.get('reason')]
    reason_combined = "；".join(reasons[:3])
    sources = list(set(s.get('source', '未知') for s in suggestions))
    return {
        'asset': asset,
        'direction': direction,
        'factor': round(avg_factor, 2),
        'strength': round(avg_strength, 1),
        'reason': reason_combined,
        'sources': sources,
        'count': len(suggestions)
    }

merged_list = []
for asset, sugs in asset_groups.items():
    merged = merge_asset_suggestions(sugs)
    if merged:
        merged_list.append(merged)

merged_list.sort(key=lambda x: x['asset'])

intervention_lines = ["【今日干预信息】"]
for m in merged_list:
    direction_cn = "利多" if m['direction'] == 'bull' else "利空"
    sources_cn = "、".join(m['sources'])
    line = f"- {m['asset']}：{direction_cn}，建议因子 {m['factor']}，强度 {m['strength']}（{sources_cn}）"
    intervention_lines.append(line)

if not merged_list:
    intervention_lines.append("无有效干预建议。")

intervention_text = "\n".join(intervention_lines)

# ====================== 生成 HTML 页面 ======================
html_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>多品种动量轮动+健康预警</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(145deg, #f0f2f5 0%, #e6e9f0 100%);
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
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
        h1 {{ font-size: 22px; text-align: center; color: #1e293b; margin: 0 0 10px; }}
        .badge {{
            background: #0f172a; color: white; padding: 6px 14px; border-radius: 40px;
            font-size: 14px; display: inline-block; margin-bottom: 15px;
        }}
        .health-bar {{
            background-color: {health_color};
            color: white; padding: 12px 18px;
            border-radius: 40px; margin-bottom: 20px;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .health-text {{ font-size: 16px; font-weight: 700; }}
        .health-score {{ font-size: 20px; font-weight: 800; }}
        .advice-box {{
            background: #f1f5f9; padding: 12px; border-radius: 24px;
            margin: 15px 0; font-size: 15px; color: #1e293b;
        }}
        .signal {{
            font-size: 40px; font-weight: 800; padding: 20px; border-radius: 48px;
            text-align: center; margin: 15px 0;
        }}
        .strong-buy {{ background: #1e7e34; color: white; box-shadow: 0 8px 0 #0f4d1f; }}
        .buy {{ background: #4caf50; color: white; box-shadow: 0 8px 0 #2e7d32; }}
        .sell {{ background: #f44336; color: white; box-shadow: 0 8px 0 #b71c1c; }}
        .position {{
            background: #f1f5f9; padding: 18px; border-radius: 30px;
            font-size: 18px; font-weight: 500; margin: 20px 0;
            border: 1px solid #cbd5e1; text-align: center;
        }}
        .filter-info {{
            background: #e9eef3; border-radius: 20px; padding: 15px; margin: 15px 0;
        }}
        .filter-item {{
            display: flex; justify-content: space-between; margin: 5px 0;
        }}
        .asset-table {{
            background: #ffffffcc; border-radius: 20px; padding: 15px; margin-top: 20px;
        }}
        table {{ width: 100%; border-collapse: collapse; font-size: 15px; }}
        th, td {{ padding: 10px 5px; text-align: center; border-bottom: 1px solid #cbd5e1; }}
        th {{ font-weight: 600; color: #334155; }}
        .positive {{ color: #166534; font-weight: 600; }}
        .negative {{ color: #991b1b; font-weight: 600; }}
        .selected {{ background-color: #dcfce7; font-weight: 700; }}
        .footer {{ font-size: 14px; color: #64748b; text-align: center; margin-top: 25px; }}
        .event-link {{
            margin-top: 20px;
            text-align: center;
        }}
        .event-link a {{
            background: #0f172a;
            color: white;
            padding: 8px 16px;
            border-radius: 30px;
            text-decoration: none;
            font-size: 14px;
            display: inline-block;
        }}
        .event-link a:hover {{
            background: #1e293b;
        }}
        .intervention-area {{
            margin-top: 20px;
            background: #f0f0f0;
            padding: 15px;
            border-radius: 10px;
        }}
        .intervention-area h4 {{
            margin-top: 0;
            color: #0f172a;
        }}
        .intervention-text {{
            white-space: pre-wrap;
            font-size: 14px;
            background: white;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ccc;
        }}
        .copy-btn {{
            margin-top: 8px;
            padding: 8px 16px;
            background: #0f172a;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }}
    </style>
</head>
<body>
<div class="card">
    <div style="display: flex; justify-content: space-between;">
        <span class="badge">📊 多品种轮动+健康预警</span>
        <span class="badge" style="background:#334155;">更新 {latest_date}</span>
    </div>

    <div class="health-bar">
        <span class="health-text">🧠 策略状态：{health_status}</span>
        <span class="health-score">{health_score} 分</span>
    </div>
    <div class="advice-box">
        {health_advice}<br>
        <span style="font-size:13px; color:#475569;">（基于创业板指数模拟，仅供参考）</span>
    </div>

    <h1>今日信号</h1>
    <div class="signal {signal_class}">{signal}</div>
    <div class="position">⚡ {position}</div>

    <div style="background: #e9eef3; border-radius: 20px; padding: 15px; margin: 15px 0;">
        <div style="font-weight:600; margin-bottom:10px;">💰 建议仓位</div>
        <div style="font-size: 32px; font-weight: 800; text-align: center;">{suggested_position}</div>
    </div>

    <div class="filter-info">
        <div style="font-weight:600; margin-bottom:8px;">🛡️ 过滤条件</div>
        <div class="filter-item">
            <span>市场状态 (ADX)</span>
            <span style="color:{market_adx_color};">{market_adx_display}</span>
        </div>
        <div class="filter-item">
            <span>买入阈值 >{BUY_THRESHOLD:.0%}</span>
            <span style="color:{buy_threshold_color};">{buy_threshold_display}</span>
        </div>
        <div class="filter-item">
            <span>卖出阈值 <{SELL_THRESHOLD:.0%}</span>
            <span style="color:{sell_threshold_color};">{sell_threshold_display}</span>
        </div>
    </div>

    <!-- 当前生效事件展示 -->
    {events_html}

    <div class="asset-table">
        <div style="font-weight:600; margin-bottom:10px;">📋 各品种动量排序（调整后）</div>
        <table>
            <tr><th>品种</th><th>20日涨幅</th><th>10日涨幅</th><th>调整后</th><th>状态</th></tr>
            {table_rows}
        </table>
    </div>

    <!-- 人工干预链接 -->
    <div class="event-link">
        <a href="https://github.com/feihudie2026/etf-momentum-v2/edit/main/events_config.json" target="_blank">
            ✏️ 管理人工干预事件
        </a>
    </div>

    <!-- 今日干预信息 -->
    <div class="intervention-area">
        <h4>💬 今日干预信息（复制后发给我）</h4>
        <div class="intervention-text" id="interventionText">{intervention_text}</div>
        <button class="copy-btn" onclick="copyIntervention()">📋 复制提示词</button>
    </div>

    <div class="footer">
        🤖 每日14:30更新 · 执行时间 14:50<br>
        空仓时持有 {ETF_SAFE} (银华日利)<br>
        健康度指标基于创业板指数模拟，非实盘收益。
    </div>
</div>
<script>
function copyIntervention() {{
    var text = document.getElementById('interventionText').innerText;
    navigator.clipboard.writeText(text).then(function() {{
        alert('提示词已复制，请粘贴到与AI的对话中');
    }});
}}
</script>
</body>
</html>
"""

# 准备模板变量
signal_class = 'strong-buy' if best and best['adjusted_momentum'] > BUY_THRESHOLD else ('buy' if best else 'sell')
market_adx_display = f"{market_adx:.1f} {'✅趋势' if market_adx and market_adx >= ADX_TREND_THRESHOLD else '❌震荡' if market_adx else '未知'}"
market_adx_color = '#166534' if market_adx and market_adx >= ADX_TREND_THRESHOLD else '#991b1b'

buy_threshold_display = f"最强 {asset_momentums[0]['adjusted_momentum']:.1%} {'✅满足' if best and best['adjusted_momentum'] > BUY_THRESHOLD else '❌不满足' if best else '无'}"
buy_threshold_color = '#166534' if best and best['adjusted_momentum'] > BUY_THRESHOLD else '#991b1b'

sell_threshold_display = f"{asset_momentums[0]['adjusted_momentum']:.1%} {'❌空仓' if best is None else '✅持有'}"
sell_threshold_color = '#991b1b' if best is None else '#166534'

if current_events:
    events_list = ''.join([f"<div>• {e['name']}: {e['description']}</div>" for e in current_events])
    events_html = f'<div style="background:#fef9c3; border-radius:20px; padding:15px; margin:15px 0;"><div style="font-weight:600; margin-bottom:8px;">📢 当前生效事件</div>{events_list}</div>'
else:
    events_html = ''

table_rows = ''
for a in asset_momentums:
    selected_class = 'selected' if a == best else ''
    momentum_class = 'positive' if a['momentum'] > 0 else 'negative'
    momentum_10d_class = 'positive' if a.get('momentum_10d') and a['momentum_10d'] > 0 else 'negative' if a.get('momentum_10d') else ''
    selected_mark = '✅ 选中' if a == best else ''
    momentum_10d_str = f"{a['momentum_10d']:.2%}" if a['momentum_10d'] is not None else "N/A"
    table_rows += f'<tr class="{selected_class}"><td>{a["name"]}</td><td class="{momentum_class}">{a["momentum"]:.2%}</td><td class="{momentum_10d_class}">{momentum_10d_str}</td><td>{a["adjusted_momentum"]:.2%}</td><td>{selected_mark}</td></tr>'

html_content = html_template.format(
    health_color=health_color,
    latest_date=latest_date,
    health_status=health_status,
    health_score=health_score,
    health_advice=health_advice,
    signal_class=signal_class,
    signal=signal,
    position=position,
    suggested_position=suggested_position,
    BUY_THRESHOLD=BUY_THRESHOLD,
    SELL_THRESHOLD=SELL_THRESHOLD,
    market_adx_color=market_adx_color,
    market_adx_display=market_adx_display,
    buy_threshold_color=buy_threshold_color,
    buy_threshold_display=buy_threshold_display,
    sell_threshold_color=sell_threshold_color,
    sell_threshold_display=sell_threshold_display,
    events_html=events_html,
    table_rows=table_rows,
    ETF_SAFE=ETF_SAFE,
    intervention_text=intervention_text
)

with open('docs/index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

record = pd.DataFrame([{
    'date': latest_date,
    'selected': best['name'] if best else '空仓',
    'etf': best_etf,
    'market_adx': market_adx,
    'top_momentum': asset_momentums[0]['momentum'] if asset_momentums else 0,
    'health_score': health_score,
    'health_status': health_status
}])
csv_path = 'docs/signals.csv'
if os.path.exists(csv_path):
    old = pd.read_csv(csv_path)
    combined = pd.concat([old, record], ignore_index=True)
else:
    combined = record
combined.to_csv(csv_path, index=False)
