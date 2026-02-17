# Arquitectura del Sistema

## Diagrama de Flujo Principal

```
┌──────────────────────────────────────────────────────────────┐
│                     SISTEMA TRADING BOT                      │
└──────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  EventBridge    │  ⏰ 8:00 CET diario
│  daily-trigger  │
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────┐
│  Lambda: daily_analysis                                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 1. Lee S3 (portfolio, histórico, patterns)             │ │
│  │ 2. Lee Parameter Store (API keys)                      │ │
│  │ 3. Web Search (contexto macro, noticias)               │ │
│  │ 4. Claude API Opus 4.6 (análisis completo)             │ │
│  │ 5. Validación anti-FOMO (4 checks)                     │ │
│  │ 6. Calculadora costes (comisiones + impuestos)         │ │
│  │ 7. Gestión riesgo portfolio                            │ │
│  │ 8. Telegram (envío análisis)                           │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────────────────┘
                   │
                   ↓
         ┌─────────────────┐
         │   S3 Bucket     │
         │  trading-data   │
         └─────────────────┘
                   │
                   ↓
         ┌─────────────────┐
         │  Telegram Bot   │
         │  (Usuario)      │
         └─────────────────┘
                   │
         Comandos: /compra, /vende, /portfolio, etc
                   │
                   ↓
┌─────────────────────────────────────────────────────────────┐
│  Lambda: telegram_handler                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 1. Parsea comando                                      │ │
│  │ 2. Valida formato                                      │ │
│  │ 3. Actualiza S3 (current_positions.json)               │ │
│  │ 4. Confirma vía Telegram                               │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  EventBridge    │  ⏰ Día 1 mes, 2:00 CET
│  monthly-trigger│
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────────────────────────┐
│  Lambda: monthly_consolidation                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ 1. Lee S3 (operations_full.csv)                        │ │
│  │ 2. Claude API (análisis mes completo)                  │ │
│  │ 3. Genera patterns_learned.json                        │ │
│  │ 4. Actualiza monthly_performance.json                  │ │
│  │ 5. Ventana deslizante (last_30_trades.json)            │ │
│  │ 6. Archiva ops antiguas (>3 meses)                     │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Servicios AWS Detallados

### Lambda Functions

#### daily_analysis

- **Runtime:** Python 3.12
- **Memoria:** 512 MB
- **Timeout:** 60s
- **Trigger:** EventBridge (cron: `0 7 * * ? *`)
- **Variables entorno:**
  - `S3_BUCKET`: trading-system-data
  - `PARAMETER_PATH`: /trading-bot/
- **Rol IAM:** lambda-trading-bot-role
- **Ejecuciones/mes:** ~30

#### monthly_consolidation

- **Runtime:** Python 3.12
- **Memoria:** 256 MB
- **Timeout:** 120s
- **Trigger:** EventBridge (cron: `0 1 1 * ? *`)
- **Variables entorno:** Igual que daily_analysis
- **Rol IAM:** lambda-trading-bot-role
- **Ejecuciones/mes:** 1

#### telegram_handler

- **Runtime:** Python 3.12
- **Memoria:** 128 MB
- **Timeout:** 30s
- **Trigger:** Polling desde daily_analysis
- **Variables entorno:** Igual que daily_analysis
- **Rol IAM:** lambda-trading-bot-role
- **Ejecuciones/mes:** ~30-50

### S3 Bucket: trading-system-data

**Estructura:**

```
trading-system-data/
├── portfolio/
│   └── current_positions.json
├── history/
│   ├── operations_full.csv
│   └── last_30_trades.json
├── learning/
│   ├── patterns_learned.json
│   └── monthly_performance.json
├── external/
│   ├── zumitow_parsed.json
│   ├── user_tips.json
│   └── tickers_blacklist.txt
└── config/
    └── rules.json
```

**Configuración:**

- Región: eu-west-1 (Irlanda)
- Versionado: Deshabilitado
- Encriptación: SSE-S3 (default)
- Lifecycle: Archivar `history/operations_full.csv` >1 año a Glacier

### Parameter Store (Systems Manager)

**Parámetros:**

```
/trading-bot/claude-api-key      Type: SecureString
/trading-bot/telegram-token      Type: SecureString
/trading-bot/telegram-chat-id    Type: String
```

**Configuración:**

- Región: eu-west-1
- Tier: Standard
- KMS: Default AWS managed key

### EventBridge Rules

**daily-analysis-trigger:**

```
Schedule: cron(0 7 * * ? *)  # 8:00 CET (7:00 UTC)
Target: Lambda daily_analysis
Enabled: Yes
```

**monthly-consolidation-trigger:**

```
Schedule: cron(0 1 1 * ? *)  # 2:00 CET día 1 mes
Target: Lambda monthly_consolidation
Enabled: Yes
```

### IAM Role: lambda-trading-bot-role

**Permisos necesarios:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::trading-system-data",
        "arn:aws:s3:::trading-system-data/*"
      ]
    },
    {
      "Sid": "ParameterStoreAccess",
      "Effect": "Allow",
      "Action": ["ssm:GetParameter", "ssm:GetParameters"],
      "Resource": "arn:aws:ssm:eu-west-1:*:parameter/trading-bot/*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:eu-west-1:*:*"
    }
  ]
}
```

