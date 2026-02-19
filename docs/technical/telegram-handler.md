# Telegram Handler Lambda

Deep dive into command processing and portfolio management.

## Overview

**Function:** `telegram-handler`

**Purpose:** Process Telegram commands and manage portfolio state

**Trigger:** API Gateway webhook (instant on user message)

**Runtime:** Python 3.12

**Average Duration:** 2-5 seconds

**Cost:** $0.00 (within Free Tier)

---

## Execution Flow

```
User sends /command
    ↓
Telegram → API Gateway webhook
    ↓
Lambda receives event
    ↓
Parse command from webhook body
    ↓
Load configuration (Parameter Store)
    ↓
Process command (read/write S3)
    ↓
Format response
    ↓
Send to Telegram
    ↓
Lambda ends
```

---

## Code Structure

### Main Handler

**File:** `lambdas/telegram_handler/handler.py`

**Entry point:** `lambda_handler(event, context)`

**Core functions:**

- `get_config()` - Load secrets
- `process_command()` - Route commands
- `cmd_*()` - Individual command handlers (13 total)
- S3 helpers (load/save JSON and text)
- Telegram helpers (send messages)

---

## Webhook Event Structure

### What Lambda Receives

**event from API Gateway:**

```python
{
    "body": '{"message":{"text":"/portfolio","chat":{"id":5411031813}}}'
}
```

**Parsed:**

```python
body = json.loads(event["body"])
message = body["message"]
text = message["text"]  # "/portfolio"
chat_id = message["chat"]["id"]  # 5411031813
```

**Why webhook vs polling?**

