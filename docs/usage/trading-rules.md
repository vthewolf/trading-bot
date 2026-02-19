# Trading Rules Configuration

How to configure and customize your trading rules.

## Rules File Location

**S3:** `s3://trading-bot-data-victor/config/rules.json`

**Local template:** `config/rules.json.example`

---

## Default Configuration

```json
{
  "trading_rules": {
    "stop_loss_percent": -10,
    "target_profit_percent": 20,
    "max_positions": 3,
    "min_cash_reserve_eur": 500,
    "max_position_size_eur": 800
  },
  "broker_costs": {
    "commission_per_trade_eur": 1,
    "spread_percent": 0.1
  },
  "tax_rules_spain": {
    "capital_gains_tax_percent": 19
  }
}
```

---

## Trading Rules

### stop_loss_percent

**Default:** `-10`

**What it means:** Sell if position loses 10%

**Example:**

- Buy AAPL at 100€
- Stop-loss triggers at 90€
- Protects from larger losses

**How to change:**

```bash
# Edit rules.json.example locally
# Upload to S3
aws s3 cp config/rules.json.example s3://trading-bot-data-victor/config/rules.json
```

**Conservative:** `-5` (tighter stop)
**Aggressive:** `-15` (more room for volatility)

---

### target_profit_percent

**Default:** `20`

**What it means:** Consider selling when position gains 20%

**Example:**

- Buy AAPL at 100€
- Target reached at 120€
- Daily analysis suggests selling

**Conservative:** `15` (take profits earlier)
**Aggressive:** `30` (let winners run)

---

### max_positions

**Default:** `3`

**What it means:** Maximum open positions at once

**Why limit?**

- Diversification (don't put all eggs in one basket)
- Risk management
- Easier to monitor

**Small portfolio:** `2-3`
**Larger capital:** `5-8`

---

### min_cash_reserve_eur

**Default:** `500`

**What it means:** Always keep 500€ in cash

**Why?**

- Emergency liquidity
- Opportunity fund (buy dips)
- Never fully invested

**Adjust to:** 20-30% of total capital

---

### max_position_size_eur

**Default:** `800`

**What it means:** Never invest more than 800€ in single position

**Why?**

- Position sizing
- Risk per trade
- Prevents overconcentration

**Formula:** Max position = Total capital × 30-40%

---

## Broker Costs

### commission_per_trade_eur

**Default:** `1`

**Trade Republic:** 1€ per trade (buy or sell)

**Used in P&L calculations:**

- Buy: Price × Quantity + 1€
- Sell: Price × Quantity - 1€
- Total trade cost: 2€

**Do not change** unless broker changes fees.

---

### spread_percent

**Default:** `0.1`

**What it is:** Bid-ask spread cost

**Example:**

- Bid: 100.00€
- Ask: 100.10€
- Spread: 0.1%

**Trade Republic:** Minimal spreads (0.05-0.15%)

**Used for:** Cost estimation in analysis

---

## Tax Rules (Spain)

### capital_gains_tax_percent

**Default:** `19`

**Spain tax rates:**

- Up to 6,000€: 19%
- 6,000€ - 50,000€: 21%
- 50,000€ - 200,000€: 23%
- Above 200,000€: 26%

**Default assumes:** Most trades under 6,000€

**Adjust if:** You expect larger gains

**Applied in:** `/vendo` command automatically

---

## How to Update Rules

### Step 1: Edit Locally

```bash
cd ~/projects/trading-bot
nano config/rules.json.example
```

**Change values:**

```json
{
  "trading_rules": {
    "stop_loss_percent": -12,
    "target_profit_percent": 25
  }
}
```

---

### Step 2: Upload to S3

```bash
BUCKET="trading-bot-data-victor"
aws s3 cp config/rules.json.example s3://${BUCKET}/config/rules.json
```

---

### Step 3: Verify

**Next daily analysis (8 AM) will use new rules.**

**Test immediately:**

```
/run
```

Check analysis mentions new stop-loss/target values.

---

## Rule Combinations

### Conservative Profile

```json
{
  "stop_loss_percent": -5,
  "target_profit_percent": 15,
  "max_positions": 2,
  "min_cash_reserve_eur": 800,
  "max_position_size_eur": 600
}
```

**Who:** Risk-averse, capital preservation
**Goal:** Steady, small gains

---

### Balanced Profile (Default)

```json
{
  "stop_loss_percent": -10,
  "target_profit_percent": 20,
  "max_positions": 3,
  "min_cash_reserve_eur": 500,
  "max_position_size_eur": 800
}
```

**Who:** Moderate risk tolerance
**Goal:** Growth with protection

---

### Aggressive Profile

```json
{
  "stop_loss_percent": -15,
  "target_profit_percent": 30,
  "max_positions": 5,
  "min_cash_reserve_eur": 300,
  "max_position_size_eur": 1000
}
```

**Who:** High risk tolerance, active trading
**Goal:** Maximum growth

---

## Rules in Daily Analysis

**How Claude uses rules:**

1. **Stop-loss check:** Recommends selling if position down >10%
2. **Target check:** Suggests taking profits if up >20%
3. **Position limit:** Won't recommend new entry if at max positions
4. **Cash reserve:** Won't suggest entry if it breaks minimum cash
5. **Position size:** Limits recommendation amounts

**Example analysis:**

```
💼 POSICIONES
AAPL: VENDER - Stop-loss alcanzado (-12%)
MSFT: MANTENER - Dentro de rango

🎯 OPORTUNIDADES
No recomendar entrada - Ya tienes 3 posiciones (máximo)
```

---

## Advanced: Custom Rules

**Future enhancement ideas:**

**Time-based rules:**

```json
{
  "no_trade_before_fomc": true,
  "no_trade_friday_pm": true
}
```

**Sector limits:**

```json
{
  "max_tech_exposure_percent": 60
}
```

**Volatility-based:**

```json
{
  "pause_if_vix_above": 30
}
```

**Not implemented yet - v2.0 feature**

---

## Troubleshooting

**Rules not applying:**

- Verify file uploaded to S3: `aws s3 ls s3://bucket/config/`
- Check JSON syntax: https://jsonlint.com/
- Wait for next analysis (8 AM) or use `/run`

**Analysis ignoring rules:**

- Check CloudWatch Logs for "KeyError: trading_rules"
- Verify rules.json structure matches template

---

## Related

- [telegram-commands.md](telegram-commands.md) - Command reference
- [daily-analysis.md](../technical/daily-analysis.md) - How analysis uses rules
