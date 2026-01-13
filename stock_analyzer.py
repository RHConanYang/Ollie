import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_stock_info(ticker_symbol):
    """
    Fetch comprehensive stock data including technicals, fundamentals, earnings, and sector context.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. Fetch Price Data
        hist = ticker.history(period="1mo")
        if hist.empty:
            return None, "Ticker symbol not found."
        
        # Technicals
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        latest_price = hist['Close'].iloc[-1]
        price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100
        
        # 2. Fetch Deep Fundamentals & Info
        info = ticker.info
        sector = info.get('sector', 'N/A')
        
        # Earnings Data
        calendar = ticker.calendar
        next_earnings = "N/A"
        if calendar and 'Earnings Date' in calendar:
            dates = calendar['Earnings Date']
            next_earnings = ", ".join([d.strftime('%Y-%m-%d') for d in dates]) if isinstance(dates, list) else dates.strftime('%Y-%m-%d')

        analysis_data = {
            "target_price": info.get('targetMeanPrice', 'N/A'),
            "recommendation": info.get('recommendationKey', 'N/A').replace('_', ' ').capitalize(),
            "gross_margins": f"{info.get('grossMargins', 0) * 100:.2f}%" if info.get('grossMargins') else 'N/A',
            "roe": f"{info.get('returnOnEquity', 0) * 100:.2f}%" if info.get('returnOnEquity') else 'N/A',
            "free_cashflow": f"{info.get('freeCashflow', 0) / 1e9:.2f}B" if info.get('freeCashflow') else 'N/A',
            "next_earnings": next_earnings,
            "sector": sector
        }
        
        fundamentals = {
            "pe_ratio": info.get('forwardPE', 'N/A'),
            "beta": info.get('beta', 'N/A'),
            "market_cap": f"{info.get('marketCap', 0) / 1e9:.2f}B" if info.get('marketCap') else 'N/A',
            "fifty_two_week_high": info.get('fiftyTwoWeekHigh', 'N/A'),
            "fifty_two_week_low": info.get('fiftyTwoWeekLow', 'N/A')
        }
        
        # 3. Sector Context (Compare stock with S&P 500)
        spy = yf.Ticker("SPY").history(period="1wk")
        spy_change = ((spy['Close'].iloc[-1] - spy['Close'].iloc[0]) / spy['Close'].iloc[0]) * 100
        
        price_summary = {
            "latest_price": round(latest_price, 2),
            "weekly_change_pct": round(price_change, 2),
            "spy_weekly_change": round(spy_change, 2),
            "rsi": round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else 'N/A',
            "ma_20": round(hist['Close'].rolling(window=20).mean().iloc[-1], 2),
            "volume": hist['Volume'].iloc[-1]
        }
        
        # 4. Fetch News
        news = ticker.news[:5]
        news_list = []
        if news:
            for item in news:
                content = item.get('content', {})
                title = content.get('title')
                publisher = "Yahoo Finance"
                if 'finance' in content and 'owner' in content['finance']:
                    publisher = content['finance']['owner'].get('displayName', "Yahoo Finance")
                if title:
                    news_list.append({"title": title, "publisher": publisher})
        
        if not news_list:
            import requests
            from bs4 import BeautifulSoup
            rss_url = f"https://news.google.com/rss/search?q={ticker_symbol}+stock&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(rss_url)
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.findAll('item')[:5]
            for item in items:
                news_list.append({"title": item.title.text, "publisher": item.source.text if item.source else "Google News"})
            
        return (price_summary, fundamentals, analysis_data), news_list
        
    except Exception as e:
        return None, str(e)

def generate_ai_prompt(ticker_symbol, data, news_list, persona):
    """
    Generate an ultra-depth analysis prompt for AI based on selected persona.
    """
    price_summary, fundamentals, analysis_data = data
    news_text = "\n".join([f"- {n['title']} (Source: {n['publisher']})" for n in news_list])
    
    # Define Persona Instructions
    personas = {
        "1": {
            "name": "Standard/Balanced Analyst",
            "instruction": "Provide a balanced view covering both technical, fundamental, and upcoming event risks."
        },
        "2": {
            "name": "Value & Fundamental Specialist",
            "instruction": "Focus heavily on Financial Health, P/E, Cashflow, and how the stock compares to the broader market valuation."
        },
        "3": {
            "name": "Technical & Momentum Specialist",
            "instruction": "Focus heavily on Momentum, Volatility (Beta), and Price Action relative to the S&P 500 (SPY)."
        }
    }
    
    selected_persona = personas.get(persona, personas["1"])
    
    prompt = f"""
