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

# --- SESSION STATE FOR HISTORY ---
if 'prompt_history' not in st.session_state:
    st.session_state.prompt_history = []

# --- CORE LOGIC ---
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        # Fetch 3 months to ensure MA20 has enough leading data
        hist = ticker.history(period="3mo")
        if hist.empty:
            return None, "Not found"
        
        # Calculate Technical Indicators
        # Moving Average 20
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        
        # We only want to focus on recent data for the technical indicators calculation
        # but we need the leading 20 days to see the line. 
        # Let's keep the last 40 trading days for the display
        display_hist = hist.tail(40)
        
        # Macro context (VIX and 10Y Yield)
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        tnx = yf.Ticker("^TNX").history(period="1d")['Close'].iloc[-1]
        
        # RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        info = ticker.info
        calendar = ticker.calendar
        
        # Smart Money: Insider Transactions
        insider = ticker.insider_transactions
        insider_summary = "No recent data"
        if insider is not None and not insider.empty:
            summary_list = []
            for _, row in insider.head(5).iterrows():
                summary_list.append(f"{row['Text']} ({row['Shares']} shares)")
            insider_summary = "\n".join(summary_list)

        data = {
            "symbol": symbol,
            "price": round(display_hist['Close'].iloc[-1], 2),
            "change": round(((display_hist['Close'].iloc[-1] - display_hist['Close'].iloc[-5]) / display_hist['Close'].iloc[-5]) * 100, 2),
            "rsi": round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else "N/A",
            "ma20_curr": round(display_hist['MA20'].iloc[-1], 2) if not pd.isna(display_hist['MA20'].iloc[-1]) else "N/A",
            "sector": info.get('sector', 'N/A'),
            "pe": info.get('forwardPE', 'N/A'),
            "target": info.get('targetMeanPrice', 'N/A'),
            "recommendation": info.get('recommendationKey', 'N/A').replace('_', ' ').capitalize(),
            "short_ratio": info.get('shortRatio', 'N/A'),
            "insider": insider_summary,
            "history": display_hist,
            "next_earnings": calendar.get('Earnings Date', 'N/A') if isinstance(calendar, dict) else "N/A",
            "vix": round(vix, 2),
            "tnx": round(tnx, 2)
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
    spy = yf.Ticker("SPY").history(period="1wk")
    spy_change = round(((spy['Close'].iloc[-1] - spy['Close'].iloc[0]) / spy['Close'].iloc[0]) * 100, 2)

    prompt = f"""
You are {persona_name}. Your objective is: {persona_instruction}

### 🌐 GLOBAL & MACRO CONTEXT ###
- VIX Index: {data['vix']} (Volatility check)
- 10Y Yield: {data['tnx']}% (Interest rate pressure)
- SPY Weekly: {spy_change}% (Market Benchmark)

### 📊 DATASET FOR {data['symbol']} ###

### 1. Smart Money & Sentiment:
- **Insider Activity (Recent)**: 
{data['insider']}
- **Short Ratio**: {data['short_ratio']} (Note: Above 5-10 indicates high bearish interest or squeeze potential)

### 2. Market & Sector Performance:
- Latest Close Price: ${data['price']}
- Weekly Change: {data['change']}%
- Sector: {data['sector']}
- 20-Day Moving Average (MA20): ${data['ma20_curr']}
- RSI (14-Day): {data['rsi']}

### 3. Fundamental & Institutional Metrics:
- Forward P/E Ratio: {data['pe']}
- Analyst Target Price (Mean): ${data['target']}
- Analyst Recommendation: {data['recommendation']}
- **NEXT EARNINGS DATE**: {data['next_earnings']}

### 4. Recent News Catalysts:
{news_text}

---
### ANALYSIS TASK ###
Based on your unique expertise as {persona_name}, please provide:
1. **Smart Money Check**: What does the Insider Activity and Short Ratio tell you about the current sentiment?
2. **Technical vs Fundamental**: Contrast the chart momentum (MA20/RSI) with its valuation and analyst targets.
3. **Macro/Event Synthesis**: Factor in VIX, 10Y Yield, and the upcoming Earnings Date.
4. Provide 3 specific Buy Reasons and 3 specific Risks.
5. Final Short-Term Outlook (5-10 days).
"""
    return prompt

# --- SIDEBAR ---
# (Keep sidebar mostly same but add history button)
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
selected_symbol = st.sidebar.selectbox("Choose a stock", watchlist)

persona_options = {
    "Warren Buffett": "Value/Moat focus",
    "Cathie Wood": "Innovation/Growth focus",
    "Michael Burry": "Contrarian/Bubble skepticism",
    "Ray Dalio": "Macro/Cycle focus",
    "Peter Lynch": "GARP/Stock-picking focus",
    "Jim Cramer": "Momentum/Sentiment focus"
}
selected_persona = st.sidebar.radio("Persona", list(persona_options.keys()))

if st.sidebar.button("🗑️ Clear History"):
    st.session_state.prompt_history = []
    st.rerun()

# --- MAIN ---
st.title("📈 Ollie - Expert Prompt Factory v4.0")

if selected_symbol:
    data, news = get_stock_data(selected_symbol)
    if data:
        # Metrics Display
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", f"${data['price']}", f"{data['change']}%")
        c2.metric("RSI", data['rsi'])
        c3.metric("Short Ratio", data['short_ratio'])
        c4.metric("MA20", f"${data['ma20_curr']}")

        # ADVANCED CHART
        fig = go.Figure()
        # Candlesticks
        fig.add_trace(go.Candlestick(x=data['history'].index,
                        open=data['history']['Open'], high=data['history']['High'],
                        low=data['history']['Low'], close=data['history']['Close'], 
                        name="Price"))
        # MA20 Line - Make it YELLOW and THICKER
        fig.add_trace(go.Scatter(x=data['history'].index, y=data['history']['MA20'], 
                        line=dict(color='#FFD700', width=3), name="MA20 (20-Day SMA)"))
        
        fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False,
                          margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, width='stretch')

        # PROMPT AREA
        final_prompt = generate_prompt(data, news, selected_persona, persona_options[selected_persona])
        
        st.subheader(f"🤖 {selected_persona}'s Expert Prompt")
        st.text_area("Copy this to your AI:", final_prompt, height=300)
        
        if st.button("📋 Copy & Save to History"):
            pyperclip.copy(final_prompt)
            # Save to history
            entry = {"time": datetime.now().strftime("%H:%M:%S"), "symbol": selected_symbol, "prompt": final_prompt}
            st.session_state.prompt_history.insert(0, entry)
            st.success("Copied and recorded!")

        # HISTORY SECTION
        if st.session_state.prompt_history:
            st.markdown("---")
            st.subheader("📜 Prompt History")
            for i, item in enumerate(st.session_state.prompt_history[:5]): # Show last 5
                with st.expander(f"{item['time']} - {item['symbol']} Analysis"):
                    st.text(item['prompt'])
    else:
        st.error(f"Could not fetch data for {selected_symbol}. Please check the ticker. Error: {news}")

st.markdown("---")
st.caption("Ollie v4.0 - Designed to make your AI analysis smarter.")
