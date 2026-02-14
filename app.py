import streamlit as st
import requests
import re
import pandas as pd
import plotly.express as px
from datetime import datetime

# ============ PAGE CONFIG ============
st.set_page_config(page_title="Tech Intelligence Pipeline", page_icon="🔍", layout="wide")

# ============ RSS SOURCES ============
DEFAULT_SOURCES = {
    "Azure Blog": "https://azure.microsoft.com/en-us/blog/feed/",
    "ZDNet Cloud": "https://www.zdnet.com/topic/cloud/rss.xml",
    "CloudComputing News": "https://www.cloudcomputing-news.net/feed/"
}

# ============ HELPER FUNCTIONS ============
def fetch_rss(url):
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "TechIntelBot/1.0"})
        r.raise_for_status()
        return r.text
    except Exception:
        return None

def parse_rss(xml, source):
    articles = []
    if not xml:
        return articles
    for m in re.finditer(r'<item>(.*?)</item>', xml, re.DOTALL):
        item = m.group(1)
        title = get_tag(item, 'title')
        link = get_tag(item, 'link')
        desc = get_tag(item, 'description')
        date = get_tag(item, 'pubDate')
        clean = re.sub(r'<[^>]+>', '', desc).strip()
        if len(clean) > 300:
            clean = clean[:300] + "..."
        articles.append({"title": title, "description": clean, "link": link, "pub_date": date, "source": source})
    return articles

def get_tag(xml, tag):
    m = re.search(r'<' + tag + r'>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</' + tag + r'>', xml, re.DOTALL)
    return m.group(1).strip() if m else ""

def classify_category(title, desc):
    t = (title + " " + desc).lower()
    if any(w in t for w in ['security','cyber','lockdown','threat','privacy','governance','compliance']):
        return 'Security'
    if any(w in t for w in ['ai','machine learning','chatbot','copilot','gpt','inference','llm','neural']):
        return 'AI/ML'
    if any(w in t for w in ['cloud','azure','aws','storage','datacenter','data center','saas','kubernetes']):
        return 'Cloud Computing'
    if any(w in t for w in ['devops','postgresql','database','container','docker','deploy']):
        return 'DevOps'
    if any(w in t for w in ['enterprise','partner','marketplace','business','strategy']):
        return 'Enterprise'
    if any(w in t for w in ['innovation','xr','vr','ar','robot','quantum','glasses','wearable']):
        return 'Innovation'
    return 'Other'

def classify_sentiment(title, desc):
    t = (title + " " + desc).lower()
    pos = ['best','great','excellent','supercharged','breakthrough','proud','leader','upgrade','boost',
           'improve','advance','exciting','honored','strong','worthy','wonders','exhilarating','premium',
           'momentum','future','new']
    neg = ['slow','problem','blame','attack','threat','risk','issue','missing','old','dropped','hard',
           'fail','decline']
    pc = sum(1 for w in pos if w in t)
    nc = sum(1 for w in neg if w in t)
    if pc > nc + 1: return 'positive', round(min(0.3 + pc * 0.12, 0.9), 2)
    if nc > pc + 1: return 'negative', round(max(-0.3 - nc * 0.12, -0.9), 2)
    if pc > nc: return 'positive', round(0.2 + pc * 0.08, 2)
    if nc > pc: return 'negative', round(-0.2 - nc * 0.08, 2)
    return 'neutral', 0.05

def classify_trend(title, desc):
    t = (title + " " + desc).lower()
    if any(w in t for w in ['launch','introduce','announce','first','new']): return 'emerging'
    if any(w in t for w in ['grow','rise','boost','expand','future']): return 'growing'
    if any(w in t for w in ['decline','drop','slow','end']): return 'declining'
    return 'stable'

def extract_topics(title, desc):
    t = (title + " " + desc).lower()
    topics = []
    kw = {'AI':['ai','machine learning','chatbot','gpt','copilot','inference'],
          'Cloud':['cloud','azure','aws','gcp'],'Security':['security','cyber','privacy','lockdown'],
          'Storage':['storage','datacenter','netapp'],'Microsoft':['microsoft','azure','windows'],
          'Database':['postgresql','sql','database'],'Hardware':['laptop','phone','chip','gpu','nvidia','ssd'],
          'Mobile':['iphone','android','app'],'Enterprise':['enterprise','business','marketplace'],
          'Healthcare':['healthcare','medicine','life sciences']}
    for topic, words in kw.items():
        if any(w in t for w in words):
            topics.append(topic)
    return topics[:4]

