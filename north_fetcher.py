import requests
import json
from datetime import datetime

def fetch_north_flow():
    """从新浪财经获取北向资金实时数据"""
    url = "https://vip.stock.finance.sina.com.cn/q/view/api/public/getData.php"
    params = {
        "command": "moneyflow_hsgt",
        "page": 1,
        "num": 1
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        # 解析数据（新浪返回结构示例）
        north_data = data.get('result', {}).get('data', [])
        if north_data:
            # 取最新一条
            latest = north_data[0]
            # 北向资金净流入（亿元）
            net_inflow = float(latest.get('net_inflow', 0))
            return {
                'net_inflow': net_inflow,
                'date': latest.get('date', datetime.now().strftime('%Y-%m-%d'))
            }
        return None
    except Exception as e:
        print(f"❌ 北向资金抓取失败: {e}")
        return None

def generate_interventions(flow_data):
    """生成干预建议"""
    if not flow_data:
        return []
    interventions = []
    net = flow_data['net_inflow']
    # 规则：连续3日净流入>50亿（需要历史数据，这里简化，用单日>50亿作为示例）
    # 实际应用中，你可以存储历史数据计算连续，这里先做简单版
    if net > 50:
        interventions.append({
            'asset': '沪深300',
            'direction': 'bull',
            'strength': 4,
            'factor': 1.1,
            'reason': f"北向资金单日净流入{net:.0f}亿，外资积极入场",
            'source': 'north'
        })
    elif net < -50:
        interventions.append({
            'asset': '沪深300',
            'direction': 'bear',
            'strength': 4,
            'factor': 0.9,
            'reason': f"北向资金单日净流出{abs(net):.0f}亿，外资出逃",
            'source': 'north'
        })
    return interventions

if __name__ == "__main__":
    data = fetch_north_flow()
    interventions = generate_interventions(data)
    with open('north_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    print(f"北向资金干预建议已生成，共{len(interventions)}条")
