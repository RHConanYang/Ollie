import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_stock_info(ticker_symbol):
    """
    獲取股票價格與新聞
    """
    try:
        # 建立 Ticker 物件
        ticker = yf.Ticker(ticker_symbol)
        
        # 1. 獲取股價 (過去一週)
        hist = ticker.history(period="1wk")
        if hist.empty:
            return None, "找不到該股票代號的數據。"
        
        latest_price = hist['Close'].iloc[-1]
        price_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        
        price_summary = {
            "latest_price": round(latest_price, 2),
            "weekly_change_pct": round(price_change, 2),
            "high": round(hist['High'].max(), 2),
            "low": round(hist['Low'].min(), 2),
            "volume": hist['Volume'].iloc[-1]
        }
        
        # 2. 獲取新聞
        # 優先嘗試 yfinance 的新聞 (整合 Yahoo Finance)
        news = ticker.news[:5]
        news_list = []
        
        if news:
            for item in news:
                content = item.get('content', {})
                title = content.get('title')
                # 嘗試獲取出版者名稱
                publisher = "Yahoo Finance"
                if 'finance' in content and 'owner' in content['finance']:
                    publisher = content['finance']['owner'].get('displayName', "Yahoo Finance")
                
                if title:
                    news_list.append({
                        "title": title,
                        "publisher": publisher
                    })
        
        # 如果 yfinance 沒抓到新聞，則使用 Google News RSS 作為備案 (優力、免費且全面)
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
    產生餵給 AI 的 Prompt
    """
    news_text = "\n".join([f"- {n['title']} (來源: {n['publisher']})" for n in news_list])
    
    prompt = f"""
你是一位資深美股分析師。請根據以下關於 {ticker_symbol} 的最新數據，分析其下週走勢，並給出三個買入理由與三個風險。

### 數據概況:
- **股票代號**: {ticker_symbol}
- **最新收盤價**: ${price_summary['latest_price']}
- **本週漲跌幅**: {price_summary['weekly_change_pct']}%
- **本週最高/最低**: ${price_summary['high']} / ${price_summary['low']}
- **成交量**: {price_summary['volume']:,}

### 最新相關新聞:
{news_text}

---
請根據上述數據與新聞，提供專業的分析報告。
"""
    return prompt

if __name__ == "__main__":
    symbol = input("請輸入股票代號 (例如 AAPL, TSLA): ").upper()
    print(f"\n正在抓取 {symbol} 的數據中...\n")
    
    price_data, news_data = get_stock_info(symbol)
    
    if price_data:
        ai_prompt = generate_ai_prompt(symbol, price_data, news_data)
        print("="*30)
        print("產生的 AI Prompt 如下：")
        print("="*30)
        print(ai_prompt)
        
        # 同時存成檔案方便用戶複製
        with open(f"{symbol}_ai_prompt.txt", "w", encoding="utf-8") as f:
            f.write(ai_prompt)
        print(f"\nPrompt 已自動存檔至: {symbol}_ai_prompt.txt")
    else:
        print(f"錯誤: {news_data}")