def gen_tweet(title, cat):
    tags = {'AI/ML':'#AI #MachineLearning #Tech','Cloud Computing':'#Cloud #Azure #CloudComputing',
            'Security':'#CyberSecurity #InfoSec #Tech','DevOps':'#DevOps #CloudNative #Tech',
            'Enterprise':'#Enterprise #Digital #Tech','Innovation':'#Innovation #FutureTech',
            'Other':'#Tech #Digital #Innovation'}
    short = title[:210] + "..." if len(title) > 210 else title
    return f"📰 {short} {tags.get(cat, '#Tech')}"

def gen_linkedin(title, desc, cat):
    short = desc[:150] + "..." if len(desc) > 150 else desc
    tag = cat.replace('/','').replace(' ','')
    return f"🔍 Key development in {cat}: {title}. {short} What are your thoughts? #{tag} #TechTrends"

def analyze(article):
    t, d = article['title'], article['description']
    cat = classify_category(t, d)
    sent, score = classify_sentiment(t, d)
    trend = classify_trend(t, d)
    topics = extract_topics(t, d)
    impacts = {'AI/ML':'AI capabilities reshape enterprise workflows, requiring integration strategy evaluation.',
               'Cloud Computing':'Cloud developments impact operational costs and transformation timelines.',
               'Security':'Security developments affect risk management and compliance requirements.',
               'DevOps':'DevOps improvements accelerate release cycles and system reliability.',
               'Enterprise':'Enterprise tech shifts influence procurement and IT strategy.',
               'Innovation':'Emerging tech presents competitive advantages and disruption risks.',
               'Other':'Technology trends evolve the digital landscape with new opportunities.'}
    recs = {'AI/ML':'Evaluate this AI development for workflow integration.',
            'Cloud Computing':'Review cloud architecture to leverage latest services.',
            'Security':'Assess security posture for this evolving landscape.',
            'DevOps':'Consider these tools to streamline your pipeline.',
            'Enterprise':'Align technology roadmap with these trends.',
            'Innovation':'Monitor this technology for early-adoption advantages.',
            'Other':'Evaluate this trend for potential business impact.'}
    return {**article, 'category':cat, 'sentiment':sent, 'sentiment_score':score,
            'trend_signal':trend, 'key_topics':topics,
            'business_impact':impacts.get(cat,impacts['Other']),
            'recommendation':recs.get(cat,recs['Other']),
            'twitter_post':gen_tweet(t,cat), 'linkedin_post':gen_linkedin(t,d,cat)}

# ============ SIDEBAR ============
with st.sidebar:
    st.title("🔍 Tech Intelligence")
    st.markdown("**AI-Powered News Analysis Pipeline**")
    st.divider()

    st.subheader("📡 Data Sources")
    selected = st.multiselect("Select RSS feeds to analyze:", options=list(DEFAULT_SOURCES.keys()),
                               default=list(DEFAULT_SOURCES.keys()),
                               help="Choose which tech news sources to scrape and analyze")

    custom_url = st.text_input("Add a custom RSS feed URL (optional):",
                                placeholder="https://example.com/feed/rss.xml",
                                help="Enter any valid RSS feed URL")
    st.divider()

    st.subheader("⚙️ Settings")
    max_articles = st.slider("Max articles to analyze:", min_value=5, max_value=50, value=30, step=5)

    run_btn = st.button("🚀 Run Analysis", type="primary", use_container_width=True)

    st.divider()
    st.subheader("ℹ️ About")
    st.markdown("""
    **Tech Intelligence Pipeline** analyzes tech news articles using AI-powered
    sentiment analysis, category classification, trend detection, and auto-generates
    social media posts.

    **Who it's for:** Tech professionals, marketing managers, content strategists

    **Tech Stack:** Python, Streamlit, NLP, RSS Parsing, Plotly

    **Built by:** Pratiksha Mohod
    [LinkedIn](https://www.linkedin.com/in/pratiksha-mohod/) | [GitHub](https://github.com/)

    *Assignment 5 — Northeastern University*
    """)