## Flujo de Datos Detallado

### 1. Análisis Matinal (8:00 CET)

**Input:**

- S3: current_positions.json, last_30_trades.json, patterns_learned.json
- Parameter Store: claude-api-key, telegram-token
- Web search: noticias últimas 24h, contexto macro

**Procesamiento:**

1. Contexto macro (Fed, geopolítica, datos económicos)
2. Análisis posiciones actuales (correlaciones, eventos)
3. Validación anti-FOMO (4 checks: técnico, fundamental, sentimiento, timing)
4. Calculadora costes completa (comisiones + spread + divisa + impuestos)
5. Gestión riesgo portfolio (correlación, exposición sectorial)
6. Input externo (Zumitow, tips)
7. Crypto (BTC/ETH)
8. Tracking performance (win rate, patterns)

**Output:**

- Telegram: mensaje análisis formateado
- S3: actualiza datos si cambios
- CloudWatch Logs: métricas ejecución

### 2. Comandos Usuario (vía Telegram)

**Ejemplo: `/compra AAPL 2 180.50`**

**Flujo:**

1. Emvío de comandos → Telegram API
2. daily_analysis polling detecta mensaje
3. Llama telegram_handler
4. Handler parsea: ticker=AAPL, qty=2, price=180.50
5. Valida formato
6. Lee current_positions.json de S3
7. Añade nueva posición
8. Escribe current_positions.json actualizado
9. Responde Telegram: "✅ AAPL: 2 @ 180.50€ registrado"

### 3. Consolidación Mensual (día 1 mes)

**Input:**

- S3: operations_full.csv (todas operaciones)

**Procesamiento:**

1. Lee CSV completo
2. Filtra operaciones mes pasado
3. Claude API: "Analiza estas N operaciones, identifica patterns"
4. Genera insights JSON
5. Calcula métricas agregadas (win rate, sectores, etc)
6. Actualiza ventana deslizante (últimos 30 trades)
7. Archiva operaciones >3 meses

**Output:**

- S3: patterns_learned.json, monthly_performance.json, last_30_trades.json
- CloudWatch Logs: resumen procesamiento

## Optimización Tokens API

### Problema

Histórico crece infinitamente → tokens crecen → coste crece

### Solución: Ventana Deslizante + Agregación

**Análisis diario recibe (tokens fijos):**

```
PORTFOLIO ACTUAL (~200 tokens):
{current_positions.json completo}

ÚLTIMAS 10 OPERACIONES (~500 tokens):
[Detalle completo trades recientes]

PERFORMANCE AGREGADA (~300 tokens):
{
  "total_trades": 120,
  "win_rate": 68%,
  "best_sector": "tech",
  "patterns": ["Entradas pre-market 80% win", ...]
}

MES ACTUAL (~150 tokens):
{trades: 8, return: +3.2%, vs_last: +1.1%}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL: ~1150 tokens (NO CRECE)
```

**Consolidación mensual:**

- Analiza mes completo (puede usar 5K tokens)
- Genera insights compactos (300 tokens)
- Próximo mes: usa insights, no raw data

**Resultado:** Coste estable ~1.5€/mes indefinidamente

## Seguridad

### Secrets Management

- API keys en Parameter Store (SecureString)
- .gitignore excluye credenciales

### IAM Least Privilege

- Lambda solo accede S3 bucket específico
- Solo lee parámetros /trading-bot/\*
- No permisos delete/modify config

### Telegram Bot

- Token guardado seguro
- Solo responde a tu chat_id
- Comandos validados antes ejecutar

### Billing Alerts

- Alerta $1, $3, $5/mes
- CloudWatch alarm si Lambda errors >5%
- Email notificación automática

## Monitoring

### CloudWatch Metrics

- Lambda invocations/día
- Lambda errors/día
- Lambda duration average
- S3 PUT/GET operations

### CloudWatch Logs

- Cada ejecución Lambda loguea:
  - Timestamp inicio/fin
  - Portfolio estado
  - Decisiones tomadas
  - Errores si aplica

### Alertas

- Error rate >10% → Email
- Ejecución >50s → Email (cerca timeout)
- Coste AWS >$3/mes → Email

## Escalabilidad Futura

### v2.0 Posibles Mejoras

**Alertas Intraday:**

- Lambda adicional cada 2h
- Solo ejecuta si evento crítico
- +1€/mes coste

**API Trade Republic:**

- Lectura portfolio automática
- Sin actualización manual
- Requiere pytr (no oficial)

**CI/CD GitHub Actions:**

- Deploy automático merge a main
- Testing automatizado
- Rollback si falla

**Dashboard Web:**

- S3 static website
- Visualización portfolio
- Gráficos performance
- CloudFront CDN
