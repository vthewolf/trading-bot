# Telegram Commands Reference

Complete guide to all available bot commands with examples.

## Quick Reference

| Command             | Purpose              | Example                       |
| ------------------- | -------------------- | ----------------------------- |
| `/help`             | Show all commands    | `/help`                       |
| `/compro`           | Register buy         | `/compro AAPL 2 180.50`       |
| `/vendo`            | Register sell        | `/vendo AAPL 2 195.00`        |
| `/portfolio`        | View positions       | `/portfolio`                  |
| `/balance`          | Financial summary    | `/balance`                    |
| `/stats`            | Trading statistics   | `/stats`                      |
| `/blacklist`        | Block ticker         | `/blacklist PLTR`             |
| `/blacklists`       | View blocked tickers | `/blacklists`                 |
| `/remove_blacklist` | Unblock ticker       | `/remove_blacklist PLTR`      |
| `/tip`              | Add insight          | `/tip NVDA Earnings próximos` |
| `/tips`             | View active tips     | `/tips`                       |
| `/remove_tip`       | Remove tip           | `/remove_tip NVDA`            |
| `/run`              | Manual analysis      | `/run`                        |

---

## Portfolio Management

### /compro - Register Purchase

**Format:**

```
/compro TICKER CANTIDAD PRECIO
```

**Parameters:**

- `TICKER` - Stock symbol (e.g., AAPL, MSFT, GOOGL)
- `CANTIDAD` - Number of shares (decimals allowed)
- `PRECIO` - Purchase price in euros (€)

**Examples:**

**Buy 2 shares of Apple at 180.50€:**

```
/compro AAPL 2 180.50
```

**Response:**

```
✅ Compra registrada
AAPL: 2 acc @ 180.50€
Efectivo restante: 1938.00€
```

**Buy fractional shares:**

```
/compro MSFT 0.5 350.00
```

**Add to existing position:**

```
/compro AAPL 1 185.00
```

**Response:**

```
✅ Posición ampliada
AAPL: 3 acc @ 182.00€ (precio medio)
Efectivo restante: 1753.00€
```

**Notes:**

- Automatically calculates weighted average price when adding to existing position
- Deducts cash (purchase price × quantity + 1€ commission)
- Price must be in euros (Trade Republic shows prices in EUR)

---

### /vendo - Register Sale

**Format:**

```
/vendo TICKER CANTIDAD PRECIO
```

**Parameters:**

- `TICKER` - Stock symbol
- `CANTIDAD` - Number of shares to sell
- `PRECIO` - Sale price in euros (€)

**Examples:**

**Sell 2 shares of Apple at 195€:**

```
/vendo AAPL 2 195.00
```

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

**Partial close:**

```
/vendo AAPL 1 195.00
```

**Response:**

```
📈 Venta registrada (parcial)
AAPL: 1 acc @ 195.00€
...
```

**P&L Calculation breakdown:**

1. **Gross P&L:** (Exit price - Entry price) × Quantity
2. **Costs:** 2€ (1€ entry commission + 1€ exit commission)
3. **Net before tax:** Gross P&L - Costs
4. **Tax (19%):** Only if profit (Spain capital gains tax)
5. **Net P&L:** Net before tax - Tax

**Notes:**

- Cannot sell more shares than you own
- Automatically removes position if fully closed
- Records trade in history for statistics
- Updates cash balance

---

### /portfolio - View Positions

**Format:**

```
/portfolio
```

**No parameters needed.**

**Example response (with positions):**

```
💼 PORTFOLIO

AAPL: 2 acc @ 180.50€
Invertido: 361.00€
Desde: 2026-02-15

MSFT: 1 acc @ 350.00€
Invertido: 350.00€
Desde: 2026-02-16

Total invertido: 711.00€
Efectivo: 1588.00€
Total portfolio: 2299.00€
```

**Example response (no positions):**

```
💼 PORTFOLIO

Sin posiciones abiertas
Efectivo: 2300.00€
```

**Shows:**

- Each open position (ticker, quantity, entry price)
- Amount invested per position
- Date position opened
- Total invested across all positions
- Available cash
- Total portfolio value

