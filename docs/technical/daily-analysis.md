# Daily Analysis Lambda

Deep dive into how the daily analysis system works.

## Overview

**Function:** `daily-analysis`

**Purpose:** Automated daily market analysis powered by Claude Opus 4.6

**Trigger:** EventBridge cron (8:00 AM CET daily)

**Runtime:** Python 3.12

**Average Duration:** 10-15 seconds

**Average Cost:** $0.01 per execution

---

## Execution Flow

```
EventBridge (7:00 UTC)
    ↓
Lambda starts
    ↓
Load configuration (Parameter Store + S3)
    ↓
Fetch market data (yfinance)
    ↓
Build optimized prompt (478 tokens)
    ↓
Call Claude Opus 4.6 API
    ↓
Receive analysis (319 tokens)
    ↓
Send to Telegram
    ↓
Log to S3
    ↓
Lambda ends
```

---

## Code Structure

### Main Handler

**File:** `lambdas/daily_analysis/handler.py`

**Entry point:** `lambda_handler(event, context)`

**Functions:**

1. `get_config()` - Load secrets
2. `load_portfolio()` - Get portfolio state
3. `get_market_data()` - Fetch prices
4. `build_prompt()` - Construct Claude prompt
5. `analyze_with_claude()` - API call
6. `clean_for_telegram()` - Format output
7. `send_telegram()` - Deliver message
8. `save_results()` - Log execution

---

## Configuration Loading

### get_config()

**Environment detection:**

- `ENVIRONMENT=local` → Read from `.env` file
- `ENVIRONMENT=aws` → Read from Parameter Store

**AWS mode loads:**

```python
/trading-bot/claude-api-key     # Anthropic API key
/trading-bot/telegram-token     # Bot token
/trading-bot/telegram-chat-id   # Your chat ID
```

**Local mode loads:**

```python
.env file:
CLAUDE_API_KEY=sk-ant-...
TELEGRAM_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=5411031813
S3_BUCKET=trading-bot-data-victor
MOCK_CLAUDE=false
```

**Mock mode:**

- `MOCK_CLAUDE=true` → Skip API call, return test response
- Used for local testing without consuming tokens

---

## Data Loading

### load_portfolio()

**Loads from S3:**

- `portfolio/current_positions.json` - Open positions
- `config/rules.json` - Trading rules (stop-loss, targets)
- `external/tickers_blacklist.txt` - Unavailable tickers

**Returns:**

```python
portfolio = {
    "positions": [
        {
            "ticker": "AAPL",
            "quantity": 2,
            "entry_price": 180.50,
            "date_open": "2026-02-15"
        }
    ],
    "cash_eur": 2300
}

blacklist = ["PLTR", "TSLA"]  # List of tickers

rules = {
    "trading_rules": {
        "stop_loss_percent": -10,
        "target_profit_percent": 20
    }
}
```

**Local mode:**

- Returns mock empty portfolio
- Reads `config/rules.json.example`

---

## Market Data

### get_market_data()

**Uses:** yfinance library

**Fetches for each open position:**

- Current price
- 24h change

**Rate limiting:**

```python
time.sleep(5)  # Between requests to avoid yfinance throttling
```

**Error handling:**

- Ticker not found → Log warning, continue
- API timeout → Log error, skip that ticker

**Output:**

```python
market_data = {
    "AAPL": {
        "current_price": 185.30
    }
}
```

**Note:** Only fetches data for tickers you already own (not scanning entire market).

---

## Prompt Construction

### build_prompt()

**Optimized for minimal tokens while maintaining quality.**

**Structure:**

```
Analista financiero experto. Fecha: {today}

POSICIONES ABIERTAS:
AAPL: 2 @ 180.50€ → 185.30€ (+2.66%)

REGLAS: Stop-loss -10%, Target 20%
NO DISPONIBLE TR: PLTR, TSLA

ANÁLISIS (máximo 200 palabras):

🌍 MACRO
Riesgo mercado: BAJO/MEDIO/ALTO
Razón: 1 línea

💼 POSICIONES (si hay)
Cada una: MANTENER/VENDER/AJUSTAR STOP
Razón: 1 línea

🎯 OPORTUNIDADES (0-3 tickers máximo)
Solo si pasa 4/4 checks...

₿ CRYPTO
BTC: ESPERAR/VIGILAR/ACTUAR
ETH: ESPERAR/VIGILAR/ACTUAR

✅ RESUMEN EJECUTIVO
2-3 líneas autosuficientes
```

**Key optimizations:**

- Only includes positions if they exist
- No market data details in prompt (Claude uses web search for current data)
- Structured format for consistent outputs
- Strict word limit (200 words)

**Token count:** ~478 tokens input

---

## Claude API Call

### analyze_with_claude()

**Configuration:**

```python
model="claude-opus-4-6"
max_tokens=1000  # Hard cap on output
messages=[
    {"role": "user", "content": prompt}
]
```

**Why Opus 4.6?**

- Best at financial analysis
- Web search capability (fetches current market data)
- High reasoning quality for risk assessment

**Token logging:**

```python
logger.info(f"Tokens input: {message.usage.input_tokens}")
logger.info(f"Tokens output: {message.usage.output_tokens}")
logger.info(f"Coste estimado: ${cost}")
```

**Cost calculation:**

```python
cost = (input_tokens × $5/1M) + (output_tokens × $25/1M)
# Example: (478 × 0.000005) + (319 × 0.000025) = $0.01036
```

**Average output:** 319 tokens (~200 words)

---

## Output Formatting

### clean_for_telegram()

**Removes problematic markdown:**

- `**bold**` → bold
- `*italic*` → italic
- `` `code` `` → code
- `# headers` → headers
- `[links](url)` → links

