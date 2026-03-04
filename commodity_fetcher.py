import requests
import json
from bs4 import BeautifulSoup

def fetch_oil_price():
    """从英为财情获取原油价格"""
    url = "https://cn.investing.com/commodities/crude-oil"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # 解析价格（需要根据实际页面调整）
        # 示例：取布伦特原油最近价格
        price_elem = soup.find('span', {'data-test': 'instrument-price-last'})
        if price_elem:
            price = float(price_elem.text.strip())
            # 计算20日新高（需要历史数据，这里简化，用当日涨跌幅代替）
            change_elem = soup.find('span', {'data-test': 'instrument-price-change-percent'})
            change = float(change_elem.text.strip('%')) if change_elem else 0
            return {'price': price, 'change': change}
        return None
    except Exception as e:
        print(f"❌ 原油价格抓取失败: {e}")
        return None

def generate_interventions(price_data):
    if not price_data:
        return []
    interventions = []
    change = price_data.get('change', 0)
    if change > 1:
        interventions.append({
            'asset': '能源',
            'direction': 'bull',
            'strength': 4,
            'factor': 1.2,
            'reason': f"原油价格上涨{change:.1f}%，创近期新高",
            'source': 'commodity'
        })
    elif change < -3:
        interventions.append({
            'asset': '能源',
            'direction': 'bear',
            'strength': 4,
            'factor': 0.8,
            'reason': f"原油价格下跌{abs(change):.1f}%，承压",
            'source': 'commodity'
        })
    return interventions

if __name__ == "__main__":
    data = fetch_oil_price()
    interventions = generate_interventions(data)
    # 如果也要处理铜价，可以类似添加
    with open('commodity_interventions.json', 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)
    print(f"大宗商品干预建议已生成，共{len(interventions)}条")
