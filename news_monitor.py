#!/usr/bin/env python3
"""
 Research Information Monitor
 Monitors conferences, tech news, and GitHub trends for AI research
"""

import json
import re
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path

CONFIG_FILE = '/home/ubuntu/jarvis-dashboard/news_tracked.json'

# Monitor configuration
CONFERENCES = {
    'NeurIPS': 'https://nips.cc/Conferences/2025',
    'ICML': 'https://icml.cc/2025',
    'ICLR': 'https://iclr.cc/conference/2025',
    'AAMAS': 'https://aamas2025.org/',
    'CoRL': 'https://www.corl.org/',
    'AAAI': 'https://aaai.org/Conference/aaai-25/',
}

NEWS_SOURCES = {
    'hacker_news': 'https://news.ycombinator.com',
    'arxiv_announce': 'https://arxiv.org/list/cs.AI/recent',
}

BLOGS = {
    'Andrew Ng': 'https://www.andrewng.org/',
    'Lilac Weng': 'https://lilianweng.github.io/',
    'Sebastian Ruder': 'https://ruder.io/',
    'Jay Alammar': 'https://jalammar.github.io/',
}

KEYWORDS = [
    'multi-agent', 'multi agent', 'agent', 'collaboration', 'cooperation',
    'task planning', 'task allocation', 'coordination', 'llm', 'reasoning',
    'autonomous', 'swarm', 'collective', 'distributed', 'emergent',
    'reinforcement learning', 'foundation model', 'generative ai'
]

def fetch_url(url):
    """Fetch URL content"""
    try:
        subprocess.run([
            'curl', '-s', '-L', '-A', 'Mozilla/5.0',
            url, '-o', '/tmp/news_fetch.html'
        ], check=True, timeout=30)
        with open('/tmp/news_fetch.html', 'r') as f:
            return f.read()
    except Exception as e:
        print(f"⚠️ Fetch failed: {e}")
        return None

def parse_hacker_news():
    """Parse Hacker News AI-related stories"""
    html = fetch_url('https://news.ycombinator.com')
    if not html:
        return []
    
    stories = []
    # Parse story links with AI keywords
    for match in re.finditer(r'<tr class="athing".*?<a href="(.*?)".*?class="titlelink">(.*?)</a>.*?class="subtext">.*?(\d+) points', html, re.DOTALL):
        url, title, points = match.groups()
        if any(kw in title.lower() for kw in ['ai', 'llm', 'agent', 'gpt', 'neural']):
            stories.append({
                'source': 'Hacker News',
                'title': title,
                'url': url if url.startswith('http') else f'https://news.ycombinator.com/{url}',
                'points': int(points)
            })
    return stories[:5]

def parse_github_trending(lang='python', since='daily'):
    """Parse GitHub Trending for AI projects"""
    html = fetch_url(f'https://github.com/trending?spoken_language_code=en&l={lang}&since={since}')
    if not html:
        return []
    
    repos = []
    for match in re.finditer(r'<article class="Box-row".*?href="(.*?)".*?class="h3 lh-condensed">(.*?)</span>.*?(\d+) stars', html, re.DOTALL):
        repo_url, repo_name, stars = match.groups()
        # Filter for AI-related repos
        desc = fetch_url(f'https://github.com{repo_url}')
        if desc and any(kw in (repo_name + desc).lower() for kw in KEYWORDS):
            repos.append({
                'source': 'GitHub Trending',
                'name': repo_name.strip(),
                'url': f'https://github.com{repo_url}',
                'stars': int(stars.replace(',', ''))
            })
    return repos[:5]

def parse_conferences():
    """Monitor conference updates (accepted papers, important dates)"""
    updates = []
    
    # NeurIPS 2025
    html = fetch_url('https://nips.cc/Conferences/2025')
    if html:
        # Look for accepted papers, deadlines, etc.
        if 'accepted' in html.lower() or 'deadline' in html.lower():
            updates.append({
                'source': 'NeurIPS 2025',
                'title': '会议更新',
                'url': 'https://nips.cc/Conferences/2025',
                'detail': '有新的公告或更新'
            })
    
    # ICLR 2025
    html = fetch_url('https://iclr.cc/conference/2025')
    if html:
        if 'accepted' in html.lower() or 'deadline' in html.lower():
            updates.append({
                'source': 'ICLR 2025',
                'title': '会议更新',
                'url': 'https://iclr.cc/conference/2025',
                'detail': '有新的公告或更新'
            })
    
    return updates[:5]

