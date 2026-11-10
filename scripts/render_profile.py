#!/usr/bin/env python3
"""Render GitHub profile README cards as animated, GitHub-safe SVGs.

Requires Python 3.10+. Optional: pip install fonttools (for Amiamie subsetting).
Set GH_TOKEN for contribution data; STATIC=1 emits animation-free final-state SVGs.
"""
from __future__ import annotations
import base64, json, os, re, subprocess, urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "cards"
DATA = ROOT / "data" / "profile.json"
BG, SURFACE, SAGE, GOLD, INK = "#e5e5e0", "#393632", "#8b8b73", "#cfa355", "#393632"
STATIC = os.getenv("STATIC", "0") == "1"
WIDTH = 960

def esc(v): return escape(str(v or ""), {'"': '&quot;'})

def load_data():
    if DATA.exists():
        return json.loads(DATA.read_text())
    return {"name":"Sayantan Bera","tagline":"Full Stack Web Developer · Building ZenBlocks UI Library","links":[
        {"label":"Portfolio","url":"https://sayantanbera.vercel.app/"},
        {"label":"LinkedIn","url":"https://linkedin.com/in/sayantan-bera-b11300202"},
        {"label":"Email","url":"mailto:sayantanbera25@gmail.com"}],
        "featured_repos":[],"contributions":{}}

def github(query, variables=None):
    token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token: return None
    body = json.dumps({"query":query,"variables":variables or {}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
        headers={"Authorization":f"Bearer {token}","Content-Type":"application/json","User-Agent":"profile-card-renderer"})
    with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)