**Note:** Does not show current prices or unrealized P&L (check daily analysis for that)

---

### /balance - Financial Summary

**Format:**

```
/balance
```

**Example response:**

```
💰 BALANCE

Capital actual: 2320.87€
  Efectivo: 1959.87€
  Invertido: 361.00€

P&L realizado: 21.87€
Operaciones cerradas: 1
Win rate: 100.0%
```

**Shows:**

- Current total capital
- Cash breakdown
- Amount currently invested
- Realized P&L (from closed trades only)
- Number of completed trades
- Win rate (% of profitable trades)

**Difference from /portfolio:**

- Portfolio shows open positions
- Balance shows overall financial performance

---

### /stats - Trading Statistics

**Format:**

```
/stats
```

**Example response:**

```
📊 STATS

Total operaciones: 5
Win rate: 80.0% (4W / 1L)
P&L total neto: 145.23€

Mejor trade: AAPL +45.87€ (+12.3%)
Peor trade: TSLA -12.45€ (-5.2%)
```

**Shows:**

- Total completed trades
- Win rate (wins vs losses)
- Total realized P&L
- Best trade (highest profit)
- Worst trade (biggest loss)

**Available after:** First completed trade (requires at least 1 /vendo)

**Before first trade:**

```
📊 STATS

Sin operaciones cerradas aún.
Las estadísticas aparecerán tras tu primera venta.
```

---

## Configuration

### /blacklist - Block Ticker

**Format:**

```
/blacklist TICKER
```

**Purpose:** Mark ticker as unavailable in your broker (Trade Republic)

**Example:**

```
/blacklist PLTR
```

**Response:**

```
✅ PLTR añadido a blacklist
No se recomendará en futuros análisis
```

**Use cases:**

- Ticker not available in Trade Republic
- Stock you don't want to trade (personal reasons)
- Already analyzed and rejected

**Effect:** Daily analysis will skip this ticker in recommendations

---

### /blacklists - View Blacklist

**Format:**

```
/blacklists
```

**Example response:**

```
🚫 BLACKLIST

PLTR
TSLA
GME
```

**Empty blacklist:**

```
🚫 BLACKLIST

Sin tickers bloqueados.
```

---

### /remove_blacklist - Unblock Ticker

**Format:**

```
/remove_blacklist TICKER
```

**Example:**

```
/remove_blacklist PLTR
```

**Response:**

```
✅ PLTR eliminado de blacklist
Claude puede volver a recomendarlo
```

**Use case:** Ticker becomes available in broker, or you change your mind

---

### /tip - Add External Insight

**Format:**

```
/tip TICKER RAZÓN
```

**Purpose:** Add external information for daily analysis to consider

**Examples:**

**Friend's recommendation:**

```
/tip NVDA Amigo dice que presentan nueva GPU
```

**News you saw:**

```
/tip AAPL Earnings report próxima semana
```

**Social media insight:**

```
/tip TSLA Rumores de nueva fábrica en Europa
```

**Response:**

```
✅ Tip añadido
NVDA: Amigo dice que presentan nueva GPU
Se analizará en el próximo análisis
```

**Effect:**

- Stored in S3 (`external/user_tips.json`)
- Daily analysis will consider this context
- Claude validates if insight is actionable

**Note:** Tips persist until you remove them manually

---

### /tips - View Active Tips

**Format:**

```
/tips
```

**Example response:**

```
💡 TIPS ACTIVOS

NVDA: Amigo dice que presentan nueva GPU
Añadido: 2026-02-18

AAPL: Earnings report próxima semana
Añadido: 2026-02-17
```

**Empty tips:**

```
💡 TIPS ACTIVOS

Sin tips pendientes.
```

---

### /remove_tip - Remove Tip

**Format:**

```
/remove_tip TICKER
```

**Example:**

```
/remove_tip NVDA
```

**Response:**

```
✅ Tip de NVDA eliminado
```

**Use case:** Insight no longer relevant (event passed, changed mind)

---

## System

### /run - Manual Analysis

**Format:**

```
/run
```

