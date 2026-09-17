
import os, re, json, math, html, time
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).parent
SITE = ROOT / "site"
SITE.mkdir(exist_ok=True)

PROFILE = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "").strip()

SEARCH_QUERIES = [
    '2027 校招 视觉设计 品牌 内容 传播 site:jobs.bytedance.com OR site:hr.tencent.com OR site:campus.alibaba.com',
    '2027 校招 海外市场 国际传播 品牌营销 招聘',
    '2027 校招 AI 公司 品牌 内容 视觉 招聘',
    '2027 校招 机器人 具身智能 品牌 市场 运营 招聘',
    '2027 校招 商业航天 品牌 市场 传播 招聘',
    '2027 校招 新能源 海外营销 品牌 视觉 招聘',
    '2027 campus recruitment visual designer global marketing China',
    '2027 graduate brand content communications overseas China',
    '2027 校招 出海 品牌 社媒 视觉 运营 招聘',
    '2027 校招 专精特新 品牌 市场 视觉 招聘'
]

TARGET_TERMS = {
    "visual": ["视觉","设计","visual","graphic","brand design","creative design","ui","ux","展陈","包装","视频"],
    "brand_content": ["品牌","内容","传播","brand","content","communications","social media","marketing","creative","公关","新媒体"],
    "overseas": ["海外","全球","global","international","overseas","出海","外派","东南亚","中东","欧洲","美国","日本","新加坡"],
    "growth": ["ipo","上市","融资","独角兽","高成长","pre-ipo","上市辅导","扩张","全球化"],
    "policy": ["人工智能","ai","机器人","具身智能","商业航天","低空经济","新能源","储能","半导体","先进制造","专精特新"],
    "campus": ["2027","校招","校园招聘","graduate","campus","应届","entry level"]
}

OFFICIAL_HINTS = [
    "career", "careers", "jobs", "job", "hr.", "recruit", "join", "zhaopin",
    "zhiye", "feishu", "mokahr"
]

BAD_DOMAINS = [
    "baidu.com/s", "google.com", "bing.com", "douyin.com", "xiaohongshu.com"
]

def serper_search(q, num=10):
    if not SERPER_API_KEY:
        return []
    r = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": q, "num": num, "gl": "cn", "hl": "zh-cn"},
        timeout=30
    )
    r.raise_for_status()
    data = r.json()
    return data.get("organic", [])

def safe_get_text(url):
    try:
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=12, allow_redirects=True)
        if r.status_code >= 400:
            return ""
        ctype = r.headers.get("content-type","")
        if "text/html" not in ctype:
            return ""
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","noscript"]):
            tag.decompose()
        return " ".join(soup.stripped_strings)[:18000]
    except Exception:
        return ""

def official_score(url):
    u = url.lower()
    host = urlparse(url).netloc.lower()
    score = 0
    if any(h in u for h in OFFICIAL_HINTS):
        score += 1
    if any(x in host for x in ["nowcoder","wondercv","shixiseng","nankai","hust","edu.cn"]):
        score -= 0.3
    return score

def find_company(title, snippet):
    raw = f"{title} {snippet}"
    # Common separators. Keep short first segment if it looks like a company.
    parts = re.split(r"[-_|｜—·:：]", raw)
    for p in parts:
        p = p.strip()
        if 2 <= len(p) <= 24 and not re.search(r"2027|校招|招聘|岗位|职位", p, re.I):
            return p
    return "待核实公司"

def infer_title(title, snippet):
    t = re.sub(r"\s+", " ", title).strip()
    return t[:80]

def term_hits(text, terms):
    t = text.lower()
    return sum(1 for x in terms if x.lower() in t)

def score_job(title, snippet, page_text, url):
    text = f"{title} {snippet} {page_text}".lower()
    role_fit = min(30, 4 * (
        term_hits(text, TARGET_TERMS["visual"]) +
        term_hits(text, TARGET_TERMS["brand_content"])
    ))
    brand_visual = min(20, 4 * (
        term_hits(text, TARGET_TERMS["visual"]) +
        term_hits(text, TARGET_TERMS["brand_content"])
    ))
    overseas = min(15, 5 * term_hits(text, TARGET_TERMS["overseas"]))
    growth = min(15, 5 * term_hits(text, TARGET_TERMS["growth"]))
    policy = min(10, 3 * term_hits(text, TARGET_TERMS["policy"]))
    scale = 5 if any(x in text for x in ["集团","全球","上市公司","头部","领先","500强","独角兽"]) else 2
    urgency = 5 if any(x in text for x in ["截止","deadline","招满即止","尽快"]) else 2
    score = role_fit + brand_visual + overseas + growth + policy + scale + urgency
    score += official_score(url) * 3
    return max(50, min(99, int(round(score))))