- Instant response (no delay)
- Lower cost (only runs when needed)
- More secure (Telegram calls us, we don't store messages)

---

## Command Processing

### process_command()

**Router function - dispatches to specific handlers:**

```python
command = parts[0].lower()  # "/portfolio" → "/portfolio"

if command == "/help":
    return cmd_help()
elif command == "/compro":
    return cmd_compro(parts, s3, config)
elif command == "/vendo":
    return cmd_vendo(parts, s3, config)
# ... etc
```

**Parts splitting:**

```python
text = "/compro AAPL 2 180.50"
parts = text.split()  # ["/compro", "AAPL", "2", "180.50"]
```

---

## Command Handlers

### 1. cmd_help()

**Purpose:** Display all available commands

**No S3 access:** Returns static text

**Output:** Full command reference (~400 chars)

**Usage:** `/help`

---

### 2. cmd_compro()

**Purpose:** Register stock purchase

**S3 reads:**

- `portfolio/current_positions.json`

**S3 writes:**

- `portfolio/current_positions.json` (updated)

**Logic:**

```python
# Parse command
ticker = parts[1].upper()  # "AAPL"
quantity = float(parts[2])  # 2.0
price = float(parts[3])  # 180.50

# Load portfolio
portfolio = load_s3_json(s3, bucket, "portfolio/current_positions.json")

# Check if position exists
existing = next((p for p in portfolio["positions"] if p["ticker"] == ticker), None)

if existing:
    # Update existing position (weighted average price)
    total_qty = existing["quantity"] + quantity
    avg_price = ((existing["quantity"] * existing["entry_price"]) + (quantity * price)) / total_qty
    existing["quantity"] = total_qty
    existing["entry_price"] = round(avg_price, 2)
else:
    # Add new position
    portfolio["positions"].append({
        "ticker": ticker,
        "quantity": quantity,
        "entry_price": price,
        "date_open": datetime.now().strftime("%Y-%m-%d")
    })

# Deduct cash (including 1€ commission)
cost = quantity * price + 1
portfolio["cash_eur"] -= cost

# Save to S3
save_s3_json(s3, bucket, "portfolio/current_positions.json", portfolio)
```

**Usage:** `/compro AAPL 2 180.50`

**Response:**

```
✅ Compra registrada
AAPL: 2 acc @ 180.50€
Efectivo restante: 1938.00€
```

**Or if adding to existing:**

```
✅ Posición ampliada
AAPL: 4 acc @ 182.25€ (precio medio)
Efectivo restante: 1577.00€
```

---

### 3. cmd_vendo()

**Purpose:** Register stock sale and calculate P&L

**S3 reads:**

- `portfolio/current_positions.json`

**S3 writes:**

- `portfolio/current_positions.json` (updated/position removed)
- `history/operations_full.csv` (append trade)

**Logic:**

```python
# Parse command
ticker = parts[1].upper()
quantity = float(parts[2])
price = float(parts[3])

# Load portfolio
portfolio = load_s3_json(...)
position = next((p for p in portfolio["positions"] if p["ticker"] == ticker), None)

# Validate
if not position:
    return f"❌ No tienes {ticker} en portfolio"
if quantity > position["quantity"]:
    return f"❌ Solo tienes {position['quantity']} acciones"

# Calculate P&L
entry_price = position["entry_price"]
gross_pnl = (price - entry_price) * quantity
costs = 2  # 1€ entry + 1€ exit commission
net_before_tax = gross_pnl - costs
tax = max(0, net_before_tax * 0.19)  # Only if profit
net_pnl = net_before_tax - tax
pnl_pct = ((price - entry_price) / entry_price) * 100

# Update portfolio
if quantity == position["quantity"]:
    portfolio["positions"].remove(position)  # Full close
else:
    position["quantity"] -= quantity  # Partial close

# Add cash
proceeds = quantity * price - 1  # -1€ commission
portfolio["cash_eur"] += proceeds

# Save portfolio
save_s3_json(...)

# Append to history CSV
trade = {
    "ticker": ticker,
    "quantity": quantity,
    "entry_price": entry_price,
    "exit_price": price,
    "date_close": datetime.now().strftime("%Y-%m-%d"),
    "gross_pnl": gross_pnl,
    "net_pnl": net_pnl,
    "pnl_pct": pnl_pct,
    "result": "win" if net_pnl > 0 else "loss"
}
save_trade_to_history(s3, bucket, trade)
```

**Usage:** `/vendo AAPL 2 195.00`

**Response:**

```
📈 Venta registrada (cerrada)
AAPL: 2 acc @ 195.00€

Entrada: 180.50€
Salida: 195.00€
P&L bruto: 29.00€ (+8.03%)
Costes: -2€
Impuestos (19%): -5.13€
P&L NETO: 21.87€

Efectivo: 2325.87€
```

---

### 4. cmd_portfolio()

**Purpose:** Show current positions and P&L (unrealized)

**S3 reads:**

- `portfolio/current_positions.json`

**S3 writes:** None

**Logic:**

```python
portfolio = load_s3_json(...)
positions = portfolio.get("positions", [])

if not positions:
    return "💼 PORTFOLIO\n\nSin posiciones abiertas\nEfectivo: 2300€"

# Build message
msg = "💼 PORTFOLIO\n\n"
total_invested = 0

for p in positions:
    invested = p["quantity"] * p["entry_price"]
    total_invested += invested
    msg += f"{p['ticker']}: {p['quantity']} acc @ {p['entry_price']}€\n"
    msg += f"Invertido: {invested}€\n"
    msg += f"Desde: {p['date_open']}\n\n"

msg += f"Total invertido: {total_invested}€\n"
msg += f"Efectivo: {portfolio['cash_eur']}€\n"
msg += f"Total portfolio: {total_invested + portfolio['cash_eur']}€"
```

**Usage:** `/portfolio`

**Response:**

```
💼 PORTFOLIO

AAPL: 2 acc @ 180.50€
Invertido: 361.00€
Desde: 2026-02-15

Total invertido: 361.00€
Efectivo: 1938.00€
Total portfolio: 2299.00€
```

---

### 5. cmd_balance()

**Purpose:** Financial summary with realized P&L

**S3 reads:**

- `portfolio/current_positions.json`
- `history/operations_full.csv`

**S3 writes:** None

**Logic:**

```python
portfolio = load_s3_json(...)
csv_text = load_s3_text(s3, bucket, "history/operations_full.csv")

# Parse CSV
total_net_pnl = 0
total_trades = 0
wins = 0

for line in csv_text.split("\n")[1:]:  # Skip header
    parts = line.split(",")
    net_pnl = float(parts[6])
    result = parts[8]
    total_net_pnl += net_pnl
    total_trades += 1
    if result == "win":
        wins += 1

# Calculate totals
cash = portfolio["cash_eur"]
invested = sum(p["quantity"] * p["entry_price"] for p in portfolio["positions"])
total_value = cash + invested
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
```

**Usage:** `/balance`

**Response:**

```
💰 BALANCE

Capital actual: 2320.87€
  Efectivo: 1959.87€
  Invertido: 361.00€

P&L realizado: 21.87€
Operaciones cerradas: 1
Win rate: 100.0%
```

---

### 6. cmd_stats()

**Purpose:** Detailed trading statistics

**S3 reads:**

- `history/operations_full.csv`

**S3 writes:** None

**Logic:**

```python
# Parse all trades
trades = []
for line in csv_text.split("\n")[1:]:
    trades.append({
        "ticker": parts[0],
        "net_pnl": float(parts[6]),
        "pnl_pct": float(parts[7]),
        "result": parts[8]
    })

# Calculate stats
wins = [t for t in trades if t["result"] == "win"]
losses = [t for t in trades if t["result"] == "loss"]
win_rate = len(wins) / len(trades) * 100

best = max(trades, key=lambda x: x["net_pnl"])
worst = min(trades, key=lambda x: x["net_pnl"])
total_pnl = sum(t["net_pnl"] for t in trades)
```

**Usage:** `/stats`

**Response:**

```
📊 STATS

Total operaciones: 3
Win rate: 66.7% (2W / 1L)
P&L total neto: 45.23€

Mejor trade: AAPL +21.87€ (+8.03%)
Peor trade: TSLA -12.45€ (-5.2%)
```

---

### 7. cmd_blacklist()

**Purpose:** Add ticker to blacklist (unavailable in broker)

**S3 reads:**

- `external/tickers_blacklist.txt`

**S3 writes:**

- `external/tickers_blacklist.txt` (updated)

**Logic:**

```python
ticker = parts[1].upper()

current = load_s3_text(s3, bucket, "external/tickers_blacklist.txt")
tickers = [t.strip() for t in current.split("\n") if t.strip()]

if ticker in tickers:
    return f"⚠️ {ticker} ya está en blacklist"

tickers.append(ticker)
save_s3_text(s3, bucket, "external/tickers_blacklist.txt", "\n".join(tickers))
```

**Usage:** `/blacklist PLTR`

**Response:**

```
✅ PLTR añadido a blacklist
No se recomendará en futuros análisis
```

---

### 8-13. Other Commands

**cmd_remove_blacklist()** - Remove from blacklist

**cmd_blacklists()** - View all blacklisted tickers

**cmd_tip()** - Add external insight

```python
# Stores in external/user_tips.json
{
    "ticker": "NVDA",
    "context": "Amigo dice que presentan GPU",
    "date": "2026-02-18",
    "source": "user"
}
```

**cmd_tips()** - View active tips

**cmd_remove_tip()** - Remove tip

**cmd_run()** - Trigger daily analysis manually

```python
# Invokes daily-analysis Lambda asynchronously
lambda_client.invoke(
    FunctionName="daily-analysis",
    InvocationType="Event"  # Fire and forget
)
```

---

## S3 Operations

### JSON Files

**Read:**

```python
def load_s3_json(s3_client, bucket, key, default=None):
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except:
        return default if default else {}
```

**Write:**

```python
def save_s3_json(s3_client, bucket, key, data):
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(data, indent=2, ensure_ascii=False),
        ContentType="application/json"
    )
```

### Text Files

**Read:**

```python
def load_s3_text(s3_client, bucket, key):
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    except:
        return ""
```

**Write:**

```python
def save_s3_text(s3_client, bucket, key, text):
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=text.encode("utf-8"),
        ContentType="text/plain"
    )
```

---

## Error Handling

### Input Validation

**Format errors:**

```python
if len(parts) != 4:
    return "❌ Formato incorrecto\nUso: /compro TICKER CANTIDAD PRECIO"

try:
    quantity = float(parts[2])
    price = float(parts[3])
except ValueError:
    return "❌ Cantidad y precio deben ser números"
```

**Business logic errors:**

```python
if ticker not in portfolio["positions"]:
    return f"❌ No tienes {ticker} en portfolio"

if quantity > position["quantity"]:
    return f"❌ Solo tienes {position['quantity']} acciones"
```

### S3 Errors

**Handled gracefully:**

```python
try:
    portfolio = load_s3_json(...)
except Exception as e:
    logger.error(f"Failed to load portfolio: {e}")
    return "❌ Error cargando datos. Intenta de nuevo."
```

### Telegram Errors

**Non-blocking:**

```python
try:
    requests.post(telegram_url, json=payload)
except Exception as e:
    logger.error(f"Telegram send failed: {e}")
    # Don't raise - Lambda shouldn't fail if Telegram is down
```

---

## Performance

### Execution Time

**By command type:**

- `/help`: <1 sec (no S3)
- `/portfolio`, `/balance`, `/stats`: 1-2 sec (S3 reads only)
- `/compro`, `/vendo`: 2-3 sec (S3 read + write)
- `/run`: <1 sec (Lambda invoke, async)

**Memory usage:** 60-90 MB (256 MB allocated)

**Why 256 MB?**

- Lighter workload than daily-analysis
- No yfinance, no Claude API
- Just S3 operations and JSON parsing

---

## Concurrency & Rate Limiting

### Webhook Configuration

```bash
"max_connections": 1
```

**Effect:** Only 1 command processed at a time

**Why?**

- Prevents race conditions on portfolio updates
- Avoids overwhelming Lambda
- User sends commands sequentially anyway

### Telegram Limits

**Bot API limits:**

- 30 messages/second per bot (we send ~1/minute max)
- No risk of hitting limits

---

## Testing

### Local Testing

```bash
cd ~/projects/trading-bot
source .venv/bin/activate

# Simulate webhook event
python3 lambdas/telegram_handler/handler.py
```

**Mock event in `__main__`:**

```python
mock_event = {
    "body": json.dumps({
        "message": {
            "text": "/help",
            "chat": {"id": int(os.getenv("TELEGRAM_CHAT_ID"))}
        }
    })
}
```

### Lambda Testing

**Lambda console → Test tab**

**Event JSON:**

```json
{
  "body": "{\"message\":{\"text\":\"/portfolio\",\"chat\":{\"id\":5411031813}}}"
}
```

**Expected:** 200 OK + Telegram message received

---

## Security

### Input Sanitization

**Ticker validation:**

```python
ticker = parts[1].upper()
# Only alphanumeric allowed (implicit via yfinance later)
```

**Amount validation:**

```python
quantity = float(parts[2])
if quantity <= 0:
    return "❌ Cantidad debe ser positiva"
```

**No SQL injection risk:** Using S3 JSON/CSV, not database

**No command injection:** Not executing shell commands

### Access Control

**Webhook verification:**

- Telegram verifies webhook authenticity
- Only messages from your bot reach Lambda

**No authentication needed:**

- Bot only responds to your chat_id
- Lambda checks chat_id matches Parameter Store value (future improvement)

---

## Monitoring

### CloudWatch Logs

**Log group:** `/aws/lambda/telegram-handler`

**Key metrics:**

- Command frequency (which commands used most)
- Execution duration per command
- Error rate by command type
- S3 operation success/failure

### Useful Log Queries

**CloudWatch Insights:**

**Most used commands:**

```
fields @timestamp, @message
| filter @message like /Comando recibido:/
| stats count() by @message
```

**Failed executions:**

```
fields @timestamp, @message
| filter @message like /ERROR/
```

---

## Future Improvements

**v1.1:**

- Chat ID validation (reject messages from other users)
- `/edit` command to modify existing position
- `/history TICKER` to show trade history for specific ticker

**v2.0:**

- Rich formatting (buttons, inline keyboards)
- Photo responses (charts of portfolio performance)
- Multiple users support (multi-tenant)

---

## Troubleshooting

**"Task timed out after 3.00 seconds"**

- Increase timeout to 30 sec
- Configuration → General configuration → Edit

**"Unable to import module 'lambda_function'"**

- Handler incorrect
- Should be: `handler.lambda_handler`

**Portfolio updates not persisting**

- Check S3 write permissions (lambda-trading-bot-role)
- Check CloudWatch Logs for S3 errors

**Commands not responding**

- Verify webhook: `curl https://api.telegram.org/bot{token}/getWebhookInfo`
- Check API Gateway logs (if enabled)
- Check Lambda is being invoked (CloudWatch Logs)

**Incorrect P&L calculations**

- Verify commission amounts (1€ per trade)
- Verify tax rate (19% Spain)
- Check weighted average formula for position additions

---

## Related Documentation

- [architecture.md](architecture.md) - Overall system design
- [daily-analysis.md](daily-analysis.md) - Automated analysis
- [telegram-commands.md](../usage/telegram-commands.md) - User guide
- [costs.md](costs.md) - Cost breakdown
