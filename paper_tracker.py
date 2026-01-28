#!/usr/bin/env python3
"""
 Multi-Agent Systems Paper Tracker
 Sends daily paper recommendations to Telegram
"""

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

PAPERS_FILE = '/home/ubuntu/jarvis-dashboard/papers_tracked.json'

KEYWORDS = [
    'multi-agent', 'multi agent', 'agent', 'collaboration', 'cooperation',
    'task planning', 'task allocation', 'coordination', 'llm', 'reasoning',
    'autonomous', 'swarm', 'collective', 'distributed', 'emergent'
]

def fetch_arxiv_list():
    subprocess.run([
        'curl', '-s', '-L', '-A', 'Mozilla/5.0',
        'https://arxiv.org/list/cs.AI/recent?show=50',
        '-o', '/tmp/arxiv.html'
    ], check=True)
    with open('/tmp/arxiv.html', 'r') as f:
        return f.read()

def parse_papers(html):
    papers = []
    ids = re.findall(r'href ="/abs/(\d+\.\d+)"', html)
    titles = re.findall(r"<span class='descriptor'>Title:</span>\s*([^<]+)", html)
    abstracts = re.findall(r'<meta name="citation_abstract" content="([^"]+)"', html)
    
    for i, paper_id in enumerate(ids):
        title = titles[i].strip() if i < len(titles) else "Unknown"
        abstract = abstracts[i].replace('\n', ' ').strip()[:200] if i < len(abstracts) else ""
        score = sum(1 for kw in KEYWORDS if kw in (title + abstract).lower())
        
        papers.append({
            'id': paper_id,
            'link': f"https://arxiv.org/{paper_id}",
            'title': title,
            'abstract': abstract,
            'score': score
        })
    return papers

def load_tracked():
    if Path(PAPERS_FILE).exists():
        with open(PAPERS_FILE, 'r') as f:
            data = json.load(f)
            return set(data.get('tracked', [])), data.get('last_run')
    return set(), None

def save_tracked(tracked):
    with open(PAPERS_FILE, 'w') as f:
        json.dump({
            'tracked': list(tracked),
            'last_run': datetime.now().isoformat()
        }, f)

def send_to_telegram(message):
    """Send message to Harry via Clawdbot"""
    import urllib.request
    import json as json_lib
    
    try:
        with open('/home/ubuntu/.clawdbot/config.json', 'r') as f:
            config = json_lib.load(f)
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
            data=json_lib.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.read().decode()
    except Exception as e:
        print(f"⚠️ Telegram 发送失败: {e}")
        return None

def main():
    print(f"\n📚 论文追踪器 - {datetime.now().strftime('%H:%M')}")
    
    tracked, last_run = load_tracked()
    html = fetch_arxiv_list()
    papers = parse_papers(html)
    
    # Filter new relevant papers
    relevant = [p for p in papers if p['score'] > 0 and p['id'] not in tracked]
    relevant.sort(key=lambda x: (-x['score'], x['id']))
    
    print(f"  发现 {len(relevant)} 篇新相关论文")
    
    if relevant:
        # Format message for Telegram
        message = f"🎯 **每日论文推荐** - {datetime.now().strftime('%m-%d')}\n\n"
        
        for i, p in enumerate(relevant[:5], 1):
            message += f"**{i}. {p['title'][:55]}...**\n"
            message += f"🔗 {p['link']}\n"
            message += f"📊 相关度: {'⭐'*p['score']}\n\n"
        
        message += f"---\n共 {len(relevant)} 篇新论文 | 只显示前 5 篇"
        
        # Send to Telegram
        result = send_to_telegram(message)
        if result:
            print(f"  ✅ 已发送到 Telegram")
        else:
            print(f"  ⚠️ Telegram 发送失败，仅打印到控制台")
            print(message)
        
        # Track these papers
        for p in relevant:
            tracked.add(p['id'])
        save_tracked(tracked)
    else:
        print("  ✅ 暂无新的相关论文")

if __name__ == "__main__":
    main()