**Purpose:** Trigger daily analysis immediately (don't wait until 8 AM)

**Example:**

```
/run
```

**Response:**

```
⚡ Análisis lanzado
Recibirás el resultado en unos segundos
```

**Use cases:**

- Breaking news (Fed announcement, major event)
- Want fresh analysis before market close
- Testing after configuration changes

**Note:** Consumes tokens (~$0.01 per execution)

**In local environment:**

```
⚠️ /run solo funciona en AWS
En local ejecuta: python3 lambdas/daily_analysis/handler.py
```

---

### /help - Show Commands

**Format:**

```
/help
```

**Shows:** Complete list of all available commands with examples

**No parameters needed.**

---

## Command Tips

### General Rules

✅ **Case insensitive:** `/COMPRO` = `/compro` = `/Compro`

✅ **Space-separated:** Use spaces between parameters

✅ **Ticker format:** Use standard symbols (AAPL, not Apple Inc.)

❌ **No commas:** Use `180.50` not `180,50`

❌ **No currency symbols:** Use `180.50` not `€180.50`

### Common Mistakes

**Wrong:**

```
/compro AAPL,2,180.50    ❌ (commas)
/compro AAPL 2 €180.50   ❌ (currency symbol)
/compro aapl2180.50      ❌ (no spaces)
```

**Correct:**

```
/compro AAPL 2 180.50    ✅
```

---

## Automated Messages

### Daily Analysis (8:00 AM)

**You'll receive automatically:**

```
📊 ANÁLISIS - 18/02/2026 08:00 CET

🌍 MACRO: MEDIO
Fed mantiene tipos. Cautela moderada.

💼 POSICIONES
AAPL: MANTENER - Tendencia alcista sólida

🎯 OPORTUNIDADES
Ninguna pasa 4/4 checks hoy.

₿ CRYPTO
BTC: VIGILAR - Consolidación
ETH: ESPERAR - Sin catalizador

✅ RESUMEN
Hoy mantener posiciones. Sin entradas nuevas.
Riesgo: MEDIO
```

**No action needed:** Just read and decide

**If you want analysis now:** Use `/run`

---

## Workflow Examples

### Example 1: Opening First Position

```
1. /portfolio
   → See available cash: 2300€

2. /compro AAPL 2 180.50
   → Confirm purchase registered

3. /portfolio
   → Verify position appears

4. Next day 8 AM: Receive analysis with AAPL recommendation
```

---

### Example 2: Closing Profitable Trade

```
1. Check daily analysis: "AAPL: VENDER - Target alcanzado"

2. /vendo AAPL 2 195.00
   → See P&L breakdown

3. /balance
   → Verify profit added to realized P&L

4. /stats
   → See updated win rate
```

---

### Example 3: Managing Blacklist

```
1. Daily analysis recommends PLTR

2. Check Trade Republic → PLTR not available

3. /blacklist PLTR
   → Prevent future recommendations

4. Next day: No PLTR in analysis

5. Later: PLTR becomes available

6. /remove_blacklist PLTR
   → Allow recommendations again
```

---

### Example 4: Adding External Insight

```
1. Friend: "NVDA earnings look great"

2. /tip NVDA Amigo dice earnings positivos

3. Next day 8 AM: Analysis considers this context

4. After earnings: /remove_tip NVDA
```

---

## Troubleshooting

**Command not recognized:**

- Check spelling: `/help` not `/ayuda`
- Start with `/` (forward slash)

**"Formato incorrecto":**

- Count parameters: `/compro TICKER CANTIDAD PRECIO` (3 parameters)
- Use spaces to separate
- No commas or extra symbols

**"No tienes X en portfolio":**

- Verify ticker with `/portfolio`
- Check spelling (case-insensitive but must match)

**No response from bot:**

- Check internet connection
- Bot might be updating (rare, <1 min)
- Try again in 30 seconds

---

## Next Steps

**Configure your rules:**
→ [trading-rules.md](trading-rules.md) - Customize stop-loss, targets, and more

**Understand the system:**
→ [../technical/telegram-handler.md](../technical/telegram-handler.md) - How commands work internally

**Daily analysis details:**
→ [../technical/daily-analysis.md](../technical/daily-analysis.md) - How analysis is generated
