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

def update_index_html(news_data):
    """更新 index.html 中的热点文章和历史数据"""
    if not os.path.exists(INDEX_FILE):
        print("❌ 未找到 index.html")
        return False
    
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 1. 更新 "数据更新" 时间戳
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = re.sub(
        r'数据更新：\d{4}-\d{2}-\d{2}',
        f'数据更新：{now}（自动刷新）',
        html
    )
    html = re.sub(
        r'验证时间：\d{4}-\d{2}-\d{2}',
        f'自动刷新时间：{now}',
        html
    )
    
    # 2. 替换 Hot Articles 数据（JavaScript DATA.hotArticles）
    articles = news_data.get('articles', [])
    hot_js = []
    for a in articles[:8]:
        title = a['title'].replace("'", "\\'").replace('"', '\\"')
        source = a['source']
        url = a.get('url', '')
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        hot_js.append(
            '    {topic:"' + title[:50] + '",'
            'summary:"最新资讯，来自' + source + '",'
            'source:"' + source + '",'
            'date:"' + date_str + '",'
            'url:"' + url + '"}'
        )
    
    new_hot_articles = ',\n'.join(hot_js)
    
    # 替换 hotArticles 数组
    html = re.sub(
        r'hotArticles:\s*\[.*?\]',
        'hotArticles: [\n' + new_hot_articles + '\n  ]',
        html,
        flags=re.DOTALL
    )
    
    # 3. 替换 Updated badge
    total_articles = news_data.get('total_articles', 0)
    html = re.sub(
        r'共抓取 \d+ 篇最新文章',
        f'共抓取 {total_articles} 篇最新文章',
        html
    )
    
    # 4. 更新时间戳
    html = re.sub(
        r'const lastUpdate = ".*?"',
        f'const lastUpdate = "{now}"',
        html
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
    
    # 推送
    env = os.environ.copy()
    env['GIT_SSL_NO_VERIFY'] = '1'
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
