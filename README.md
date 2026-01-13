# Ollie - AI Stock Market Analyzer 📈

Ollie is a simple yet powerful tool for US stock market analysis. It automatically fetches the latest price data and real-time news, then generates a structured AI analysis prompt to help you gain investment insights.

## Features

- **Real-time Data**: Get the latest close price, weekly change, and volume using `yfinance`.
- **News Integration**: Combines Yahoo Finance and Google News to fetch the most relevant market updates.
- **AI-Friendly**: Generates a structured prompt that can be directly pasted into ChatGPT, Claude, or Gemini for deep analysis.
- **Lightweight**: No complex configuration required, just run and analyze.

## Installation

1. **Clone the repository**
   ```bash
   git clone git@github.com:RHConanYang/Ollie.git
   cd Ollie
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the main script and enter a ticker symbol (e.g., AAPL):

```bash
python stock_analyzer.py
```

After execution, the program will:
1. Display the analysis data in the terminal.
2. Generate a `[TICKER]_ai_prompt.txt` file, which you can paste directly into an AI for analysis.

## Tech Stack

- Python 3.12
- yfinance (Data Source)
- BeautifulSoup4 (News Parsing)
- Pandas (Data Processing)

## Disclaimer

This tool is for informational purposes only and does not constitute investment advice. Investing involves risk.
