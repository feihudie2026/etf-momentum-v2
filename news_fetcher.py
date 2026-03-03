#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新闻抓取模块 - 使用 Apify 的 Google News Scraper
输出：news_interventions.json（格式与资金流、北向等一致）
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import hashlib
from collections import defaultdict
from apify_client import ApifyClient

# ====================== 配置 ======================
# 资产池（与你的系统一致）
ASSETS = ['创业板', '沪深300', '有色金属', '电力', '黄金', '能源', '半导体']

# 资产与关键词映射（用于新闻分类）
ASSET_KEYWORDS = {
    '创业板': ['创业板', '科技股', '成长股', '新兴产业', 'TMT', '互联网+'],
    '沪深300': ['沪深300', '蓝筹股', '权重股', '大盘', 'A股', '股指'],
    '有色金属': ['有色金属', '铜', '铝', '锌', '铅', '镍', '锡', '稀土', '小金属', '矿产'],
    '电力': ['电力', '电网', '发电', '火电', '水电', '风电', '光伏', '新能源发电', '储能'],
    '黄金': ['黄金', '金价', '贵金属', '白银', '铂金'],
    '能源': ['能源', '原油', '石油', '天然气', '煤炭', '燃油', '汽油', '柴油', 'OPEC'],
    '半导体': ['半导体', '芯片', '集成电路', '晶圆', '封测', '光刻', 'AI芯片', '存储芯片']
}

# 宏观关键词（用于未匹配到具体资产时归入沪深300）
MACRO_KEYWORDS = [
    '美联储', '加息', '降息', '利率', 'CPI', '通胀', 'PPI', 'GDP',
    '货币政策', '财政政策', '逆回购', 'MLF', 'LPR', '准备金率',
    '中美', '贸易战', '关税', '制裁', '地缘', '冲突', '战争'
]

# 情感词库（简单版）
POSITIVE_WORDS = ['上涨', '大涨', '飙升', '利好', '提振', '回升', '反弹', '增长', '加速', '突破',
                  '支持', '鼓励', '补贴', '减税', '降息', '宽松', '放水', '刺激']
NEGATIVE_WORDS = ['下跌', '大跌', '暴跌', '利空', '打压', '下挫', '回落', '放缓', '减速', '跌破',
                  '制裁', '关税', '加息', '收紧', '缩表', '危机', '风险', '警告']

# Apify 配置
APIFY_TOKEN = os.environ.get('APIFY_TOKEN')
if not APIFY_TOKEN:
    raise ValueError("❌ 环境变量 APIFY_TOKEN 未设置！请在 GitHub Secrets 中添加。")

# 初始化 Apify 客户端
client = ApifyClient(APIFY_TOKEN)

# 输出文件
OUTPUT_FILE = 'news_interventions.json'
HISTORY_FILE = 'news_history.csv'  # 用于去重

