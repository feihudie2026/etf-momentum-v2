
---

## 📄 二、完整 `momentum.py` 代码（添加了评分映射函数）

请在您的仓库中，用以下代码**完全替换**原有的 `momentum.py` 文件。它包含了您之前的所有功能（多资产轮动、ADX、健康度、事件干预、动态仓位、管理链接），并新增了 **`score_to_params` 评分映射函数**，供您参考或未来扩展。

```python
import baostock as bs
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os
import json

# 尝试导入 akshare（用于黄金）
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告：akshare 未安装，黄金等依赖 akshare 的品种将无法获取数据")

# ====================== 配置参数 ======================
ASSETS = [
    {"name": "创业板",   "index_code": "sz.399006", "etf_code": "159915", "use_akshare": False},
    {"name": "沪深300", "index_code": "sh.000300", "etf_code": "510300", "use_akshare": False},
    {"name": "有色金属", "index_code": "sz.399807", "etf_code": "512400", "use_akshare": False},
    {"name": "电力",     "index_code": "sh.000966", "etf_code": "159611", "use_akshare": False},
    {"name": "黄金",     "index_code": None,        "etf_code": "518880", "use_akshare": True},
]
ETF_SAFE = "511880"                # 空仓时持有的货币ETF
MOMENTUM_PERIOD = 20                # 动量周期（日）
BUY_THRESHOLD = 0.08                # 买入阈值
SELL_THRESHOLD = 0.02               # 卖出阈值

ADX_PERIOD = 14
ADX_TREND_THRESHOLD = 25            # 低于此值视为震荡市，强制空仓
MARKET_INDEX = "sz.399006"          # 创业板指，用于计算市场状态

# ====================== 新增：事件评分映射函数（短期优化）======================
def score_to_params(score):
    """
    根据事件评分（1-5分）返回建议的干预参数范围
    用于帮助您将评分转化为具体的 factor 或 force_ratio
    """
    if score >= 4.5:
        return {
            "factor_range": (1.5, 2.0),
            "force_range": (0.2, 0.3),
            "desc": "极强"
        }
    elif score >= 3.5:
        return {
            "factor_range": (1.2, 1.5),
            "force_range": (0.1, 0.2),
            "desc": "强"
        }
    elif score >= 2.5:
        return {
            "factor_range": (1.1, 1.2),
            "force_range": (0.05, 0.1),
            "desc": "中等"
        }
    else:
        return {
            "factor_range": (1.0, 1.05),
            "force_range": (0.0, 0.05),
            "desc": "弱"
        }

# ====================== 数据获取函数 ======================
def fetch_index_data_baostock(index_code, days=600):
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

def fetch_etf_data_akshare(etf_code, days=600):
    if not AKSHARE_AVAILABLE:
        return None
    try:
        end = datetime.now().strftime('%Y%m%d')
        start = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
        df = ak.fund_etf_hist_em(symbol=etf_code, period="daily", start_date=start, end_date=end, adjust="qfq")
        df = df[['日期','收盘']].rename(columns={'日期':'date','收盘':'close'})
        df['date'] = pd.to_datetime(df['date'])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = df['close']
        df['low'] = df['close']
        df = df.sort_values('date').reset_index(drop=True)
        return df
    except Exception as e:
        print(f"akshare 获取 {etf_code} 失败: {e}")
        return None

def get_asset_data(asset):
    if asset["use_akshare"]:
        return fetch_etf_data_akshare(asset["etf_code"])
    else:
        return fetch_index_data_baostock(asset["index_code"])

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
    df = get_asset_data(asset)
    if df is None or len(df) < MOMENTUM_PERIOD + 1:
        print(f"警告：{asset['name']} 数据不足，跳过")
        continue
    df['return'] = df['close'].pct_change(periods=MOMENTUM_PERIOD)
    latest = df.iloc[-1]
    momentum = latest['return']
    last_close = latest['close']
    asset_momentums.append({
        "name": asset["name"],
        "etf_code": asset["etf_code"],
        "momentum": momentum,
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

# 构建事件影响字典
event_factors = {}   # 资产 -> 动量乘数
event_force = {}     # 资产 -> 强制仓位比例

for e in current_events:
    for asset_name in e.get('affected_assets', []):
        if 'factor' in e:
            event_factors[asset_name] = event_factors.get(asset_name, 1.0) * e['factor']
        if 'force_ratio' in e:
            event_force[asset_name] = e['force_ratio']

# ====================== 应用事件调整 ======================
for asset in asset_momentums:
    name = asset['name']
    asset['adjusted_momentum'] = asset['momentum'] * event_factors.get(name, 1.0)

# 按调整后动量排序
asset_momentums.sort(key=lambda x: x['adjusted_momentum'], reverse=True)

# ====================== 轮动决策（含ADX过滤）======================
best = None
# 强制配置优先
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
    # 正常轮动
    if asset_momentums:
        top = asset_momentums[0]
        market_ok = (market_adx is not None and market_adx >= ADX_TREND_THRESHOLD) or (market_adx is None)
        if top['adjusted_momentum'] > BUY_THRESHOLD and market_ok:
            best = top
        elif top['adjusted_momentum'] > SELL_THRESHOLD and market_ok:
            best = top   # 谨慎持有
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
  
