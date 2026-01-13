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

# --- LANGUAGE DICTIONARY ---
LANG_DICT = {
    "EN": {
        "title": "Ollie - Expert Prompt Factory",
        "market_radar": "Market Radar",
        "expert_analysis": "Expert Analysis",
        "manage_watchlist": "⚙️ Manage Watchlist Tickers",
        "edit_tickers": "Edit tickers (comma separated):",
        "save_watchlist": "💾 Save Watchlist",
        "scanning": "Scanning the market...",
        "radar_hint": "💡 **Pro Tip:** Look for stocks with **Negative Weekly %** but **Oversold RSI** for potential bounce plays.",
        "select_ticker": "Select Ticker",
        "persona": "Analyst Persona",
        "tech_score": "Technical Score",
        "price": "Price",
        "rsi": "RSI",
        "sector": "Sector",
        "bullish": "Bullish",
        "bearish": "Bearish",
        "copy_btn": "📋 Copy Strategy Prompt",
        "success_copy": "Strategy Copied!",
        "prompt_header": "Analysis Prompt",
        "about_recom": "**About Recommendations:** Analyst targets and ratings are from Yahoo Finance.",
        "earnings_title": "🛡️ Earnings Surprise History:",
        "condition": "Condition",
        "status_neutral": "Neutral",
        "status_overbought": "Overbought",
        "status_oversold": "Oversold",
        "prompt_instr": "As {name}, provide your high-conviction analysis:",
        "prompt_task1": "1. **The 'Earnings Fatigue' Check**: Based on past surprises, how should we position?",
        "prompt_task2": "2. **Techno-Fundamental Synthesis**: Combine Technical Score with Valuation.",
        "prompt_task3": "3. **Smart Money**: Analyze Insider/Short sentiment.",
        "final_caption": "Ollie v6.1 - Professional Multi-Language Terminal"
    },
    "TW": {
        "title": "Ollie - 專業提示詞終端",
        "market_radar": "市場雷達",
        "expert_analysis": "深度專家分析",
        "manage_watchlist": "⚙️ 管理自選名單",
        "edit_tickers": "編輯代號 (用逗號分隔):",
        "save_watchlist": "💾 儲存清單",
        "scanning": "正在掃描市場數據...",
        "radar_hint": "💡 **專家提示:** 尋找 **週跌幅為負** 但 **RSI 超賣** 的股票，這通常是潛在的反彈機會。",
        "select_ticker": "選擇股票代號",
        "persona": "分析師人格",
        "tech_score": "技術面評分",
        "price": "目前價格",
        "rsi": "RSI 指數",
        "sector": "所屬板塊",
        "bullish": "看多",
        "bearish": "看空",
        "copy_btn": "📋 複製分析提示詞",
        "success_copy": "分析指令已複製到剪貼簿！",
        "prompt_header": "專家分析指令 (Prompt)",
        "about_recom": "**關於建議數據:** 目標價與分析師評等彙整自 Yahoo Finance 專業機構數據。",
        "earnings_title": "🛡️ 歷史財報數據 (驚喜度):",
        "condition": "當前狀態",
        "status_neutral": "中性",
        "status_overbought": "超買/過熱",
        "status_oversold": "超賣/低估",
        "prompt_instr": "請以 {name} 的身份，提供專業的高勝率分析：",
        "prompt_task1": "1. **財報慣性檢查**: 根據歷史財報驚喜度，這檔股票在下次事件應如何佈局？",
        "prompt_task2": "2. **技資合一分析**: 結合技術評分與基本面估值，這是一個「陷阱」還是「機會」？",
        "prompt_task3": "3. **大戶動向**: 分析內部人交易與券賣比所呈現的市場情緒。",
        "final_caption": "Ollie v6.1 - 專業中英雙語投資終端"
    }
}

# --- SIDEBAR ---
st.sidebar.title("🌍 Language / 語言")
lang_choice = st.sidebar.selectbox("Select Language", ["English", "繁體中文"])
L = LANG_DICT["EN"] if lang_choice == "English" else LANG_DICT["TW"]

st.sidebar.markdown("---")
st.sidebar.title(f"🔍 {L['title']}")
tab_choice = st.sidebar.radio("Navigate", [L['market_radar'], L['expert_analysis']])

# Reset tab names comparison logic
is_radar = tab_choice == L['market_radar']
is_expert = tab_choice == L['expert_analysis']

try:
    with open("watchlist.txt", "r") as f:
        watchlist = [line.strip().upper() for line in f if line.strip()]
except:
    watchlist = ["AAPL", "TSLA", "NVDA", "GOOGL", "MSFT"]

st.sidebar.markdown("---")
if is_expert:
    selected_symbol = st.sidebar.selectbox(L['select_ticker'], watchlist)
    persona_options = {
        "Warren Buffett": "Value/Moat focus",
        "Cathie Wood": "Innovation/Growth focus",
        "Michael Burry": "Contrarian skepticism",
        "Ray Dalio": "Macro/Cycle focus",
        "Peter Lynch": "GARP/Stock-picking focus",
        "Jim Cramer": "Momentum/Sentiment focus"
    }
    selected_persona = st.sidebar.radio(L['persona'], list(persona_options.keys()))