# ============ MAIN PAGE ============
st.title("🔍 Tech Intelligence Pipeline")
st.caption("AI-Powered Tech News Analysis, Sentiment Scoring & Social Content Generation")

if not run_btn:
    st.info("👈 Select your data sources in the sidebar and click **Run Analysis** to start.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Sources Available", "3+")
    c2.metric("Analysis Points", "8 per article")
    c3.metric("Cost per Run", "~$0.00")
    st.markdown("---")
    st.subheader("What this tool does:")
    st.markdown("""
    1. **Scrapes** tech news from RSS feeds (Azure Blog, ZDNet, CloudComputing News)
    2. **Analyzes** sentiment (positive / negative / neutral with numeric scores)
    3. **Classifies** into categories (AI/ML, Cloud, Security, DevOps, Enterprise, Innovation)
    4. **Detects** trend signals (emerging, growing, stable, declining)
    5. **Extracts** key topics from each article
    6. **Generates** ready-to-post Twitter and LinkedIn content
    7. **Produces** business impact assessments and recommendations
    8. **Visualizes** everything in interactive charts and tables
    """)
    st.stop()

# ============ RUN ANALYSIS ============
if not selected and not custom_url:
    st.error("⚠️ Please select at least one source or enter a custom RSS URL.")
    st.stop()

sources = {}
for name in selected:
    sources[name] = DEFAULT_SOURCES[name]
if custom_url:
    if not custom_url.startswith("http"):
        st.error("⚠️ Custom URL must start with http:// or https://")
        st.stop()
    sources["Custom Feed"] = custom_url

all_articles = []
progress = st.progress(0, text="Fetching RSS feeds...")

for i, (name, url) in enumerate(sources.items()):
    progress.progress((i + 1) / (len(sources) + 1), text=f"Fetching {name}...")
    xml = fetch_rss(url)
    if xml:
        arts = parse_rss(xml, name)
        all_articles.extend(arts)
        st.toast(f"✅ {name}: {len(arts)} articles")
    else:
        st.warning(f"⚠️ Could not fetch {name}")

if not all_articles:
    st.error("❌ No articles fetched. Check your sources and try again.")
    st.stop()

all_articles = all_articles[:max_articles]
progress.progress(0.8, text="Running AI analysis...")
results = [analyze(a) for a in all_articles]
progress.progress(1.0, text="✅ Analysis complete!")

st.success(f"✅ Analyzed **{len(results)}** articles from **{len(sources)}** sources!")

# ============ METRICS ============
st.subheader("📈 Key Metrics")
sents = [r['sentiment'] for r in results]
pos = sents.count('positive')
neg = sents.count('negative')
neu = sents.count('neutral')
avg = round(sum(r['sentiment_score'] for r in results) / len(results), 2)
cats = {}
for r in results:
    cats[r['category']] = cats.get(r['category'], 0) + 1

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Articles", len(results))
c2.metric("Positive 🟢", pos)
c3.metric("Negative 🔴", neg)
c4.metric("Neutral 🟡", neu)
c5.metric("Avg Score", avg)
c6.metric("Categories", len(cats))

# ============ CHARTS ============
st.subheader("📊 Analysis Dashboard")
ch1, ch2 = st.columns(2)

with ch1:
    fig1 = px.pie(names=['Positive','Negative','Neutral'], values=[pos, neg, neu],
                  color_discrete_sequence=['#34d399','#f87171','#fbbf24'], title="Sentiment Distribution")
    fig1.update_layout(height=350)
    st.plotly_chart(fig1, use_container_width=True)

with ch2:
    cat_df = pd.DataFrame(list(cats.items()), columns=['Category','Count']).sort_values('Count', ascending=True)
    fig2 = px.bar(cat_df, x='Count', y='Category', orientation='h', color='Category', title="Category Breakdown")
    fig2.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

ch3, ch4 = st.columns(2)

with ch3:
    trends = {}
    for r in results:
        trends[r['trend_signal']] = trends.get(r['trend_signal'], 0) + 1
    tr_df = pd.DataFrame(list(trends.items()), columns=['Trend','Count'])
    fig3 = px.bar(tr_df, x='Trend', y='Count', color='Trend',
                  color_discrete_map={'emerging':'#f472b6','growing':'#34d399','stable':'#60a5fa','declining':'#f87171'},
                  title="Trend Signals")
    fig3.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

