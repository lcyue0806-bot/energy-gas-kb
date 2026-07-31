#!/usr/bin/env python3
"""
能源天然气知识库 - 自动构建脚本
读取最新爬虫数据，更新 index.html，推送到 GitHub
"""
import json, os, re, subprocess, sys
from datetime import datetime

BASE_DIR = '/home/sherry/energy-gas-kb'
NEWS_FILE = os.path.join(BASE_DIR, 'latest_news.json')
INDEX_FILE = os.path.join(BASE_DIR, 'index.html')
GIT_TOKEN = os.environ.get('GIT_PUSH_TOKEN', '')
if not GIT_TOKEN:
    print("❌ 请设置环境变量: export GIT_PUSH_TOKEN=your_github_token")
    sys.exit(1)
GIT_REPO = 'https://lcyue0806-bot:{}@github.com/lcyue0806-bot/energy-gas-kb.git'.format(GIT_TOKEN)

def load_news():
    """加载爬虫最新数据"""
    if not os.path.exists(NEWS_FILE):
        print("❌ 未找到 latest_news.json，请先运行 scraper.py")
        return None
    
    with open(NEWS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_hot_articles_html(articles):
    """根据最新文章生成热点文章 HTML"""
    if not articles:
        return ''
    
    # 取前 8 条作为热点
    hot = articles[:8]
    
    html_parts = []
    for a in hot:
        title = a['title'][:60]
        source = a['source']
        url = a.get('url', '')
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        card = f'''<div class="hot-card">
      <div class="hdate">📅 {date_str}</div>
      <div class="htitle"><a href="{url}" target="_blank">{title} ↗</a></div>
      <div class="hdesc">最新资讯，来自 {source}</div>
      <span class="hsource">📌 {source}</span>
      <a class="hlink" href="{url}" target="_blank">查看原文 →</a>
    </div>'''
        html_parts.append(card)
    
    return '\n'.join(html_parts)

def extract_js_array(html, array_name):
    """从 JavaScript 中提取数组"""
    pattern = array_name + r':\s*\[(.*?)\]\s*,\s*\n'
    match = re.search(pattern, html, re.DOTALL)
    if match:
        return match.group(1)
    return ''

def parse_articles_from_js(js_text):
    """解析 JS 文章数组为 Python 列表"""
    articles = []
    # 匹配每个 {topic:"...",summary:"...",source:"...",date:"...",url:"..."}
    pattern = r'\{topic:"(.*?)",summary:"(.*?)",source:"(.*?)",date:"(.*?)",url:"(.*?)"\}'
    for m in re.finditer(pattern, js_text):
        articles.append({
            'topic': m.group(1),
            'summary': m.group(2),
            'source': m.group(3),
            'date': m.group(4),
            'url': m.group(5)
        })
    return articles

def articles_to_js(articles, indent=4):
    """将文章列表转为 JS 数组字符串"""
    lines = []
    for a in articles:
        t = a['topic'].replace('"', '\\"').replace("'", "\\'")
        s = a['summary'].replace('"', '\\"').replace("'", "\\'")
        src = a['source']
        d = a['date']
        u = a.get('url', '')
        prefix = ' ' * indent
        lines.append(f'{prefix}{{topic:"{t}",summary:"{s}",source:"{src}",date:"{d}",url:"{u}"}}')
    return '[\n' + ',\n'.join(lines) + '\n  ]'

# 重大事件关键词（用于筛选）
MAJOR_KEYWORDS = [
    '行动方案', '规划', '政策', '国家能源局', '发改', '十五五',
    '投产', '交付', '命名', '突破', '首创', '首票', '首家',
    '里程碑', '创新高', '创历史', '正式', '出台', '发布',
    'LNG船', '接收站', '页岩气', '煤层气', '管网', '管道',
    '保供', '增储', '招标', '区块', '碳中和', '碳达峰',
    '国际', '全球', '进口', '出口', '格局',
]

def is_major_event(article):
    """判断是否为重大事件"""
    text = article.get('title', '') + article.get('topic', '')
    # 排除纯地区性小事件
    exclude_patterns = [
        r'关于.{2,8}市.{2,8}的通知', r'关于.{2,8}县', r'关于.{2,8}区',
        r'销售价格', r'阶梯气价', r'统计数据表',
        r'非居民用天然气销售价格',
    ]
    for p in exclude_patterns:
        if re.search(p, text):
            return False
    # 匹配重大关键词
    for kw in MAJOR_KEYWORDS:
        if kw in text:
            return True
    return False

def update_index_html(news_data):
    """更新 index.html - 智能合并热点文章（旧文章自动归档到历史）"""
    if not os.path.exists(INDEX_FILE):
        print("❌ 未找到 index.html")
        return False
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        html = f.read()
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    today = datetime.now().strftime('%Y-%m-%d')
    
    # 1. 更新时间戳
    html = re.sub(r'数据更新：\d{4}-\d{2}-\d{2}.*?<br>', f'数据更新：{today}<br>', html)
    
    # 2. 提取当前热点和历史文章
    hot_js = extract_js_array(html, 'hotArticles')
    hist_js = extract_js_array(html, 'historyArticles')
    
    current_hot = parse_articles_from_js(hot_js)
    current_hist = parse_articles_from_js(hist_js) if hist_js else []
    
    print(f"  当前热点: {len(current_hot)} 篇 | 历史: {len(current_hist)} 篇")
    
    # 3. 从爬虫数据筛选重大事件
    raw_articles = news_data.get('articles', [])
    new_major = []
    for a in raw_articles:
        if is_major_event(a):
            title = a.get('title', '')[:50]
            # 避免与现有热点重复
            if not any(title[:20] in h.get('topic', '') for h in current_hot):
                new_major.append({
                    'topic': title,
                    'summary': f"最新资讯，来自{a['source']}",
                    'source': a['source'],
                    'date': today,
                    'url': a.get('url', '')
                })
    
    print(f"  新重大事件: {len(new_major)} 篇（已去重）")
    
    # 4. 合并：新文章放在前面，旧文章跟在后面
    merged_hot = new_major + current_hot
    # 去重、去空
    seen = set()
    unique_hot = []
    for a in merged_hot:
        key = a['topic'][:30]
        if key and key not in seen:
            seen.add(key)
            unique_hot.append(a)
    
    # 5. 热点保持12篇，多余的移到历史
    new_hot = unique_hot[:12]
    displaced = unique_hot[12:]
    
    # 被替换的旧文章 + 新溢出的 → 加到历史前面
    new_hist = displaced + current_hist
    # 历史最多保留 30 篇
    new_hist = new_hist[:30]
    
    print(f"  新热点: {len(new_hot)} 篇 | 新历史: {len(new_hist)} 篇 | 归档: {len(displaced)} 篇")
    
    # 6. 替换 HTML 中的两个数组
    html = re.sub(
        r'hotArticles:\s*\[.*?\],\s*\n',
        'hotArticles:\n  ' + articles_to_js(new_hot) + ',\n',
        html, flags=re.DOTALL
    )
    
    if new_hist:
        html = re.sub(
            r'historyArticles:\s*\[.*?\],?\s*\n',
            'historyArticles:\n  ' + articles_to_js(new_hist) + ',\n',
            html, flags=re.DOTALL
        )
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ index.html 已更新 ({now})")
    return True

def git_push():
    """提交并推送到 GitHub"""
    os.chdir(BASE_DIR)
    
    # 配置 git
    subprocess.run(['git', 'config', 'user.name', 'Energy KB Bot'], capture_output=True)
    subprocess.run(['git', 'config', 'user.email', 'bot@energy-kb.local'], capture_output=True)
    
    # 添加文件
    subprocess.run(['git', 'add', 'index.html', 'latest_news.json', 'scraper.py', 'data.json'], capture_output=True)
    
    # 提交
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    result = subprocess.run(
        ['git', 'commit', '-m', f'🔄 自动更新 - {now}'],
        capture_output=True, text=True
    )
    print(f"  git commit: {result.stdout.strip()} {result.stderr.strip()}")
    
    # 先从远程拉取最新代码（rebase 避免合并提交）
    env = os.environ.copy()
    env['GIT_SSL_NO_VERIFY'] = '1'
    pull_result = subprocess.run(
        ['git', '-c', 'http.sslVerify=false', 'pull', '--rebase', GIT_REPO, 'master'],
        capture_output=True, text=True, timeout=60, env=env
    )
    if pull_result.returncode == 0:
        print(f"  git pull (rebase): OK")
    else:
        print(f"  git pull warning: {pull_result.stderr[:100]}")

    # 推送
    result = subprocess.run(
        ['git', '-c', 'http.sslVerify=false', 'push', GIT_REPO, 'master'],
        capture_output=True, text=True, timeout=120, env=env
    )
    
    if result.returncode == 0:
        print(f"✅ 已推送到 GitHub")
        return True
    else:
        print(f"❌ 推送失败: {result.stderr[:200]}")
        return False

def main():
    print(f"\n{'='*50}")
    print(f"🔧 自动构建: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print('='*50)
    
    # 1. 运行爬虫
    print("\n📡 Step 1: 运行爬虫...")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, 'scraper.py')], timeout=60)
    
    # 2. 加载数据
    print("\n📊 Step 2: 加载最新数据...")
    news = load_news()
    if not news:
        return
    
    print(f"  共 {news['total_articles']} 篇文章")
    
    # 3. 更新 HTML
    print("\n🔨 Step 3: 更新 index.html...")
    if not update_index_html(news):
        return
    
    # 4. 推送
    print("\n🚀 Step 4: 推送到 GitHub...")
    git_push()
    
    print(f"\n🎉 完成！网站将在几分钟内自动更新")
    print(f"🌐 https://lcyue0806-bot.github.io/energy-gas-kb/")

if __name__ == '__main__':
    main()
