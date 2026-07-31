#!/usr/bin/env python3
"""
能源天然气知识库 - 自动爬虫
每小时抓取各平台最新资讯，更新 data.json
"""
import subprocess, re, json, os
from datetime import datetime

BASE_DIR = '/home/sherry/energy-gas-kb'
OUTPUT_FILE = os.path.join(BASE_DIR, 'latest_news.json')

def fetch_gas_inen():
    """爬取国际燃气网最新文章"""
    articles = []
    try:
        r = subprocess.run([
            'curl', '-s', '--max-time', '20', '-L',
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'https://gas.in-en.com/'
        ], capture_output=True, text=True, timeout=25)
        
        html = r.stdout
        # 匹配文章链接和标题
        links = re.findall(
            r'href="(https?://gas\.in-en\.com/html/gas-\d+\.shtml)"[^>]*>([^<]+)</a>',
            html
        )
        
        seen = set()
        for url, title in links:
            title = title.strip()
            if title and title not in seen and len(title) > 10:
                seen.add(title)
                articles.append({
                    'title': title,
                    'url': url,
                    'source': '国际燃气网',
                    'platform_url': 'https://gas.in-en.com/'
                })
        
        print(f"  [国际燃气网] 抓取 {len(articles)} 篇文章")
    except Exception as e:
        print(f"  [国际燃气网] 抓取失败: {e}")
    
    return articles

def fetch_nea():
    """爬取国家能源局最新政策动态"""
    articles = []
    try:
        r = subprocess.run([
            'curl', '-s', '--max-time', '20', '-L',
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'https://www.nea.gov.cn/'
        ], capture_output=True, text=True, timeout=25)
        
        html = r.stdout
        # 匹配政策文件标题和链接
        links = re.findall(
            r'<a[^>]*href="([^"]+\.htm[^"]*)"[^>]*title="([^"]+)"[^>]*>',
            html
        )
        if not links:
            # 备用匹配
            links = re.findall(
                r'href="(/[^"]+\.htm[^"]*)"[^>]*>([^<]{10,})</a>',
                html
            )
        
        seen = set()
        for url, title in links[:15]:
            title = re.sub(r'<[^>]+>', '', title).strip()
            if title and title not in seen and len(title) > 8:
                seen.add(title)
                if not url.startswith('http'):
                    url = 'https://www.nea.gov.cn' + url
                articles.append({
                    'title': title,
                    'url': url,
                    'source': '国家能源局',
                    'platform_url': 'https://www.nea.gov.cn/'
                })
        
        print(f"  [国家能源局] 抓取 {len(articles)} 篇文章")
    except Exception as e:
        print(f"  [国家能源局] 抓取失败: {e}")
    
    return articles

def main():
    print(f"\n{'='*50}")
    print(f"🕐 爬虫启动: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*50)
    
    all_articles = []
    
    # 爬取各平台
    all_articles.extend(fetch_gas_inen())
    all_articles.extend(fetch_nea())
    
    # 按标题去重
    seen_titles = set()
    unique_articles = []
    for a in all_articles:
        t = a['title'][:40]
        if t not in seen_titles:
            seen_titles.add(t)
            unique_articles.append(a)
    
    # 保存结果
    output = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_articles': len(unique_articles),
        'articles': unique_articles[:30]  # 最多保留30条
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f'\n✅ 共抓取 {len(unique_articles)} 篇最新文章')
    print(f'📁 已保存到 {OUTPUT_FILE}')
    
    # 打印前5条
    print('\n📰 最新文章预览:')
    for a in unique_articles[:5]:
        print(f"  [{a['source']}] {a['title'][:60]}...")
        print(f"    {a['url']}")
    
    return output

if __name__ == '__main__':
    main()