def refresh(data):
    user = os.getenv("GITHUB_REPOSITORY_OWNER", "sayantan-025")
    q = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}} repositories(first:100,ownerAffiliations:OWNER, orderBy:{field:UPDATED_AT,direction:DESC}){nodes{name description url stargazerCount isPrivate}}}}"""
    try:
        result = github(q, {"login":user}) or {}
        u = result.get("data",{}).get("user")
        if not u: return data
        cal = u["contributionsCollection"]["contributionCalendar"]
        days = [d for w in cal["weeks"] for d in w["contributionDays"]]
        months = {}
        for d in days:
            m=d["date"][:7]; months[m]=months.get(m,0)+d["contributionCount"]
        active=[d for d in days if d["contributionCount"]>0]
        busiest=max(days,key=lambda d:d["contributionCount"],default={"date":"—","contributionCount":0})
        streak=best=run=0
        for d in days:
            if d["contributionCount"]: run+=1; best=max(best,run)
            else: run=0
        data["contributions"]={"months":months,"total":cal["totalContributions"],"active_days":len(active),
            "busiest_day":busiest["date"],"busiest_count":busiest["contributionCount"],"longest_streak":best,
            "days":days}
        if not data.get("featured_repos"):
            data["featured_repos"]=[{"name":r["name"],"description":r.get("description") or "A project in progress",
                "url":r["url"],"stars":r["stargazerCount"]} for r in u["repositories"]["nodes"] if not r["isPrivate"]][:4]
    except Exception as e: print(f"Contribution refresh skipped: {e}")
    return data

def font_css():
    src=os.getenv("AMIAMIE_FONT_URL","https://raw.githubusercontent.com/sayantan-025/portfolio/main/public/fonts/amiamie/ttf/Amiamie-Regular.ttf")
    target=OUT/"amiamie-subset.woff2"
    try:
        if not target.exists():
            urllib.request.urlretrieve(src, "/tmp/amiamie.ttf")
            subprocess.run(["pyftsubset","/tmp/amiamie.ttf","--output-file",str(target),"--flavor=woff2",
                "--unicodes=U+0000-00FF,U+2000-206F"],check=True,stdout=subprocess.DEVNULL)
        b64=base64.b64encode(target.read_bytes()).decode()
        return f"@font-face{{font-family:Amiamie;src:url(data:font/woff2;base64,{b64}) format('woff2');font-weight:400}}"
    except Exception as e:
        print(f"Font embedding skipped (install fonttools and check font URL): {e}")
        return " "

def svg_start(title, delay=0, height=220):
    css=font_css()
    motion="" if STATIC else f"""
      @keyframes rise {{ from {{opacity:0;transform:translateY(22px)}} to {{opacity:1;transform:translateY(0)}} }}
      .card-content {{opacity:0;animation:rise .8s cubic-bezier(.2,.7,.2,1) {delay}s forwards}}
      @media (prefers-reduced-motion:reduce) {{ *,*::before,*::after {{animation:none!important;transition:none!important;opacity:1!important;transform:none!important}} }}"""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">
    <style>{css} {motion} text{{font-family:Amiamie,Arial,sans-serif}} .muted{{fill:{BG};opacity:.68}}</style>
    <rect width="100%" height="100%" rx="28" fill="{BG}"/><rect x="2" y="2" width="956" height="{height-4}" rx="26" fill="none" stroke="{SAGE}" stroke-opacity=".45"/>
    <g class="card-content">'''
def end(): return "</g></svg>"

def write(name, content):
    OUT.mkdir(exist_ok=True); (OUT/name).write_text(content,encoding="utf-8")

def hero(d):
    portrait=d.get("portrait")
    photo=(f'<clipPath id="p"><circle cx="820" cy="112" r="66"/></clipPath><image x="754" y="46" width="132" height="132" preserveAspectRatio="xMidYMid slice" clip-path="url(#p)" xlink:href="{esc(portrait)}"/>' if portrait else
        f'<circle cx="820" cy="112" r="66" fill="{SAGE}"/><text x="820" y="128" font-size="52" text-anchor="middle" fill="{BG}">SB</text>')
    s=svg_start("Hero",0,230)
    s+=f'<text x="54" y="76" font-size="18" fill="{SAGE}" letter-spacing="4">HELLO, WORLD</text><text x="54" y="133" font-size="48" fill="{INK}">{esc(d.get("name","Sayantan Bera"))}</text><text x="56" y="174" font-size="19" fill="{INK}">{esc(d.get("tagline","Full Stack Web Developer"))}</text>{photo}'
    return s+end()

def link_card(link, idx):
    delay=.18+idx*.10
    motion="" if STATIC else f"""
      @keyframes rise {{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:translateY(0)}}}}
      .tile{{opacity:0;animation:rise .7s ease-out {delay}s forwards}}
      @media(prefers-reduced-motion:reduce){{*{{animation:none!important;opacity:1!important;transform:none!important}}}}"""
    css=font_css()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="300" height="132" viewBox="0 0 300 132">
    <style>{css}{motion}text{{font-family:Amiamie,Arial,sans-serif}}</style>
    <a xlink:href="{esc(link.get("url","#"))}"><g class="tile"><rect x="3" y="3" width="294" height="126" rx="22" fill="{SURFACE}"/><text x="150" y="76" text-anchor="middle" font-size="20" fill="{BG}">{esc(link.get("label","LINK"))}</text><text x="150" y="101" text-anchor="middle" font-size="11" fill="{GOLD}">OPEN ↗</text></g></a></svg>'''


def stats(d):
    c=d.get("contributions",{}); months=list(c.get("months",{}).items())[-12:]
    vals=[v for _,v in months] or [0]; maxv=max(vals+[1]); s=svg_start("Contribution activity",.36,310)
    s+=f'<text x="48" y="54" font-size="24" fill="{INK}">Contribution rhythm</text>'
    metrics=[("LONGEST STREAK",c.get("longest_streak",0)),("ACTIVE DAYS",c.get("active_days",0)),("BUSIEST DAY",c.get("busiest_day","—"))]
    for i,(label,value) in enumerate(metrics):
        x=50+i*300; s+=f'<text x="{x}" y="94" font-size="12" fill="{SAGE}">{label}</text><text x="{x}" y="126" font-size="25" fill="{INK}">{esc(value)}</text>'
    for i,(m,v) in enumerate(months):
        x=55+i*70; h=95*v/maxv
        s+=f'<rect x="{x}" y="{244-h:.1f}" width="38" height="{h:.1f}" rx="7" fill="{GOLD}"/><text x="{x+19}" y="267" text-anchor="middle" font-size="10" fill="{INK}">{m[5:]}</text>'
    return s+end()

def repo_card(repo, idx):
    s=svg_start("Featured repository",.54+idx*.16,174)
    s+=f'<text x="48" y="58" font-size="13" fill="{SAGE}" letter-spacing="3">FEATURED REPOSITORY</text><a xlink:href="{esc(repo.get("url","#"))}"><text x="48" y="101" font-size="30" fill="{INK}">{esc(repo.get("name","Project"))}</text></a><text x="48" y="132" font-size="16" fill="{INK}">{esc((repo.get("description") or "A project in progress")[:95])}</text><text x="850" y="100" font-size="17" text-anchor="end" fill="{GOLD}">★ {repo.get("stars",0)}</text>'
    return s+end()

def graph(d):
    days=d.get("contributions",{}).get("days",[])
    if not days: days=[{"date":(date.today()-timedelta(days=180-i)).isoformat(),"contributionCount":0} for i in range(181)]
    days=days[-371:]; s=svg_start("Contribution graph",.9,180)
    s+=f'<text x="48" y="42" font-size="20" fill="{INK}">A year in contributions</text>'
    cell=13; gap=4; startx=52; starty=60
    for i,d in enumerate(days):
        col=i//7; row=i%7; v=d.get("contributionCount",0)
        color=BG if v==0 else (SAGE if v<3 else GOLD if v<7 else SURFACE)
        s+=f'<rect x="{startx+col*(cell+gap)}" y="{starty+row*(cell+gap)}" width="{cell}" height="{cell}" rx="3" fill="{color}"><title>{esc(d.get("date"))}: {v} contributions</title></rect>'
    return s+end()

def main():
    d=refresh(load_data())
    DATA.parent.mkdir(exist_ok=True); DATA.write_text(json.dumps(d,indent=2),encoding="utf-8")
    write("hero.svg",hero(d)); write("activity.svg",stats(d)); write("contributions.svg",graph(d))
    for i,link in enumerate(d.get("links",[])[:3]): write(f"link-{i+1}.svg",link_card(link,i))
    for i,r in enumerate(d.get("featured_repos",[])): write(f"repo-{i+1}.svg",repo_card(r,i))
    print("Rendered SVG cards to cards/")
if __name__=="__main__": main()
