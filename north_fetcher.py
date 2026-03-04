import requests
import json
from bs4 import BeautifulSoup

def fetch_north_flow():
    """从东方财富网获取北向资金数据"""
    url = "https://data.eastmoney.com/hsgt/index.html"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 解析当日净流入（需要根据实际页面结构调整选择器）
        # 这里用简化方法：找到包含“当日资金流向”的表格
        flow_elem = soup.find('span', {'id': 'txt_zjl'})
        if flow_elem:
            net_inflow = float(flow_elem.text.strip().replace(',', ''))
            return {'net_inflow': net_inflow}
        return None
    except Exception as e:
        print(f"❌ 北向资金抓取失败: {e}")
        return None

def generate_interventions(flow_data):
    if not flow_data:
        return []
    net = flow_data['net_inflow']
    if net > 50:
        return [{
            'asset': '沪深300',
            'direction': 'bull',
            'strength': 4,
            'factor': 1.1,
            'reason': f"北向资金净流入{net:.0f}亿",
            'source': 'north'
        }]
    elif net < -50:
        return [{
            'asset': '沪深300',
            'direction': 'bear',
            'strength': 4,
            'factor': 0.9,
            'reason': f"北向资金净流出{abs(net):.0f}亿",
            'source': 'north'
        }]
    return []

if __name__ == "__main__":
    data = fetch_north_flow()
    interventions = generate_interventions(data)
    with open('north_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    print(f"北向资金干预建议已生成，共{len(interventions)}条")