def tags_for(text):
    t = text.lower()
    tags = []
    mapping = [
        ("🌍 海外/全球", TARGET_TERMS["overseas"]),
        ("🎨 视觉/创意", TARGET_TERMS["visual"]),
        ("📣 品牌/内容", TARGET_TERMS["brand_content"]),
        ("🚀 高成长", TARGET_TERMS["growth"]),
        ("🏭 政策产业", TARGET_TERMS["policy"]),
        ("🎓 2027校招", TARGET_TERMS["campus"]),
    ]
    for label, terms in mapping:
        if term_hits(t, terms):
            tags.append(label)
    return tags[:5]

def resume_tip(text):
    t = text.lower()
    tips = []
    if term_hits(t, TARGET_TERMS["overseas"]):
        tips.append("把 UNU Macau 的中英文传播、国际会议、跨文化协作和海外受众意识放到前两条")
    if term_hits(t, TARGET_TERMS["visual"]):
        tips.append("强调出版物设计、版式、视频、视觉叙事和艺术训练，作品集放真实项目")
    if term_hits(t, TARGET_TERMS["brand_content"]):
        tips.append("突出社媒选题、内容策划、研究转译、机构品牌表达与 campaign 思维")
    if term_hits(t, TARGET_TERMS["policy"]):
        tips.append("强调你对 AI / 数字技术议题的理解，以及把复杂研究转化为公众内容的能力")
    if not tips:
        tips.append("用 UNU Macau 的内容、视觉和国际传播经验对齐 JD 关键词，减少纯学术描述")
    return "；".join(tips[:2])

def relevance_reason(text):
    t = text.lower()
    reasons = []
    if term_hits(t, TARGET_TERMS["overseas"]):
        reasons.append("国际化/海外场景")
    if term_hits(t, TARGET_TERMS["visual"]):
        reasons.append("视觉与创意能力")
    if term_hits(t, TARGET_TERMS["brand_content"]):
        reasons.append("品牌内容与传播")
    if term_hits(t, TARGET_TERMS["policy"]):
        reasons.append("AI/硬科技与政策产业")
    if term_hits(t, TARGET_TERMS["growth"]):
        reasons.append("成长或资本化信号")
    return "、".join(reasons[:3]) or "与内容传播和视觉能力有可迁移性"

def is_candidate(title, snippet, page_text, url):
    text = f"{title} {snippet} {page_text}".lower()
    if any(b in url.lower() for b in BAD_DOMAINS):
        return False
    campus = term_hits(text, TARGET_TERMS["campus"]) > 0
    role = term_hits(text, TARGET_TERMS["visual"]) + term_hits(text, TARGET_TERMS["brand_content"]) > 0
    return campus and role

def collect_jobs():
    seen = set()
    jobs = []
    for q in SEARCH_QUERIES:
        try:
            results = serper_search(q, num=10)
        except Exception as e:
            print("Search failed:", q, e)
            continue
        for item in results:
            url = item.get("link","").strip()
            title = item.get("title","").strip()
            snippet = item.get("snippet","").strip()
            if not url or not title:
                continue
            key = re.sub(r"[?#].*$","",url)
            if key in seen:
                continue
            seen.add(key)

            page_text = safe_get_text(url)
            if not is_candidate(title, snippet, page_text, url):
                continue

            full = f"{title} {snippet} {page_text}"
            jobs.append({
                "company": find_company(title, snippet),
                "title": infer_title(title, snippet),
                "score": score_job(title, snippet, page_text, url),
                "url": url,
                "reason": relevance_reason(full),
                "resume_tip": resume_tip(full),
                "tags": tags_for(full),
                "source": "官方/公开招聘页" if official_score(url) > 0.5 else "公开招聘信息",
            })
            time.sleep(0.15)
    # Deduplicate similar title+company
    uniq = {}
    for j in jobs:
        k = re.sub(r"\W+","", (j["company"] + j["title"]).lower())[:90]
        if k not in uniq or j["score"] > uniq[k]["score"]:
            uniq[k] = j
    jobs = sorted(uniq.values(), key=lambda x:(x["score"], official_score(x["url"])), reverse=True)
    return jobs[:30]

def fallback_jobs():
    return [
        {
            "company":"Job Radar 已部署",
            "title":"请在 GitHub Secrets 中添加 SERPER_API_KEY，启用每日真实岗位搜索",
            "score":99,
            "url":"https://serper.dev/",
            "reason":"当前自动化结构已经运行，但没有搜索 API Key 时无法在 GitHub Actions 中主动检索全网最新岗位。",
            "resume_tip":"添加 Key 后，脚本会自动搜索 2027 校招、海外、视觉、品牌、内容、AI/机器人/商业航天等岗位。",
            "tags":["⚙️ 配置提示"],
            "source":"系统提示"
        }
    ]

