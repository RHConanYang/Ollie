import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import pyperclip

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Ollie - Expert Prompt Factory",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CSS FOR PREMIUM LOOK ---
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #262730;
        color: white;
        border: 1px solid #4a4a4a;
    }
    .stButton>button:hover {
        border-color: #00ff88;
        color: #00ff88;
    }
    .metric-card {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2d314d;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CORE LOGIC (Adapted for UI) ---
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1mo")
        if hist.empty:
            return None, "Not found"
        
        # Technicals
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        info = ticker.info
        calendar = ticker.calendar
        
        data = {
            "symbol": symbol,
            "price": round(hist['Close'].iloc[-1], 2),
            "change": round(((hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100, 2),
            "rsi": round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else "N/A",
            "ma20": round(hist['Close'].rolling(window=20).mean().iloc[-1], 2),
            "sector": info.get('sector', 'N/A'),
            "pe": info.get('forwardPE', 'N/A'),
            "target": info.get('targetMeanPrice', 'N/A'),
            "recommendation": info.get('recommendationKey', 'N/A').replace('_', ' ').capitalize(),
            "history": hist,
            "next_earnings": calendar.get('Earnings Date', 'N/A') if isinstance(calendar, dict) else "N/A"
        }
        
        # News
        news = ticker.news[:5]
        formatted_news = []
        for n in news:
            content = n.get('content', {})
            formatted_news.append({
                "title": content.get('title', 'N/A'),
                "publisher": content.get('finance', {}).get('owner', {}).get('displayName', 'Yahoo Finance')
            })
            
        return data, formatted_news
    except Exception as e:
        return None, str(e)

def generate_prompt(data, news, persona_name, persona_instruction):
    news_text = "\n".join([f"- {n['title']} (Source: {n['publisher']})" for n in news])
    
    # Calculate SPY context for the prompt
    spy = yf.Ticker("SPY").history(period="1wk")
    spy_change = round(((spy['Close'].iloc[-1] - spy['Close'].iloc[0]) / spy['Close'].iloc[0]) * 100, 2)

    prompt = f"""
You are a {persona_name}. Your goal is: {persona_instruction}

### 📊 MASTER DATASET FOR {data['symbol']} ###

### 1. Market & Sector Performance:
- Latest Close Price: ${data['price']}
- Weekly Change: {data['change']}%
- **VS S&P 500 (SPY) Change**: {spy_change}%
- Sector: {data['sector']}
- 20-Day Moving Average (MA20): ${data['ma20']}
- RSI (14-Day): {data['rsi']}

### 2. Fundamental & Institutional Metrics:
- Forward P/E Ratio: {data['pe']}
- Analyst Target Price (Mean): ${data['target']}
- Analyst Recommendation: {data['recommendation']}
- **NEXT EARNINGS DATE**: {data['next_earnings']}

### 3. Recent News Catalysts:
{news_text}

---
### ANALYSIS TASK ###
Based on your expertise as a {persona_name}, please provide a professional analysis.
1. **Relative Strength**: Is the stock outperforming or underperforming the S&P 500? What does this tell us?
2. **Event Risk**: How should the upcoming Earnings Date ({data['next_earnings']}) affect a trader's decision?
3. **Synthesis**: Contrast Technicials (RSI/MA) with Fundamentals (P/E).
4. Provide 3 high-conviction "Buy Reasons" and 3 "Key Risks".
5. Give a final outlook for the next 5-10 trading days.
"""
    return prompt

# --- SIDEBAR: Watchlist Management ---
st.sidebar.title("🔍 Ollie Watchlist")
new_ticker = st.sidebar.text_input("Add Ticker", "").upper()
if st.sidebar.button("Add to List"):
    if new_ticker:
        with open("watchlist.txt", "a") as f:
            f.write(f"\n{new_ticker}")
        st.rerun()

try:
    with open("watchlist.txt", "r") as f:
        watchlist = list(set([line.strip().upper() for line in f if line.strip()]))
except:
    watchlist = ["AAPL", "TSLA", "NVDA"]

st.sidebar.markdown("---")
st.sidebar.subheader("Active Watchlist")
selected_symbol = st.sidebar.selectbox("Choose a stock to analyze", watchlist)

persona_options = {
    "Standard": "Provide a balanced view covering both technical, fundamental, and upcoming event risks.",
    "Value Specialist": "Focus heavily on Financial Health, P/E, Cashflow, and how the stock compares to the broader market valuation.",
    "Technical Specialist": "Focus heavily on Momentum, Volatility, and Price Action relative to the S&P 500 (SPY)."
}
selected_persona = st.sidebar.radio("Analyst Persona", list(persona_options.keys()))

# --- MAIN INTERFACE ---
st.title("📈 Ollie - Expert Prompt Factory")
st.markdown("---")

if selected_symbol:
    data, news = get_stock_data(selected_symbol)
    
    if data:
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            st.metric("Price", f"${data['price']}", f"{data['change']}%")
        with col2:
            st.metric("RSI (14)", data['rsi'])
        with col3:
            st.metric("Recommendation", data['recommendation'])

        # Chart
        fig = go.Figure(data=[go.Candlestick(x=data['history'].index,
                        open=data['history']['Open'],
                        high=data['history']['High'],
                        low=data['history']['Low'],
                        close=data['history']['Close'])])
        fig.update_layout(title=f"{selected_symbol} Technical View", template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Prompt Generation
        st.subheader("🤖 Generated Expert Prompt")
        final_prompt = generate_prompt(data, news, selected_persona, persona_options[selected_persona])
        
        st.text_area("Prompt Content", final_prompt, height=300)
        
        if st.button("📋 Copy to Clipboard"):
            pyperclip.copy(final_prompt)
            st.success(f"Prompt for {selected_symbol} copied!")
            
    else:
        st.error(f"Could not fetch data for {selected_symbol}. Please check the ticker.")

st.markdown("---")
st.caption("Ollie v3.0 - Designed to make your AI analysis smarter.")
