#!/usr/bin/env python3
"""GitHub Actions 用构建脚本 - 更新 index.html（不包含 git 操作）"""
import json, os, re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NEWS_FILE = os.path.join(BASE_DIR, 'latest_news.json')
INDEX_FILE = os.path.join(BASE_DIR, 'index.html')

def extract_js_array(html, name):
    m = re.search(name + r':\s*\[(.*?)\]\s*,\s*\n', html, re.DOTALL)
    return m.group(1) if m else ''

def parse_articles(js):
    articles = []
    for m in re.finditer(r'\{topic:"(.*?)",summary:"(.*?)",source:"(.*?)",date:"(.*?)",url:"(.*?)"\}', js):
        articles.append({'topic':m.group(1),'summary':m.group(2),'source':m.group(3),'date':m.group(4),'url':m.group(5)})
    return articles

def articles_to_js(articles, indent=4):
    lines = []
    for a in articles:
        t = a['topic'].replace('"','\\"').replace("'","\\'")
        s = a['summary'].replace('"','\\"').replace("'","\\'")
        prefix = ' '*indent
        lines.append(f'{prefix}{{topic:"{t}",summary:"{s}",source:"{a["source"]}",date:"{a["date"]}",url:"{a.get("url","")}"}}')
    return '[\n' + ',\n'.join(lines) + '\n  ]'

MAJOR_KW = ['行动方案','规划','政策','国家能源局','发改','十五五','投产','交付','命名','突破','首创','首票','首家','里程碑','创新高','创历史','正式','出台','发布','LNG船','接收站','页岩气','煤层气','管网','管道','保供','增储','招标','碳中和','碳达峰','国际','全球','进口','出口','格局']

def is_major(a):
    t = a.get('title','') + a.get('topic','')
    for p in [r'关于.{2,8}市.{2,8}的通知',r'关于.{2,8}县',r'关于.{2,8}区',r'销售价格',r'阶梯气价',r'统计数据表',r'非居民用天然气销售价格']:
        if re.search(p, t): return False
    return any(kw in t for kw in MAJOR_KW)

def main():
    print(f"🔧 GH Actions Build: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    if not os.path.exists(NEWS_FILE):
        print("❌ latest_news.json 不存在，跳过")
        return
    
    with open(NEWS_FILE) as f:
        news = json.load(f)
    with open(INDEX_FILE) as f:
        html = f.read()
    
    today = datetime.now().strftime('%Y-%m-%d')
    html = re.sub(r'数据更新：\d{4}-\d{2}-\d{2}.*?<br>', f'数据更新：{today}<br>', html)
    
    hot_js = extract_js_array(html, 'hotArticles')
    hist_js = extract_js_array(html, 'historyArticles')
    cur_hot = parse_articles(hot_js)
    cur_hist = parse_articles(hist_js) if hist_js else []
    
    new_major = []
    for a in news.get('articles', []):
        if is_major(a):
            title = a.get('title','')[:50]
            if not any(title[:20] in h.get('topic','') for h in cur_hot):
                new_major.append({'topic':title,'summary':f"来自{a['source']}",'source':a['source'],'date':today,'url':a.get('url','')})
    
    merged = new_major + cur_hot
    seen = set()
    unique = []
    for a in merged:
        k = a['topic'][:30]
        if k and k not in seen:
            seen.add(k); unique.append(a)
    
    new_hot = unique[:12]
    displaced = unique[12:]
    new_hist = (displaced + cur_hist)[:30]
    
    print(f"  热点: {len(new_hot)} | 历史: {len(new_hist)} | 新增: {len(new_major)} | 归档: {len(displaced)}")
    
    html = re.sub(r'hotArticles:\s*\[.*?\],\s*\n', 'hotArticles:\n  ' + articles_to_js(new_hot) + ',\n', html, flags=re.DOTALL)
    if new_hist:
        html = re.sub(r'historyArticles:\s*\[.*?\],?\s*\n', 'historyArticles:\n  ' + articles_to_js(new_hist) + ',\n', html, flags=re.DOTALL)
    
    with open(INDEX_FILE, 'w') as f:
        f.write(html)
    print("✅ index.html 已更新")

if __name__ == '__main__':
    main()
