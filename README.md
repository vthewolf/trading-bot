# 🤖 Trading Bot - AI-Powered Trading Assistant

Autonomous trading analysis system powered by Claude Opus 4.6 that provides daily market insights and manages portfolio tracking via Telegram.

## 🎯 What It Does

- **Daily Analysis (8:00 AM CET)**: Automated market analysis with macro context, opportunities validation, and crypto sentiment
- **Portfolio Management**: Track positions, P&L, and trades via simple Telegram commands
- **Risk Management**: Built-in anti-FOMO checks, stop-loss tracking, and position sizing rules
- **Learning System**: Identifies patterns from your trading history (v1.1 coming soon)

## 💰 Cost

**$0.30/month** (within AWS Free Tier + Claude API)

- AWS: $0.00 (Free Tier covers all services)
- Claude Opus 4.6 API: ~$0.30/month
  - Daily analysis: ~478 input tokens, ~319 output tokens
  - 30 days × $0.01 = $0.30

## 🏗️ Tech Stack

**Cloud Infrastructure:**

- AWS Lambda (Python 3.12)
- AWS S3 (data storage)
- AWS Parameter Store (secrets)
- AWS EventBridge (daily scheduler)
- AWS API Gateway (Telegram webhook)

**AI & APIs:**

- Claude Opus 4.6 (Anthropic API)
- Telegram Bot API
- yfinance (market data)

## 🚀 Getting Started

Complete setup guide: [docs/setup/](docs/setup/)

**Quick overview:**

1. Create AWS account
2. Deploy infrastructure (S3, Lambda, IAM)
3. Configure Telegram webhook
4. Receive daily analysis automatically

## 📊 Architecture

See [docs/technical/architecture.md](docs/technical/architecture.md) for detailed architecture diagram and data flow.