else:
    selected_symbol = None

# --- MAIN ---
st.title(f"📈 {tab_choice}")

if is_radar:
    st.subheader(L['market_radar'])
    
    # --- Watchlist Management ---
    with st.expander(L['manage_watchlist']):
        current_tickers = ", ".join(watchlist)
        edited_tickers = st.text_area(L['edit_tickers'], current_tickers, height=100)
        if st.button(L['save_watchlist']):
            new_list = [t.strip().upper() for t in edited_tickers.split(",") if t.strip()]
            with open("watchlist.txt", "w") as f:
                f.write("\n".join(new_list))
            st.success("Watchlist updated!")
            st.rerun()

    st.markdown("---")
    radar_data = []
    with st.spinner(L['scanning']):
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
                    
                    cur_rsi = rsi_val.iloc[-1]
                    status_text = L["status_overbought"] if cur_rsi > 70 else (L["status_oversold"] if cur_rsi < 30 else L["status_neutral"])
                    
                    radar_data.append({
                        "Ticker": sym,
                        "Price": round(price_now, 2),
                        "Weekly %": round(change_pct, 2),
                        "RSI (14)": round(cur_rsi, 2),
                        L["condition"]: status_text
                    })
            except:
                continue
    
    if radar_data:
        df = pd.DataFrame(radar_data)
        st.dataframe(
            df,
            column_config={
                "Ticker": st.column_config.TextColumn("Symbol"),
                "Price": st.column_config.NumberColumn(L["price"], format="$%.2f"),
                "Weekly %": st.column_config.NumberColumn("Weekly %", format="%.2f%%"),
                "RSI (14)": st.column_config.ProgressColumn(L["rsi"], min_value=0, max_value=100),
            },
            hide_index=True,
            use_container_width=True
        )
    
    st.info(L['radar_hint'])

elif is_expert and selected_symbol:
    data, news = get_stock_data(selected_symbol)
    if data:
        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(L["price"], f"${data['price']}", f"{data['change']}%")
        c2.metric(L["tech_score"], f"{data['tech_score']}/4", L["bullish"] if data['tech_score'] > 0 else L["bearish"])
        c3.metric(f"{L['sector']} ({data['sector_etf']})", f"{data['sector_change']}%")
        c4.metric(L["rsi"], data['rsi'])

        # Multi-panel Chart (Price + Volume)
        from plotly.subplots import make_subplots
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                           vertical_spacing=0.03, subplot_titles=(f'{selected_symbol}', 'Volume'), 
                           row_width=[0.3, 0.7])

        fig.add_trace(go.Candlestick(x=data['history'].index, open=data['history']['Open'], 
                        high=data['history']['High'], low=data['history']['Low'], 
                        close=data['history']['Close'], name="Price"), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=data['history'].index, y=data['history']['MA20'], 
                        line=dict(color='#FFD700', width=2), name="MA20"), row=1, col=1)
        
        colors = ['red' if row['Open'] > row['Close'] else 'green' for _, row in data['history'].iterrows()]
        fig.add_trace(go.Bar(x=data['history'].index, y=data['history']['Volume'], 
                        marker_color=colors, name="Volume"), row=2, col=1)

        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, showlegend=False)
        st.plotly_chart(fig, width='stretch')

        st.info(f"{L['earnings_title']}\n{data['earnings_hist']}")

        # Prompt Generation with Correct Localization
        final_prompt = generate_prompt(data, news, selected_persona, persona_options[selected_persona])
        
        # Rewrite the prompt instructions in the selected language
        if lang_choice == "繁體中文":
            final_prompt = final_prompt.replace(f"As {selected_persona}, provide your high-conviction analysis:", L["prompt_instr"].format(name=selected_persona))
            final_prompt = final_prompt.replace("1. **The \"Earnings Fatigue\" Check\": Based on past surprises ({data['earnings_hist']}), how should we position for the next event?", L["prompt_task1"])
            final_prompt = final_prompt.replace("2. **Techno-Fundamental Synthesis**: Combine Technical Score ({data['tech_score']}) with Valuation (P/E). Is this a \"trap\" or an \"opportunity\"?", L["prompt_task2"])
            final_prompt = final_prompt.replace("3. **Smart Money & News**: Are insiders buying the dip or exiting before the catalyst?", L["prompt_task3"])

        st.subheader(f"🤖 {L['prompt_header']}")
        st.text_area("Copy to AI", final_prompt, height=350)
        
        if st.button(L['copy_btn']):
            pyperclip.copy(final_prompt)
            st.success(L['success_copy'])
    else:
        st.error("Data Fetch Error.")

st.markdown("---")
st.caption(L['final_caption'])

st.markdown("---")
st.caption("Ollie v5.0 - Professional Market Intelligence Deck")
