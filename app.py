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

# --- UTILS ---
SECTOR_ETF_MAP = {
    "Technology": "XLK",
    "Consumer Cyclical": "XLY",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Basic Materials": "XLB"
}

def get_sector_performance(sector_name):
    etf_symbol = SECTOR_ETF_MAP.get(sector_name)
    if not etf_symbol:
        return 0.0, "N/A"
    try:
        etf = yf.Ticker(etf_symbol).history(period="1wk")
        change = ((etf['Close'].iloc[-1] - etf['Close'].iloc[0]) / etf['Close'].iloc[0]) * 100
        return round(change, 2), etf_symbol
    except:
        return 0.0, etf_symbol

# --- CORE LOGIC ---
def get_stock_data(symbol):
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="3mo")
        if hist.empty:
            return None, "Not found"
        
        # Indicators
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        
        # MACD Calculation
        exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
        exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
        hist['MACD'] = exp1 - exp2
        hist['Signal'] = hist['MACD'].ewm(span=9, adjust=False).mean()
        
        display_hist = hist.tail(40)
        
        # Macro context
        vix = yf.Ticker("^VIX").history(period="1d")['Close'].iloc[-1]
        tnx = yf.Ticker("^TNX").history(period="1d")['Close'].iloc[-1]
        
        # RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        info = ticker.info
        sector = info.get('sector', 'N/A')
        sector_change, sector_etf = get_sector_performance(sector)
        
        # Earnings History
        earnings_hist = ticker.earnings_dates
        earning_summary = "N/A"
        if earnings_hist is not None and not earnings_hist.empty:
            valid_surprises = earnings_hist.dropna(subset=['Surprise(%)']).head(3)
            if not valid_surprises.empty:
                earning_summary = "\n".join([f"- Date: {idx.date()}, Surprise: {row['Surprise(%)']:.2f}%" for idx, row in valid_surprises.iterrows()])

        # Technical Score
        score = 0
        latest_rsi = rsi.iloc[-1]
        if latest_rsi < 30: score += 2 # Oversold
        if latest_rsi > 70: score -= 2 # Overbought
        if display_hist['Close'].iloc[-1] > display_hist['MA20'].iloc[-1]: score += 1 # Above MA20
        if display_hist['MACD'].iloc[-1] > display_hist['Signal'].iloc[-1]: score += 1 # MACD Bullish
        
        data = {
            "symbol": symbol,
            "name": info.get('longName', symbol),
            "price": round(display_hist['Close'].iloc[-1], 2),
            "change": round(((display_hist['Close'].iloc[-1] - display_hist['Close'].iloc[-5]) / display_hist['Close'].iloc[-5]) * 100, 2),
            "rsi": round(latest_rsi, 2) if not pd.isna(latest_rsi) else 50.0,
            "ma20_curr": round(display_hist['MA20'].iloc[-1], 2) if not pd.isna(display_hist['MA20'].iloc[-1]) else 0.0,
            "macd": round(display_hist['MACD'].iloc[-1], 3),
            "sector": sector,
            "sector_change": sector_change,
            "sector_etf": sector_etf,
            "pe": info.get('forwardPE', 'N/A'),
            "target": info.get('targetMeanPrice', 'N/A'),
            "recommendation": info.get('recommendationKey', 'N/A').replace('_', ' ').capitalize(),
            "short_ratio": info.get('shortRatio', 'N/A'),
            "insider": "\n".join([f"{r['Text']} ({r['Shares']} shares)" for _, r in ticker.insider_transactions.head(3).iterrows()]) if ticker.insider_transactions is not None else "No data",
            "earnings_hist": earning_summary,
            "history": display_hist,
            "next_earnings": ticker.calendar.get('Earnings Date', 'N/A') if isinstance(ticker.calendar, dict) else "N/A",
            "vix": round(vix, 2),
            "tnx": round(tnx, 2),
            "tech_score": score
        }
        return data, ticker.news[:5]
    except Exception as e:
        return None, str(e)

