import requests
import json
from bs4 import BeautifulSoup

def fetch_etf_flow():
    """从东方财富网获取 ETF 资金流数据"""
    url = "https://data.eastmoney.com/etf/trade.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 解析表格，这里需要根据实际页面结构调整选择器
        # 简单起见，我们模拟几条数据（实际应用中需要解析）
        # 建议用 pandas 读取东方财富的数据表，但需要调试
        # 这里提供一个示例数据，实际使用时你需要根据真实页面解析
        mock_data = [
            {'code': '562800', 'name': '稀有金属ETF', 'net_inflow': 3.67, 'change': 4.68, 'asset': '有色金属'},
            {'code': '516150', 'name': '稀土ETF', 'net_inflow': 2.79, 'change': 4.11, 'asset': '有色金属'},
            {'code': '159915', 'name': '创业板ETF', 'net_inflow': 1.23, 'change': 0.56, 'asset': '创业板'},
        ]
        return mock_data
    except Exception as e:
        print(f"❌ ETF资金流抓取失败: {e}")
        return []

def generate_interventions(flow_list):
    interventions = []
    for item in flow_list:
        asset = item.get('asset')
        inflow = item.get('net_inflow', 0)
        change = item.get('change', 0)
        if inflow > 1 and abs(change) < 3:
            interventions.append({
                'asset': asset,
                'direction': 'bull',
                'strength': 3,
                'factor': 1.2,
                'reason': f"{item['name']}净流入{inflow}亿，涨幅{change}%，可能主力建仓",
                'source': 'flow'
            })
        elif inflow < -1 and abs(change) < 3:
            interventions.append({
                'asset': asset,
                'direction': 'bear',
                'strength': 3,
                'factor': 0.8,
                'reason': f"{item['name']}净流出{abs(inflow)}亿，涨幅{change}%，主力可能出货",
                'source': 'flow'
            })
    return interventions

if __name__ == "__main__":
    data = fetch_etf_flow()
    interventions = generate_interventions(data)
    with open('flow_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    print(f"ETF资金流干预建议已生成，共{len(interventions)}条")