You are a {selected_persona['name']}. Your goal is: {selected_persona['instruction']}

### 📊 MASTER DATASET FOR {ticker_symbol} ###

### 1. Market & Sector Performance:
- Latest Close Price: ${price_summary['latest_price']}
- Weekly Change: {price_summary['weekly_change_pct']}%
- **VS S&P 500 (SPY) Change**: {price_summary['spy_weekly_change']}%
- Sector: {analysis_data['sector']}
- 20-Day Moving Average (MA20): ${price_summary['ma_20']}
- RSI (14-Day): {price_summary['rsi']}
- Beta (Volatility): {fundamentals['beta']}

### 2. Fundamental & Profitability Metrics:
- Market Cap: {fundamentals['market_cap']}
- Forward P/E Ratio: {fundamentals['pe_ratio']}
- Gross Margins: {analysis_data['gross_margins']}
- Return on Equity (ROE): {analysis_data['roe']}
- Free Cash Flow: {analysis_data['free_cashflow']}
- 52-Week Range: ${fundamentals['fifty_two_week_low']} - ${fundamentals['fifty_two_week_high']}

### 3. Institutional Context & Upcoming Events:
- **NEXT EARNINGS DATE**: {analysis_data['next_earnings']}
- Analyst Target Price (Mean): ${analysis_data['target_price']}
- Analyst Recommendation: {analysis_data['recommendation']}

- Recent News Catalysts:
{news_text}

---
### ANALYSIS TASK ###
Based on your expertise as a {selected_persona['name']}, please provide a professional analysis.
1. **Relative Strength**: Is the stock outperforming or underperforming the S&P 500? What does this tell us?
2. **Event Risk**: How should the upcoming Earnings Date ({analysis_data['next_earnings']}) affect a trader's decision right now?
3. **Valuation vs. Momentum**: Contrast the current Fundamentals (P/E, Margins) with Technicals (RSI/MA).
4. Provide 3 high-conviction "Buy Reasons" and 3 "Key Risks".
5. Give a final outlook for the next 5-10 trading days.
"""
    return prompt

if __name__ == "__main__":
    print("-" * 30)
    print("      OLLIE - PROMPT FACTORY   ")
    print("-" * 30)
    
    symbol = input("Enter ticker symbol (e.g., NVDA, TSLA): ").upper()
    
    print("\nSelect Analyst Persona:")
    print("1. Standard (Balanced)")
    print("2. Value Specialist (Fundamentals focus)")
    print("3. Technical Specialist (Price action focus)")
    persona_choice = input("Enter choice (1-3): ") or "1"
    
    print(f"\nProcessing high-depth data for {symbol}...\n")
    
    result, news_data = get_stock_info(symbol)
    
    if result:
        ai_prompt = generate_ai_prompt(symbol, result, news_data, persona_choice)
        print("="*30)
        print("GENERATE PROFESSIONAL AI PROMPT:")
        print("="*30)
        print(ai_prompt)
        
        # Save to file
        with open(f"{symbol}_expert_prompt.txt", "w", encoding="utf-8") as f:
            f.write(ai_prompt)
        print(f"\nExpert prompt saved to: {symbol}_expert_prompt.txt")
    else:
        print(f"Error: {news_data}")