def parse_ai_blogs():
    """Monitor AI research blogs"""
    posts = []
    
    blog_urls = {
        'Lilac Weng': 'https://lilianweng.github.io/',
        'Sebastian Ruder': 'https://ruder.io/',
    }
    
    for name, url in blog_urls.items():
        html = fetch_url(url)
        if html:
            # Look for recent posts
            for match in re.finditer(r'href="(.*?)".*?>(.*?)</a>', html):
                post_url, title = match.groups()
                if title and len(title) > 10 and not title.startswith('http'):
                    if any(kw in title.lower() for kw in ['agent', 'llm', 'multi', 'reasoning', 'planning']):
                        full_url = post_url if post_url.startswith('http') else f'{url.rstrip("/")}/{post_url.lstrip("/")}'
                        posts.append({
                            'source': name,
                            'title': title.strip()[:80],
                            'url': full_url
                        })
    return posts[:5]

def send_to_telegram(message):
    """Send message to Harry via Clawdbot"""
    try:
        with open('/home/ubuntu/.clawdbot/config.json', 'r') as f:
            config = json.load(f)
        gateway_url = config.get('gatewayUrl', 'http://localhost:5000')
    except:
        gateway_url = 'http://localhost:5000'
    
    data = {
        "action": "send",
        "channel": "telegram",
        "target": "8077045709",
        "message": message
    }
    
    try:
        req = urllib.request.Request(
            f"{gateway_url}/api/message",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode()
    except Exception as e:
        print(f"⚠️ Telegram 发送失败: {e}")
        return None

def load_config():
    """Load tracked items"""
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'tracked_hn': [], 'tracked_gh': [], 'tracked_conf': [], 'tracked_blog': [], 'last_run': None}

def save_config(data):
    """Save tracked items"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f)

def format_message(news_items, github_items, conf_items, blog_items):
    """Format news for Telegram"""
    now = datetime.now().strftime('%m-%d %H:%M')
    
    message = f"🔬 **科研资讯速递** - {now}\n\n"
    
    if news_items:
        message += "📰 **技术新闻**\n"
        for i, item in enumerate(news_items[:5], 1):
            message += f"{i}. {item['title'][:60]}...\n"
            message += f"   👍 {item['points']} points | [链接]({item['url']})\n"
        message += "\n"
    
    if github_items:
        message += "⭐ **GitHub Trending**\n"
        for i, item in enumerate(github_items[:5], 1):
            message += f"{i}. {item['name']}\n"
            message += f"   ⭐ {item['stars']} | [链接]({item['url']})\n"
        message += "\n"
    
    if conf_items:
        message += "🎓 **顶会动态**\n"
        for i, item in enumerate(conf_items[:3], 1):
            message += f"{i}. {item['source']}: {item['detail']}\n"
            message += f"   [链接]({item['url']})\n"
        message += "\n"
    
    if blog_items:
        message += "📝 **博客更新**\n"
        for i, item in enumerate(blog_items[:3], 1):
            message += f"{i}. {item['source']}: {item['title']}\n"
            message += f"   [链接]({item['url']})\n"
    
    message += "\n---\n🤖 Jarvis 科研助理"
    return message

def main():
    print(f"\n🔍 科研信息监控 - {datetime.now().strftime('%H:%M')}")
    
    config = load_config()
    
    # Fetch news
    print("  📰 抓取 Hacker News...")
    hn_news = parse_hacker_news()
    
    print("  ⭐ 抓取 GitHub Trending...")
    gh_repos = parse_github_trending()
    
    print("  🎓 监控顶会动态...")
    conf_updates = parse_conferences()
    
    print("  📝 监控 AI 博客...")
    blog_posts = parse_ai_blogs()
    
    # Filter new items
    new_hn = [n for n in hn_news if n['url'] not in config['tracked_hn']]
    new_gh = [r for r in gh_repos if r['url'] not in config['tracked_gh']]
    new_conf = [c for c in conf_updates if c['url'] not in config['tracked_conf']]
    new_blog = [b for b in blog_posts if b['url'] not in config.get('tracked_blog', [])]
    
    print(f"  发现 {len(new_hn)} 条新闻, {len(new_gh)} 个项目, {len(new_conf)} 个会议更新, {len(new_blog)} 篇博客")
    
    if new_hn or new_gh or new_conf or new_blog:
        # Format and send
        message = format_message(new_hn, new_gh, new_conf, new_blog)
        result = send_to_telegram(message)
        
        if result:
            print("  ✅ 已发送到 Telegram")
        else:
            print("  ⚠️ Telegram 发送失败")
            print(message)
        
        # Update tracked
        for n in new_hn:
            config['tracked_hn'].append(n['url'])
        for r in new_gh:
            config['tracked_gh'].append(r['url'])
        for c in new_conf:
            config['tracked_conf'].append(c['url'])
        for b in new_blog:
            if 'tracked_blog' not in config:
                config['tracked_blog'] = []
            config['tracked_blog'].append(b['url'])
        config['last_run'] = datetime.now().isoformat()
        save_config(config)
    else:
        print("  ✅ 暂无新的重要资讯")

if __name__ == "__main__":
    main()