def generate_prompt(data, news_list, persona_name, persona_instruction):
    news_text = ""
    for n in news_list:
        content = n.get('content', {})
        news_text += f"- {content.get('title')} (Publisher: {content.get('finance', {}).get('owner', {}).get('displayName', 'Unknown')})\n"
    
    spy_hist = yf.Ticker("SPY").history(period="1wk")
    spy_change = round(((spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0]) - 1) * 100, 2)

    prompt = f"""
You are {persona_name}. Your objective is: {persona_instruction}

### 🌐 GLOBAL MACRO & SENTIMENT ###
- VIX Index: {data['vix']} | 10Y Yield: {data['tnx']}% | SPY Weekly: {spy_change}%
- **Technical Signal Score**: {data['tech_score']}/4 (Higher is more bullish)

### 📊 DATASET FOR {data['symbol']} ({data['name']}) ###

### 1. Macro & Earnings Context:
- Sector Performance ({data['sector_etf']}): {data['sector_change']}%
- **PAST EARNINGS SURPRISES**: 
{data['earnings_hist']}
- **NEXT EARNINGS DATE**: {data['next_earnings']}

### 2. Smart Money Indicators:
- **Insider Activity**: 
{data['insider']}
- **Short Ratio**: {data['short_ratio']}

### 3. Technicals & Momentum:
- Price: ${data['price']} | MA20: ${data['ma20_curr']}
- RSI (14-Day): {data['rsi']} | MACD Line: {data['macd']}

### 4. Valuation & News:
- Forward P/E: {data['pe']} | Analyst Recommendation: {data['recommendation']}
- Recent News Highlights:
{news_text}

---
### ANALYSIS TASK ###
As {persona_name}, provide your high-conviction analysis:
1. **The "Earnings Fatigue" Check**: Based on past surprises ({data['earnings_hist']}), how should we position for the next event?
2. **Techno-Fundamental Synthesis**: Combine Technical Score ({data['tech_score']}) with Valuation (P/E). Is this a "trap" or an "opportunity"?
3. **Smart Money & News**: Are insiders buying the dip or exiting before the catalyst?
4. Provide 3 specific Buy Reasons and 3 specific Risks.
5. High-conviction outlook for 5-10 trading days.
"""
    return prompt

# --- SIDEBAR ---
st.sidebar.title("🔍 Ollie Control")
tab_choice = st.sidebar.radio("Navigate", ["Market Radar", "Expert Analysis"])

try:
    with open("watchlist.txt", "r") as f:
        watchlist = [line.strip().upper() for line in f if line.strip()]
except:
    watchlist = ["AAPL", "TSLA", "NVDA", "GOOGL", "MSFT"]

st.sidebar.markdown("---")
if tab_choice == "Expert Analysis":
    selected_symbol = st.sidebar.selectbox("Select Ticker", watchlist)
    persona_options = {
        "Warren Buffett": "Value/Moat focus",
        "Cathie Wood": "Innovation/Growth focus",
        "Michael Burry": "Contrarian skepticism",
        "Ray Dalio": "Macro/Cycle focus",
        "Peter Lynch": "GARP/Stock-picking focus",
        "Jim Cramer": "Momentum/Sentiment focus"
    }
    selected_persona = st.sidebar.radio("Persona", list(persona_options.keys()))
else:
    selected_symbol = None

# --- MAIN ---
st.title(f"📈 Ollie - {tab_choice}")