with ch4:
    src = {}
    for r in results:
        src[r['source']] = src.get(r['source'], 0) + 1
    src_df = pd.DataFrame(list(src.items()), columns=['Source','Count'])
    fig4 = px.pie(src_df, names='Source', values='Count', title="Articles by Source")
    fig4.update_layout(height=350)
    st.plotly_chart(fig4, use_container_width=True)

# ============ TOPICS ============
st.subheader("🔥 Trending Topics")
all_topics = {}
for r in results:
    for t in r['key_topics']:
        all_topics[t] = all_topics.get(t, 0) + 1
if all_topics:
    sorted_t = sorted(all_topics.items(), key=lambda x: x[1], reverse=True)
    st.markdown(" ".join([f"`{t} ({c})`" for t, c in sorted_t[:12]]))

# ============ ARTICLES ============
st.subheader("📰 Detailed Article Analysis")
for i, r in enumerate(results):
    icon = "🟢" if r['sentiment'] == 'positive' else "🔴" if r['sentiment'] == 'negative' else "🟡"
    with st.expander(f"{icon} {i+1}. {r['title']}", expanded=(i < 2)):
        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.markdown(f"**Sentiment:** {r['sentiment'].upper()} ({r['sentiment_score']})")
        mc2.markdown(f"**Category:** {r['category']}")
        mc3.markdown(f"**Trend:** {r['trend_signal']}")
        mc4.markdown(f"**Source:** {r['source']}")
        st.markdown(f"**Summary:** {r['description']}")
        st.markdown(f"**💡 Impact:** {r['business_impact']}")
        st.markdown(f"**🎯 Recommendation:** {r['recommendation']}")
        if r['key_topics']:
            st.markdown(f"**Topics:** {', '.join(r['key_topics'])}")
        if r['link']:
            st.markdown(f"[🔗 Read full article]({r['link']})")

# ============ SOCIAL POSTS ============
st.subheader("📱 Auto-Generated Social Media Posts")
tab_tw, tab_li = st.tabs(["🐦 Twitter / X", "💼 LinkedIn"])

with tab_tw:
    for i, r in enumerate(results[:15]):
        st.markdown(f"**{i+1}. {r['title'][:60]}...**")
        st.code(r['twitter_post'], language=None)

with tab_li:
    for i, r in enumerate(results[:15]):
        st.markdown(f"**{i+1}. {r['title'][:60]}...**")
        st.info(r['linkedin_post'])

# ============ EXPORT ============
st.subheader("📥 Export Results")
ex1, ex2 = st.columns(2)

with ex1:
    rows = [{'Title':r['title'],'Source':r['source'],'Sentiment':r['sentiment'],'Score':r['sentiment_score'],
             'Category':r['category'],'Trend':r['trend_signal'],'Topics':', '.join(r['key_topics']),
             'Summary':r['description'],'Twitter':r['twitter_post'],'LinkedIn':r['linkedin_post']} for r in results]
    csv = pd.DataFrame(rows).to_csv(index=False)
    st.download_button("📊 Download CSV Report", data=csv,
                       file_name=f"tech_intel_{datetime.now().strftime('%Y%m%d')}.csv",
                       mime="text/csv", use_container_width=True)

with ex2:
    txt = f"SOCIAL MEDIA POSTS\nGenerated: {datetime.now().isoformat()}\n\n"
    for i, r in enumerate(results):
        txt += f"--- Post {i+1} ---\nArticle: {r['title']}\nTwitter: {r['twitter_post']}\nLinkedIn: {r['linkedin_post']}\n\n"
    st.download_button("📱 Download Social Posts", data=txt,
                       file_name=f"social_{datetime.now().strftime('%Y%m%d')}.txt",
                       mime="text/plain", use_container_width=True)

# ============ FOOTER ============
st.markdown("---")
st.markdown("""
<div style='text-align:center;color:gray;'>
<p><b>Tech Intelligence Pipeline</b> — AI-Powered by Python + NLP</p>
<p>Sources: Azure Blog | ZDNet Cloud | CloudComputing News</p>
<p>Built by Pratiksha Mohod | Northeastern University</p>
</div>
""", unsafe_allow_html=True)
