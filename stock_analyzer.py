import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_stock_info(ticker_symbol):
    """
    Fetch stock price data and news.
    """
    try:
        # Create Ticker object
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. Fetch Price Data (past week)
        hist = ticker.history(period="1wk")
        if hist.empty:
            return None, "Ticker symbol not found."
        
        latest_price = hist['Close'].iloc[-1]
        price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        
        price_summary = {
            "latest_price": round(latest_price, 2),
            "weekly_change_pct": round(price_change, 2),
            "high": round(hist['High'].max(), 2),
            "low": round(hist['Low'].min(), 2),
            "volume": hist['Volume'].iloc[-1]
        }
        
        # 2. Fetch News
        # Primary source: yfinance (Yahoo Finance)
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
                    news_list.append({
                        "title": title,
                        "publisher": publisher
                    })
        
        # Secondary source: Google News RSS (if yfinance returns nothing)
        if not news_list:
            import requests
            from bs4 import BeautifulSoup
            rss_url = f"https://news.google.com/rss/search?q={ticker_symbol}+stock&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(rss_url)
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.findAll('item')[:5]
            for item in items:
                news_list.append({
                    "title": item.title.text,
                    "publisher": item.source.text if item.source else "Google News"
                })
            
        return price_summary, news_list
        
    except Exception as e:
        return None, str(e)

def generate_ai_prompt(ticker_symbol, price_summary, news_list):
    """
    Generate an analysis prompt for AI.
    """
    news_text = "\n".join([f"- {n['title']} (Source: {n['publisher']})" for n in news_list])
    
    prompt = f"""
You are a senior US stock market analyst. Based on the following data for {ticker_symbol}, analyze its trend for the upcoming week and provide three reasons to buy and three risks.

### Data Overview:
- **Ticker**: {ticker_symbol}
- **Latest Close Price**: ${price_summary['latest_price']}
- **Weekly Change**: {price_summary['weekly_change_pct']}%
- **Weekly High/Low**: ${price_summary['high']} / ${price_summary['low']}
- **Volume**: {price_summary['volume']:,}

### Latest News:
{news_text}

---
Please provide a professional analysis report based on the data and news above.
"""
    return prompt

if __name__ == "__main__":
    symbol = input("Enter ticker symbol (e.g., AAPL, TSLA): ").upper()
    print(f"\nFetching data for {symbol}...\n")
    
    price_data, news_data = get_stock_info(symbol)
    
    if price_data:
        ai_prompt = generate_ai_prompt(symbol, price_data, news_data)
        print("="*30)
        print("Generated AI Prompt:")
        print("="*30)
        print(ai_prompt)
        
        # Save to file
        with open(f"{symbol}_ai_prompt.txt", "w", encoding="utf-8") as f:
            f.write(ai_prompt)
        print(f"\nPrompt automatically saved to: {symbol}_ai_prompt.txt")
    else:
        print(f"Error: {news_data}")