# ====================== 工具函数 ======================
def calculate_hash(text):
    """计算文本哈希用于去重"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def load_history(days=3):
    """加载最近 days 天的历史新闻哈希"""
    if not os.path.exists(HISTORY_FILE):
        return set()
    try:
        df = pd.read_csv(HISTORY_FILE)
        cutoff = datetime.now() - timedelta(days=days)
        df['date'] = pd.to_datetime(df['date'])
        df = df[df['date'] > cutoff]
        return set(df['hash'].tolist())
    except Exception as e:
        print(f"⚠️ 加载历史记录失败: {e}")
        return set()

def save_history(news_items):
    """保存新闻哈希到历史文件"""
    if not news_items:
        return
    df = pd.DataFrame([{
        'date': datetime.now().strftime('%Y-%m-%d'),
        'hash': item['hash'],
        'title': item['title'][:50]
    } for item in news_items])
    if os.path.exists(HISTORY_FILE):
        old_df = pd.read_csv(HISTORY_FILE)
        df = pd.concat([old_df, df], ignore_index=True)
    df.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')

# ====================== 新闻分类 ======================
def classify_news(title, content):
    """分析单条新闻，返回 (asset, direction, strength, factor, reason) 或 None"""
    text = (title + ' ' + content).lower()
    matched_assets = []

    # 1. 匹配具体资产
    for asset, keywords in ASSET_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                matched_assets.append(asset)
                break

    # 2. 若无具体资产，尝试宏观关键词
    if not matched_assets:
        for kw in MACRO_KEYWORDS:
            if kw in text:
                matched_assets.append('沪深300')
                break

    if not matched_assets:
        return None  # 无关新闻

    # 3. 情感分析（简单词频）
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)

    if pos > neg:
        direction = 'bull'
        strength = min(5, 3 + (pos - neg))
        factor = round(1.0 + (strength - 3) * 0.1, 2)
    elif neg > pos:
        direction = 'bear'
        strength = min(5, 3 + (neg - pos))
        factor = round(1.0 - (strength - 3) * 0.1, 2)
    else:
        direction = 'neutral'
        strength = 3
        factor = 1.0

    # 取第一个匹配的资产（简化，后续可优化为多资产）
    asset = matched_assets[0]
    reason = title[:30] + '...' if len(title) > 30 else title

    return {
        'asset': asset,
        'direction': direction,
        'strength': strength,
        'factor': factor,
        'reason': reason
    }

# ====================== 从 Apify 抓取新闻 ======================
def fetch_from_apify(keyword, max_items=10):
    """使用 Apify Google News Scraper 抓取单个关键词的新闻"""
    print(f"🔍 正在抓取关键词: {keyword}")
    run_input = {
        "searchQuery": keyword,
        "maxItems": max_items,
        "locale": "zh-cn",
        "outputFormat": "json",
    }
    try:
        # 调用 Actor（这里使用广泛使用的 google-news-scraper，你也可以选择其他）
        run = client.actor("powerai/google-news-search-scraper").call(run_input=run_input)
        # 获取结果数据集
        items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        print(f"   ✅ 获取 {len(items)} 条")
        return items
    except Exception as e:
        print(f"   ❌ 抓取失败: {e}")
        return []

# ====================== 主流程 ======================
def main():
    print("="*60)
    print("📰 新闻抓取模块启动 (Apify)")
    print(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 1. 构建要搜索的关键词列表（资产名 + 宏观词）
    search_keywords = list(ASSET_KEYWORDS.keys()) + MACRO_KEYWORDS
    # 为避免 API 调用过多，先取前5个（可根据需要调整）
    # 这里为了覆盖全，循环所有关键词（Apify 免费额度足够，每个关键词调用一次）
    all_raw_news = []
    history_hashes = load_history()

    for kw in search_keywords:
        items = fetch_from_apify(kw, max_items=5)  # 每个关键词5条
        for item in items:
            title = item.get('headline', '')
            content = item.get('description', '')
            if not title:
                continue
            # 去重
            h = calculate_hash(title + content)
            if h in history_hashes:
                continue
            # 分类
            classification = classify_news(title, content)
            if classification:
                news_record = {
                    'title': title,
                    'content': content,
                    'source': item.get('publisherName', ''),
                    'url': item.get('articleUrl', ''),
                    'published': item.get('publishedAt', ''),
                    'hash': h,
                    **classification
                }
                all_raw_news.append(news_record)
                history_hashes.add(h)
                print(f"  ✅ 归类: {classification['asset']} {classification['direction']} factor={classification['factor']}")

    print(f"\n📊 共获取 {len(all_raw_news)} 条有效新闻")

    # 2. 保存原始新闻到历史
    save_history(all_raw_news)

    # 3. 按资产合并，生成干预建议
    by_asset = defaultdict(list)
    for n in all_raw_news:
        by_asset[n['asset']].append(n)

    interventions = []
    for asset, items in by_asset.items():
        # 计算平均强度和因子
        avg_strength = sum(i['strength'] for i in items) / len(items)
        # 方向投票
        bulls = sum(1 for i in items if i['direction'] == 'bull')
        bears = sum(1 for i in items if i['direction'] == 'bear')
        if bulls > bears:
            direction = 'bull'
            avg_factor = sum(i['factor'] for i in items if i['direction'] == 'bull') / bulls
        elif bears > bulls:
            direction = 'bear'
            avg_factor = sum(i['factor'] for i in items if i['direction'] == 'bear') / bears
        else:
            # 中性或持平，跳过
            continue

        # 合并理由（取前三条标题）
        reasons = [i['reason'] for i in items[:3]]
        reason_summary = f"综合{len(items)}条新闻: " + "；".join(reasons)

        interventions.append({
            'asset': asset,
            'direction': direction,
            'strength': round(avg_strength, 1),
            'factor': round(avg_factor, 2),
            'reason': reason_summary,
            'source': 'news',
            'news_count': len(items)
        })

    # 4. 保存干预建议
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(interventions, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 已生成 {len(interventions)} 条干预建议，保存至 {OUTPUT_FILE}")
    print("="*60)

if __name__ == "__main__":
    main()
