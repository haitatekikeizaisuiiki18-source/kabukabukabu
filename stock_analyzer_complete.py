import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime
import json
from pathlib import Path

st.set_page_config(page_title="株最強分析くん", page_icon="📊", layout="wide")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "analysis_history.json"
RANKING_FILE = DATA_DIR / "monthly_ranking.json"

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(code, name, score, details):
    history = load_history()
    history.append({
        'stock_code': code,
        'company_name': name,
        'score': score,
        'score_details': details,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'month': datetime.now().strftime('%Y-%m')
    })
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    update_ranking()

def load_ranking():
    if RANKING_FILE.exists():
        with open(RANKING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def update_ranking():
    history = load_history()
    month = datetime.now().strftime('%Y-%m')
    ranking = load_ranking()
    entries = [h for h in history if h.get('month') == month]
    ranking[month] = sorted(entries, key=lambda x: x['score'], reverse=True)
    with open(RANKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(ranking, f, ensure_ascii=False, indent=2)

def get_stock_data(code):
    try:
        ticker = yf.Ticker(f"{code}.T")
        hist = ticker.history(period="5y")
        info = ticker.info
        name = info.get('longName', f'銘柄{code}')
        return {'name': name, 'history': hist, 'info': info}
    except:
        return None

def calc_score(data):
    if not data:
        return 0, {}
    
    details = {}
    hist = data['history']
    info = data['info']
    
    try:
        if len(hist) > 365:
            avg1y = hist.tail(252)['Close'].mean()
            avg5y = hist.tail(1260)['Close'].mean()
            details['revenue_trend'] = 15 if avg1y > avg5y * 1.05 else 5
        else:
            details['revenue_trend'] = 5
    except:
        details['revenue_trend'] = 0
    
    try:
        eps = info.get('trailingEps', 0)
        details['eps_trend'] = 15 if eps and eps > 0 else 5
    except:
        details['eps_trend'] = 0
    
    try:
        if len(hist) > 730:
            avg2y = hist.tail(504)['Close'].mean()
            avg5y = hist.tail(1260)['Close'].mean()
            details['asset_trend'] = 10 if avg2y > avg5y else 3
        else:
            details['asset_trend'] = 3
    except:
        details['asset_trend'] = 0
    
    try:
        cur = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-252] if len(hist) > 252 else hist['Close'].iloc[0]
        details['operating_cf'] = 10 if cur > prev else 3
    except:
        details['operating_cf'] = 0
    
    try:
        cf = info.get('operatingCashflow', 0)
        details['cash_accumulation'] = 10 if cf and cf > 0 else 3
    except:
        details['cash_accumulation'] = 0
    
    try:
        roe = info.get('returnOnEquity', 0)
        if roe and roe > 0.07:
            details['roe'] = 10
        elif roe and roe > 0.05:
            details['roe'] = 6
        else:
            details['roe'] = 0
    except:
        details['roe'] = 0
    
    try:
        pb = info.get('priceToBook', 0)
        if pb and pb < 1.5:
            details['equity_ratio'] = 10
        elif pb and pb < 2.5:
            details['equity_ratio'] = 5
        else:
            details['equity_ratio'] = 0
    except:
        details['equity_ratio'] = 0
    
    try:
        div = info.get('dividendYield', 0)
        if div and div > 0.01:
            details['dividend_trend'] = 10
        elif div and div > 0:
            details['dividend_trend'] = 5
        else:
            details['dividend_trend'] = 0
    except:
        details['dividend_trend'] = 0
    
    try:
        payout = info.get('payoutRatio', 0)
        if payout and payout < 0.4:
            details['payout_ratio'] = 10
        elif payout and payout < 0.6:
            details['payout_ratio'] = 5
        else:
            details['payout_ratio'] = 0
    except:
        details['payout_ratio'] = 0
    
    return sum(details.values()), details

def gauge_chart(score):
    color = '#ff4444' if score < 40 else '#ffaa00' if score < 60 else '#00cc66'
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={'text': "総合スコア"},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 40], 'color': '#ffcccc'},
                {'range': [40, 60], 'color': '#fff5cc'},
                {'range': [60, 100], 'color': '#ccffcc'}
            ]
        }
    ))
    fig.update_layout(height=400)
    return fig

def pie_chart(details):
    labels = ['経常収益', 'EPS', '総資産', '営業CF', '現金等', 'ROE', '自己資本', '配当', '配当性向']
    keys = ['revenue_trend', 'eps_trend', 'asset_trend', 'operating_cf', 'cash_accumulation', 'roe', 'equity_ratio', 'dividend_trend', 'payout_ratio']
    values = [details.get(k, 0) for k in keys]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])
    fig.update_layout(title="スコア内訳", height=500)
    return fig

