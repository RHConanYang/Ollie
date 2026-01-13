import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_stock_info(ticker_symbol):
    """
    Fetch stock price data (with technical indicators), fundamentals, and news.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. Fetch Price Data (past month to calculate indicators)
        hist = ticker.history(period="1mo")
        if hist.empty:
            return None, "Ticker symbol not found."
        
        # Calculate Technical Indicators (Manual calculation to avoid extra dependencies)
        # RSI (14 days)
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        latest_price = hist['Close'].iloc[-1]
        price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100 # Weekly
        
        # 2. Fetch Fundamentals
        info = ticker.info
        fundamentals = {
            "pe_ratio": info.get('forwardPE', 'N/A'),
            "beta": info.get('beta', 'N/A'),
            "market_cap": f"{info.get('marketCap', 0) / 1e9:.2f}B" if info.get('marketCap') else 'N/A',
            "fifty_two_week_high": info.get('fiftyTwoWeekHigh', 'N/A'),
            "fifty_two_week_low": info.get('fiftyTwoWeekLow', 'N/A')
        }
        
        price_summary = {
            "latest_price": round(latest_price, 2),
            "weekly_change_pct": round(price_change, 2),
            "rsi": round(rsi.iloc[-1], 2) if not pd.isna(rsi.iloc[-1]) else 'N/A',
            "ma_20": round(hist['Close'].rolling(window=20).mean().iloc[-1], 2),
            "volume": hist['Volume'].iloc[-1]
        }
        
        # 3. Fetch News (Same logic as before)
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
            
        return (price_summary, fundamentals), news_list
        
    except Exception as e:
        return None, str(e)

def generate_ai_prompt(ticker_symbol, data, news_list):
    """
    Generate an enhanced analysis prompt for AI.
    """
    price_summary, fundamentals = data
    news_text = "\n".join([f"- {n['title']} (Source: {n['publisher']})" for n in news_list])
    
    prompt = f"""
You are a senior US stock market analyst. Conduct a deep-dive analysis for {ticker_symbol} based on the multi-dimensional data provided below.

### 1. Market Price Action:
- **Latest Close Price**: ${price_summary['latest_price']}
- **Weekly Change**: {price_summary['weekly_change_pct']}%
- **20-Day Moving Average (MA20)**: ${price_summary['ma_20']}
- **Relative Strength Index (RSI-14)**: {price_summary['rsi']}
- **Volume**: {price_summary['volume']:,}

### 2. Fundamental Context:
- **Market Cap**: {fundamentals['market_cap']}
- **Forward P/E**: {fundamentals['pe_ratio']}
- **Beta (Volatility)**: {fundamentals['beta']}
- **52-Week Range**: ${fundamentals['fifty_two_week_low']} - ${fundamentals['fifty_two_week_high']}

### 3. Latest Catalysts (News):
{news_text}

---
**Task:**
Analyze the short-term (1 week) and medium-term trend. 
1. Is the stock technically overbought or oversold according to the RSI and MA20?
2. How does the fundamental valuation (P/E, Market Cap) influence the risk profile?
3. Synthesize the news catalysts with the price action.
4. Provide 3 specific Buy Reasons and 3 specific Risks.
"""
    return prompt

if __name__ == "__main__":
    symbol = input("Enter ticker symbol (e.g., AAPL, TSLA): ").upper()
    print(f"\nFetching enhanced data for {symbol}...\n")
    
    result, news_data = get_stock_info(symbol)
    
    if result:
        ai_prompt = generate_ai_prompt(symbol, result, news_data)
        print("="*30)
        print("Generated ENHANCED AI Prompt:")
        print("="*30)
        print(ai_prompt)
        
        # Save to file
        with open(f"{symbol}_ai_prompt.txt", "w", encoding="utf-8") as f:
            f.write(ai_prompt)
        print(f"\nEnhanced prompt saved to: {symbol}_ai_prompt.txt")
    else:
        print(f"Error: {news_data}")