if tab_choice == "Market Radar":
    st.subheader("📡 Live Market Radar")
    
    # --- Watchlist Management ---
    with st.expander("⚙️ Manage Watchlist Tickers"):
        current_tickers = ", ".join(watchlist)
        edited_tickers = st.text_area("Edit tickers (comma separated):", current_tickers, height=100)
        if st.button("💾 Save Watchlist"):
            new_list = [t.strip().upper() for t in edited_tickers.split(",") if t.strip()]
            with open("watchlist.txt", "w") as f:
                f.write("\n".join(new_list))
            st.success("Watchlist updated!")
            st.rerun()

    st.markdown("---")
    radar_data = []
    with st.spinner("Scanning the market..."):
        for sym in watchlist:
            try:
                ticker = yf.Ticker(sym)
                hist = ticker.history(period="1mo")
                if not hist.empty:
                    # Calculate RSI
                    delta = hist['Close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rsi_val = 100 - (100 / (1 + (gain/loss)))
                    
                    price_now = hist['Close'].iloc[-1]
                    price_last_week = hist['Close'].iloc[-5]
                    change_pct = ((price_now - price_last_week) / price_last_week) * 100
                    
                    radar_data.append({
                        "Ticker": sym,
                        "Price": round(price_now, 2),
                        "Weekly %": round(change_pct, 2),
                        "RSI (14)": round(rsi_val.iloc[-1], 2),
                        "Status": "Overbought" if rsi_val.iloc[-1] > 70 else ("Oversold" if rsi_val.iloc[-1] < 30 else "Neutral")
                    })
            except:
                continue
    
    if radar_data:
        df = pd.DataFrame(radar_data)
        
        # --- PREMIUM DATAFRAME CONFIG ---
        st.dataframe(
            df,
            column_config={
                "Ticker": st.column_config.TextColumn("Symbol", help="Stock Ticker"),
                "Price": st.column_config.NumberColumn("Current Price", format="$%.2f"),
                "Weekly %": st.column_config.NumberColumn(
                    "Weekly Perf",
                    format="%.2f%%",
                    help="Performance over the last 5 trading days"
                ),
                "RSI (14)": st.column_config.ProgressColumn(
                    "Relative Strength (RSI)",
                    help="RSI > 70 is Overbought, < 30 is Oversold",
                    format="%.0f",
                    min_value=0,
                    max_value=100,
                ),
                "Status": st.column_config.TextColumn("Condition")
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Dynamic Legend
        st.markdown("""
            <div style="display: flex; gap: 20px; font-size: 0.8em; margin-top: 10px;">
                <span style="color: #00ff88;">● Up / Oversold</span>
                <span style="color: #ff4b4b;">● Down / Overbought</span>
                <span style="color: #888;">● Neutral</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("No data found for the current watchlist.")

    st.info("💡 **Pro Tip:** Look for stocks with **Negative Weekly %** but **Oversold RSI** for potential bounce plays.")

elif tab_choice == "Expert Analysis" and selected_symbol:
    data, news = get_stock_data(selected_symbol)
    if data:
        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", f"${data['price']}", f"{data['change']}%")
        c2.metric("Technical Score", f"{data['tech_score']}/4", "Bullish" if data['tech_score'] > 0 else "Bearish")
        c3.metric(f"Sector ({data['sector_etf']})", f"{data['sector_change']}%")
        c4.metric("RSI", data['rsi'])

        # Multi-panel Chart (Price + Volume)
        from plotly.subplots import make_subplots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.03, subplot_titles=(f'{selected_symbol} Technicals', 'Volume'), 
                           row_width=[0.3, 0.7])

        # Candlestick
        fig.add_trace(go.Candlestick(x=data['history'].index, open=data['history']['Open'], 
                        high=data['history']['High'], low=data['history']['Low'], 
                        close=data['history']['Close'], name="Price"), row=1, col=1)
        
        # MA20
        fig.add_trace(go.Scatter(x=data['history'].index, y=data['history']['MA20'], 
                        line=dict(color='#FFD700', width=2), name="MA20"), row=1, col=1)
        
        # Volume
        colors = ['red' if row['Open'] > row['Close'] else 'green' for _, row in data['history'].iterrows()]
        fig.add_trace(go.Bar(x=data['history'].index, y=data['history']['Volume'], 
                        marker_color=colors, name="Volume"), row=2, col=1)

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, width='stretch')

        # Info row
        st.info(f"🛡️ **Earnings Surprise History:**\n{data['earnings_hist']}")

        # Prompt
        final_prompt = generate_prompt(data, news, selected_persona, persona_options[selected_persona])
        st.subheader(f"🤖 {selected_persona} Analysis Prompt")
        st.text_area("Final Strategy Prompt (Copy to AI)", final_prompt, height=350)
        
        if st.button("📋 Copy Strategy"):
            pyperclip.copy(final_prompt)
            st.success("Strategy Copied to Clipboard!")
    else:
        st.error("Data Fetch Error.")

st.markdown("---")
st.caption("Ollie v5.0 - Professional Market Intelligence Deck")