def build_html(jobs):
    payload = json.dumps(jobs, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Zoey Job Radar</title>
<style>
:root{{--bg:#fff8fb;--card:#fff;--ink:#241d22;--muted:#766b73;--rose:#d65c8e;--soft:#f9e7ef;--line:#efdbe4}}
*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(180deg,#fff4f9,#fff 42%);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink)}}
.wrap{{max-width:1180px;margin:auto;padding:38px 22px 70px}} .eyebrow{{font-size:12px;font-weight:800;letter-spacing:.14em;color:var(--rose)}}h1{{font-size:46px;letter-spacing:-2px;margin:8px 0}}.lead{{max-width:800px;color:var(--muted);line-height:1.75}}
.stats{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:28px 0}}.stat{{border:1px solid var(--line);background:#fff;border-radius:18px;padding:18px}}.stat b{{display:block;font-size:28px}}.stat span{{font-size:12px;color:var(--muted)}}
.toolbar{{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}}input,select{{border:1px solid var(--line);background:#fff;border-radius:12px;padding:11px 13px;font:inherit}}input{{flex:1;min-width:260px}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px}}.job{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px;display:flex;flex-direction:column;box-shadow:0 8px 22px rgba(70,30,45,.045)}}.top{{display:flex;justify-content:space-between;gap:12px}}
.company{{font-size:13px;color:var(--rose);font-weight:800}}h2{{font-size:18px;line-height:1.45;margin:7px 0}}.score{{font-size:23px;font-weight:800;color:var(--rose)}}.score small{{font-size:10px;color:var(--muted)}}
.tags{{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}}.tag{{background:var(--soft);padding:5px 8px;border-radius:8px;font-size:11px}}.txt{{font-size:13px;line-height:1.65;color:#51464d}}.tip{{margin-top:10px;padding-top:10px;border-top:1px dashed var(--line);font-size:12px;line-height:1.65;color:#61535b}}
.meta{{font-size:11px;color:var(--muted);margin-top:12px}}a.btn{{display:inline-block;margin-top:14px;background:#241e23;color:#fff;text-decoration:none;padding:10px 13px;border-radius:10px;font-size:12px;font-weight:700}}
.footer{{color:var(--muted);font-size:11px;line-height:1.7;margin-top:28px}}
@media(max-width:760px){{h1{{font-size:34px}}.stats{{grid-template-columns:repeat(2,1fr)}}.grid{{grid-template-columns:1fr}}.wrap{{padding:26px 14px 50px}}}}
</style></head>
<body><div class="wrap">
<div class="eyebrow">ZOEY · PERSONAL JOB RADAR</div>
<h1>Daily Opportunities</h1>
<div class="lead">每天 08:30 自动更新。优先筛选：2027 校招 / Entry Level、品牌、内容、视觉、国际传播、海外市场、高成长公司、IPO Radar、AI / 机器人 / 商业航天 / 新能源等政策产业。</div>
<div class="stats">
<div class="stat"><b>{len(jobs)}</b><span>今日岗位</span></div>
<div class="stat"><b>{sum(1 for j in jobs if j["score"]>=90)}</b><span>90+ 高匹配</span></div>
<div class="stat"><b>{sum(1 for j in jobs if any("海外" in t or "全球" in t for t in j["tags"]))}</b><span>海外 / 全球</span></div>
<div class="stat"><b>08:30</b><span>每日更新时间</span></div>
</div>
<div class="toolbar"><input id="q" placeholder="搜索公司、岗位、海外、视觉、AI…"><select id="f"><option value="all">全部</option><option>海外</option><option>视觉</option><option>品牌</option><option>AI</option><option>政策产业</option></select></div>
<div class="grid" id="grid"></div>
<div class="footer">匹配分仅表示与你当前经历的相关程度，不代表录取概率。岗位状态变化快，投递前请在原页面再次确认截止时间、学历与专业要求。</div>
</div>
<script>
const jobs={payload};
const grid=document.getElementById('grid'),q=document.getElementById('q'),f=document.getElementById('f');
function render(){{
 const query=q.value.trim().toLowerCase(), filter=f.value.toLowerCase();
 const list=jobs.filter(j=>{{const t=(j.company+j.title+j.reason+j.resume_tip+j.tags.join(' ')).toLowerCase();return(!query||t.includes(query))&&(filter==='all'||t.includes(filter));}});
 grid.innerHTML=list.map(j=>`<article class="job"><div class="top"><div><div class="company">${{j.company}}</div><h2>${{j.title}}</h2></div><div class="score">${{j.score}}<small>% match</small></div></div><div class="tags">${{j.tags.map(t=>`<span class="tag">${{t}}</span>`).join('')}}</div><div class="txt"><b>为什么适合：</b>${{j.reason}}</div><div class="tip"><b>简历调整：</b>${{j.resume_tip}}</div><div class="meta">${{j.source}}</div><a class="btn" href="${{j.url}}" target="_blank" rel="noopener">查看 / 投递 ↗</a></article>`).join('');
}}
q.addEventListener('input',render);f.addEventListener('change',render);render();
</script></body></html>"""

def main():
    jobs = collect_jobs() if SERPER_API_KEY else fallback_jobs()
    (SITE / "index.html").write_text(build_html(jobs), encoding="utf-8")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    (SITE / "jobs.json").write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(jobs)} jobs")

if __name__ == "__main__":
    main()