def candle_chart(hist, label):
    if hist is None or hist.empty:
        return None
    fig = go.Figure(data=[go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'])])
    if len(hist) >= 25:
        ma = hist['Close'].rolling(25).mean()
        fig.add_trace(go.Scatter(x=hist.index, y=ma, mode='lines', name='25日MA'))
    fig.update_layout(title=f'株価推移({label})', height=500, xaxis_rangeslider_visible=False)
    return fig

st.title("📊 株最強分析くん")
st.info("9項目で100点満点で評価します")

tab1, tab2, tab3, tab4 = st.tabs(["分析", "履歴", "ランキング", "比較"])

with tab1:
    col1, col2 = st.columns([2, 1])
    with col1:
        code = st.text_input("銘柄コード", placeholder="7203")
    with col2:
        frames = {"5分": 1, "15分": 1, "1時間": 5, "1日": 22, "1週間": 52, "1ヶ月": 22, "1年": 252, "5年": 1260, "MAX": 10000}
        frame = st.selectbox("期間", list(frames.keys()), index=7)
    
    if st.button("分析", type="primary", use_container_width=True) and code:
        with st.spinner('取得中...'):
            data = get_stock_data(code)
            if data:
                score, details = calc_score(data)
                save_history(code, data['name'], score, details)
                
                st.success(f"✅ {data['name']}")
                
                c1, c2 = st.columns([1, 1])
                with c1:
                    st.plotly_chart(gauge_chart(score), use_container_width=True)
                with c2:
                    if score >= 80:
                        st.success("🌟 優良企業")
                    elif score >= 60:
                        st.info("👍 良好")
                    elif score >= 40:
                        st.warning("改善余地")
                    else:
                        st.error("要注意")
                
                st.plotly_chart(pie_chart(details), use_container_width=True)
                
                st.subheader("詳細")
                items = [
                    ('revenue_trend', '経常収益', 15),
                    ('eps_trend', 'EPS', 15),
                    ('asset_trend', '総資産', 10),
                    ('operating_cf', '営業CF', 10),
                    ('cash_accumulation', '現金等', 10),
                    ('roe', 'ROE', 10),
                    ('equity_ratio', '自己資本', 10),
                    ('dividend_trend', '配当', 10),
                    ('payout_ratio', '配当性向', 10)
                ]
                
                cols = st.columns(3)
                for i, (key, name, max_pts) in enumerate(items):
                    pts = details.get(key, 0)
                    with cols[i % 3]:
                        st.write(f"{name}: {pts}/{max_pts}点")
                
                if data['history'] is not None and not data['history'].empty:
                    st.subheader("チャート")
                    hist = data['history'].tail(frames[frame])
                    chart = candle_chart(hist, frame)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("現在値", f"{hist['Close'].iloc[-1]:.0f}円")
                    with c2:
                        st.metric("変化", f"{hist['Close'].iloc[-1] - hist['Close'].iloc[0]:+.0f}円")
                    with c3:
                        st.metric("高値", f"{hist['High'].max():.0f}円")
                    with c4:
                        st.metric("安値", f"{hist['Low'].min():.0f}円")

with tab2:
    st.subheader("履歴")
    hist = load_history()
    if hist:
        df = pd.DataFrame([{'銘柄': h['stock_code'], '企業': h['company_name'], 'スコア': h['score'], '日時': h['date']} for h in sorted(hist, key=lambda x: x['date'], reverse=True)])
        st.dataframe(df, use_container_width=True)
        
        st.subheader("推移")
        companies = {}
        for h in hist:
            key = (h['stock_code'], h['company_name'])
            if key not in companies:
                companies[key] = []
            companies[key].append(h)
        
        for (code, name), entries in sorted(companies.items()):
            with st.expander(f"{name} ({code})"):
                scores = [e['score'] for e in sorted(entries, key=lambda x: x['date'])]
                dates = [e['date'] for e in sorted(entries, key=lambda x: x['date'])]
                fig = go.Figure(data=[go.Scatter(x=dates, y=scores, mode='lines+markers')])
                st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("ランキング")
    ranking = load_ranking()
    if ranking:
        month = st.selectbox("月", sorted(ranking.keys(), reverse=True))
        data = ranking[month][:20]
        df = pd.DataFrame([{'順位': i+1, '銘柄': e['stock_code'], '企業': e['company_name'], 'スコア': e['score']} for i, e in enumerate(data)])
        st.dataframe(df, use_container_width=True)
        
        fig = go.Figure(data=[go.Bar(x=[e['company_name'] for e in data[:10]], y=[e['score'] for e in data[:10]], marker=dict(color=[e['score'] for e in data[:10]], colorscale='RdYlGn'))])
        fig.update_layout(title=f"{month} TOP10", height=400)
        st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("比較")
    hist = load_history()
    if hist:
        opts = list(set([f"{h['company_name']} ({h['stock_code']})" for h in hist]))
        selected = st.multiselect("銘柄選択", opts, max_selections=5)
        
        if selected:
            comp = []
            for sel in selected:
                code = sel.split('(')[1].rstrip(')')
                latest = next((h for h in reversed(hist) if h['stock_code'] == code), None)
                if latest:
                    comp.append(latest)
            
            if comp:
                df = pd.DataFrame([{'企業': d['company_name'], 'スコア': d['score']} for d in comp])
                st.dataframe(df, use_container_width=True)
                
                fig = go.Figure(data=[go.Bar(x=[d['company_name'] for d in comp], y=[d['score'] for d in comp], marker=dict(color=[d['score'] for d in comp], colorscale='RdYlGn'))])
                st.plotly_chart(fig, use_container_width=True)