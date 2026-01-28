#!/usr/bin/env python3
"""
 Jarvis AI Paper Tracker - Intelligent Version
 Orchestrates arXiv fetching, Claude Code review, and Telegram delivery
"""

import json
import subprocess
import re
from datetime import datetime

CONFIG = {
    'arxiv_categories': ['cs.AI', 'cs.LG', 'cs.MA'],
    'keywords': ['agent', 'multi-agent', 'collaboration', 'coordination', 
                 'task planning', 'llm', 'reasoning', 'autonomous', 'swarm', 
                 'collective', 'reinforcement', 'hierarchical', 'distributed',
                 'emergent', 'foundation model'],
    'max_papers': 20,
}

REVIEW_PROMPT = """You are an expert AI researcher. Review these arXiv papers for a multi-agent systems researcher.

Papers:
{papers}

For each paper:
1. Relevance Score (1-5): Relevance to multi-agent systems, LLM agents, collaborative AI?
2. Key Insight: One sentence explaining the main contribution.
3. Should Read? (yes/no/maybe)
4. Tags: Choose from [multi-agent, planning, reasoning, LLM, swarm, coordination, theory, application, survey]

Return pure JSON:
{{
  "reviews": [{{"id": "xxx", "score": 5, "key_insight": "...", "should_read": "yes", "tags": ["multi-agent"]}}],
  "summary": "Brief 2-3 sentence overview of the research landscape",
  "top_pick": "ID of the most important paper"
}}
"""

def fetch_arxiv_papers():
    """Fetch papers from arXiv API using curl"""
    papers = []
    
    for category in CONFIG['arxiv_categories']:
        url = f'https://export.arxiv.org/api/query?search_query=cat:{category}&start=0&max_results=30&sortBy=submittedDate&sortOrder=descending'
        
        result = subprocess.run(['curl', '-sL', url], capture_output=True, text=True, timeout=30)
        data = result.stdout
        entries = re.findall(r'<entry>(.*?)</entry>', data, re.DOTALL)
        
        for entry in entries:
            id_match = re.search(r'<id>(.*?)</id>', entry)
            if id_match:
                raw_id = id_match.group(1)
                paper_id = raw_id.split('/abs/')[-1].split('v')[0]
            else:
                continue
            
            title_match = re.search(r'<title>(.*?)</title>', entry, re.DOTALL)
            title = title_match.group(1).replace('\n', ' ').strip() if title_match else "No title"
            
            summary_match = re.search(r'<summary>(.*?)</summary>', entry, re.DOTALL)
            summary = summary_match.group(1).replace('\n', ' ').strip() if summary_match else ""
            
            authors = re.findall(r'<name>(.*?)</name>', entry)
            published_match = re.search(r'<published>(\d{4}-\d{2}-\d{2})</published>', entry)
            published = published_match.group(1) if published_match else "2026-01-01"
            
            text = (title + ' ' + summary).lower()
            score = sum(1 for kw in CONFIG['keywords'] if kw in text)
            
            if score > 0:
                papers.append({
                    'id': paper_id,
                    'title': title,
                    'summary': summary[:400],
                    'authors': authors[:3],
                    'published': published,
                    'url': f'https://arxiv.org/abs/{paper_id}',
                    'raw_score': score,
                    'category': category
                })
    
    papers.sort(key=lambda x: (-x['raw_score'], x['published']))
    seen = set()
    unique_papers = []
    for p in papers:
        if p['id'] not in seen:
            seen.add(p['id'])
            unique_papers.append(p)
    
    return unique_papers[:CONFIG['max_papers']]

def review_with_claude_code(papers):
    """Send papers to Claude Code for intelligent review"""
    if not papers:
        return None
    
    papers_json = json.dumps([{
        'id': p['id'],
        'title': p['title'],
        'summary': p['summary'],
        'authors': p['authors'],
        'published': p['published'],
        'url': p['url'],
        'category': p['category']
    } for p in papers], indent=2, ensure_ascii=False)
    
    prompt = REVIEW_PROMPT.format(papers=papers_json)
    
    try:
        result = subprocess.run(
            ['claude', '-p', prompt],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            json_match = re.search(r'\{[\s\S]*\}', result.stdout)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        print(f"Claude Code review failed: {e}")
    
    return None

def format_briefing(papers, review_result):
    """Compile papers and review into a nice briefing"""
    if not papers:
        return None
    
    date = datetime.now().strftime('%Y-%m-%d')
    briefing = f"📚 **Jarvis 论文简报** - {date}\n\n"
    briefing += f"🔍 从 arXiv 抓取 {len(papers)} 篇相关论文\n"
    
    if review_result:
        briefing += f"🧠 Claude Code 智能审阅完成\n\n"
        briefing += f"---\n\n{review_result.get('summary', '')}\n\n"
        briefing += f"---\n\n"
        
        reviews = {r['id']: r for r in review_result.get('reviews', [])}
        
        for paper in papers:
            review = reviews.get(paper['id'], {})
            should_read = review.get('should_read', 'maybe')
            
            if should_read == 'yes':
                icon = "⭐⭐⭐"
            elif should_read == 'maybe':
                icon = "⭐"
            else:
                icon = "○"
            
            tags = ', '.join(review.get('tags', []))
            key_insight = review.get('key_insight', '')[:100]
            
            briefing += f"{icon} **{paper['title'][:70]}...**\n"
            briefing += f"📅 {paper['published']} | {paper['category']}\n"
            if tags:
                briefing += f"Tags: {tags}\n"
            if key_insight:
                briefing += f"💡 {key_insight}\n"
            briefing += f"🔗 [arXiv]({paper['url']})\n\n"
    else:
        for paper in papers[:5]:
            stars = "⭐" * min(paper['raw_score'], 5)
            briefing += f"{stars} **{paper['title'][:60]}...**\n"
            briefing += f"📅 {paper['published']} | [arXiv]({paper['url']})\n\n"
    
    briefing += f"---\n🤖 Jarvis AI 论文助手 | 共 {len(papers)} 篇"
    
    return briefing

def send_to_telegram(message):
    """Send briefing to Harry via Clawdbot"""
    if not message:
        return False
    
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
        import urllib.request
        req = urllib.request.Request(
            f"{gateway_url}/api/message",
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return True
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return False

def main():
    print(f"\n🤖 Jarvis 论文助手 - {datetime.now().strftime('%H:%M')}")
    print("=" * 50)
    
    print("📥 Step 1: 从 arXiv 抓取论文...")
    papers = fetch_arxiv_papers()
    print(f"   找到 {len(papers)} 篇相关论文")
    
    if not papers:
        print("   没有找到新论文")
        return
    
    print("🧠 Step 2: 发送至 Claude Code 智能审阅...")
    review_result = review_with_claude_code(papers)
    if review_result:
        print("   ✅ Claude Code 审阅完成")
    else:
        print("   ⚠️ Claude Code 不可用，使用基础评分")
    
    print("📝 Step 3: 撰写简报...")
    briefing = format_briefing(papers, review_result)
    
    print("📤 Step 4: 发送至 Telegram...")
    if send_to_telegram(briefing):
        print("   ✅ 已发送！")
    else:
        print("   ⚠️ 发送失败，仅打印")
        print("\n" + briefing)

if __name__ == "__main__":
    main()
