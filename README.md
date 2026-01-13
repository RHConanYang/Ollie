# Ollie - AI Stock Market Analyzer 📈

Ollie 是一個簡單而強大的美股分析工具。它能自動抓取最新的股價數據與即時新聞，並生成一段專業的 AI 分析 Prompt，讓你輕鬆獲取投資見解。

## 功能特色

- **即時數據**：利用 `yfinance` 獲取最新的收盤價、漲跌幅及交易量。
- **新聞整合**：結合 Yahoo Finance 與 Google News，抓取最相關的市場動態。
- **AI 友善**：自動生成結構化的 Prompt，可直接餵給 ChatGPT、Claude 或 Gemini 進行深度分析。
- **輕量化**：無需複雜設定，一鍵執行。

## 安裝教學

1. **複製儲存庫**
   ```bash
   git clone git@github.com:RHConanYang/Ollie.git
   cd Ollie
   ```

2. **安裝必要套件**
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

執行主程式並輸入股票代號（例如 AAPL）：

```bash
python stock_analyzer.py
```

執行後，程式會：
1. 在終端機顯示分析數據。
2. 同時產生一個 `[股票代號]_ai_prompt.txt` 檔案，內容可直接貼給 AI 進行分析。

## 技術棧

- Python 3.12
- yfinance (數據來源)
- BeautifulSoup4 (新聞解析)
- Pandas (數據處理)

## 免責聲明

本工具僅供參考，不構成任何投資建議。投資有風險，入市需謹慎。