**Why?** Telegram's markdown parser is strict. Plain text avoids formatting errors.

**Result:** Clean, readable message without broken formatting.

---

## Message Delivery

### send_telegram()

**Adds header:**

```
📊 ANÁLISIS - 18/02/2026 08:00 CET

{Claude's analysis}
```

**API call:**

```python
POST https://api.telegram.org/bot{token}/sendMessage
{
    "chat_id": "5411031813",
    "text": message
}
```

**No parse_mode:** Sends as plain text (avoids markdown errors)

**Error handling:**

- API error → Log to CloudWatch
- Continue execution (analysis still saved to S3)

---

## Logging

### save_results()

**Saves to S3:**

```
logs/daily_analysis_{YYYY-MM-DD}.json
```

**Content:**

```json
{
  "date": "2026-02-18",
  "timestamp": "2026-02-18T08:00:15",
  "portfolio_value": 2670.6,
  "analysis_length": 245,
  "execution": "success"
}
```

**Purpose:** Track execution history, debug issues

**Only in AWS:** Local mode skips this (no S3 write)

---

## Error Handling

### Graceful Degradation

**Scenario 1: yfinance fails**

```python
try:
    stock_data = yf.Ticker(ticker).history()
except Exception as e:
    logger.error(f"Failed to fetch {ticker}: {e}")
    market_data[ticker] = {"error": str(e)}
    # Continue with other tickers
```

**Scenario 2: Claude API error**

```python
try:
    analysis = client.messages.create(...)
except Exception as e:
    logger.error(f"Claude API failed: {e}")
    send_telegram("❌ Analysis failed. Check logs.", config)
    raise e  # Lambda will retry
```

**Scenario 3: Telegram send fails**

```python
try:
    requests.post(telegram_url, json=payload)
except Exception as e:
    logger.error(f"Telegram failed: {e}")
    # Analysis still saved to S3
    # Don't raise exception (partial success ok)
```

---

## Performance Optimization

### Execution Time Breakdown

**Typical 10-15 sec execution:**

- Load config: 0.5 sec
- Load portfolio from S3: 0.3 sec
- Fetch market data (yfinance): 3-5 sec (rate limited)
- Claude API call: 4-6 sec
- Send Telegram: 0.5 sec
- Save logs to S3: 0.2 sec

**Bottlenecks:**

1. yfinance API (can't optimize much)
2. Claude API (quality vs speed tradeoff)

**Memory usage:** 80-120 MB (512 MB allocated)

**Why 512 MB?**

- yfinance needs pandas/numpy
- anthropic SDK overhead
- S3 operations

---

## Testing

### Local Testing (Mock Mode)

```bash
cd ~/projects/trading-bot
source .venv/bin/activate

# Set mock mode in .env
echo "MOCK_CLAUDE=true" >> .env

# Run locally
python3 lambdas/daily_analysis/handler.py
```

**Expected:**

- Loads mock portfolio
- Skips Claude API
- Sends test message to Telegram
- 0 tokens consumed
- ~2 sec execution

### Production Testing

**Lambda console → Test tab → Click "Test"**

**Expected:**

- Real Claude API call
- Real market data
- Real Telegram message
- ~$0.01 cost
- ~10-15 sec execution

---

## Prompt Engineering History

### Version 1 (Initial)

- Input: ~9,000 tokens
- Output: ~15,000 tokens
- Cost: $0.36/execution → $10.80/month
- **Problem:** Too expensive

### Version 2 (Optimized - Current)

- Input: ~478 tokens (95% reduction)
- Output: ~319 tokens (98% reduction)
- Cost: $0.01/execution → $0.30/month
- **Improvements:**
  - Removed verbose instructions
  - Eliminated example outputs
  - Removed market data from prompt (Claude uses web search)
  - Strict word limit (200 words)
  - No tables, no markdown

---

## Future Improvements

**v1.1 (Planned):**

- Incorporate learned patterns from `patterns_learned.json`
- Reference last 30 trades for context
- Adapt analysis based on win rate

**v2.0 (Future):**

- Multi-model approach (Haiku for basic checks, Opus for deep analysis)
- Intraday analysis (2-3 times/day)
- Sentiment analysis from external sources

---

## Monitoring

### CloudWatch Logs

**Log group:** `/aws/lambda/daily-analysis`

**What to monitor:**

- Execution duration (should be <20 sec)
- Token usage trends
- Error rate
- Cost per execution

**Alerts (recommended):**

- Duration >30 sec → Investigate bottleneck
- Error rate >10% → Check API connectivity
- Cost >$0.05 → Prompt optimization needed

---

## Troubleshooting

**"Task timed out"**

- Increase timeout (Configuration → General configuration)
- Current: 60 sec (sufficient)

**"Unable to import module"**

- Handler name incorrect
- Should be: `handler.lambda_handler`

**"KeyError: 'trading_rules'"**

- `config/rules.json` missing in S3
- Upload: `aws s3 cp config/rules.json.example s3://bucket/config/rules.json`

**No Telegram message received**

- Check CloudWatch Logs for send errors
- Verify Parameter Store has correct telegram-token
- Test Telegram API manually: `curl https://api.telegram.org/bot{token}/getMe`

**High token usage**

- Check actual tokens in CloudWatch Logs
- Should be ~478 input, ~319 output
- If higher → prompt may have grown unintentionally

---

## Related Documentation

- [architecture.md](architecture.md) - Overall system design
- [telegram-handler.md](telegram-handler.md) - Command processing
- [costs.md](costs.md) - Detailed cost analysis
- [telegram-commands.md](../usage/telegram-commands.md) - User guide
