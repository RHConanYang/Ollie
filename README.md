# 📈 Ollie - AI Expert Stock Analyzer (v6.1)

Ollie is a professional-grade AI Stock Analysis Terminal designed to bridge the gap between complex market data and high-quality AI-driven insights. It fetches real-time financial data, technical indicators, and macro environments to generate hyper-detailed prompts for LLMs (like ChatGPT, Claude, or DeepSeek).

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B)

## 🚀 Key Features

### 1. 📡 Live Market Radar
- **Watchlist Overview**: Real-time monitoring of multiple stocks simultaneously.
- **RSI Heatmap**: Instant visualization of overbought (>70) and oversold (<30) conditions.
- **Dynamic Management**: Edit your tracking list directly from the web interface.

### 2. 🎭 Expert Persona Hall of Fame
Analyze stocks through the lens of legendary investors:
- **Warren Buffett**: Value & Economic Moat focus.
- **Cathie Wood**: Innovation & Disruptive Growth focus.
- **Michael Burry**: Contrarian & Bubble Risk focus.
- **Ray Dalio**: Macro Cycles & Debt environment focus.
- **Peter Lynch**: GARP (Growth at Reasonable Price) focus.
- **Jim Cramer**: Momentum & Short-term sentiment focus.

### 3. 🔬 Deep Technical & Macro Insights
- **Advanced Charts**: Multi-panel Plotly charts featuring Candlesticks, MA20, and Volume.
- **Technical Scoring**: Automated "Technical Score (0-4/4)" based on RSI, MACD, and MA20.
- **Earnings History**: Past 4 earnings surprises (Estimated vs. Actual) for volatility prediction.
- **Global Macro**: Real-time VIX (Fear Gauge) and 10Y Treasury Yield integration.

### 4. 🌍 Multi-Language Support
- Full interface and prompt generation support for **English** and **繁體中文 (Traditional Chinese)**.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/RHConanYang/Ollie.git
   cd Ollie
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Launch the app**:
   ```bash
   streamlit run app.py
   ```

## 📋 Tech Stack
- **Data Source**: `yfinance` (Yahoo Finance API)
- **Engine**: Python 3.10+
- **UI Framework**: Streamlit
- **Visualization**: Plotly Interactive Charts
- **Clipboard**: Pyperclip for seamless one-click copying

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.

---
*Designed for serious investors who want to give their AI an edge.*
