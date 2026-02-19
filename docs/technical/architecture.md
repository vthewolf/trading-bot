# System Architecture

Complete architecture overview, data flow, and service interactions.

## Architecture Diagram

![Architecture Diagram](../images/architecture-diagram.png)

**Create this diagram using:** https://app.diagrams.net/

### Diagram Components:

**Services:**

- EventBridge
- Lambda (λ) - 2 functions
- S3
- Parameter Store
- API Gateway
- CloudWatch Logs

**External:**

- Claude API
- Telegram
- User

### Diagram Flow Description:

**Daily Analysis (Automated):**

```
[EventBridge] --cron(0 7 * * ? *)-->
[Lambda: daily-analysis] --reads--> [Parameter Store: API keys]
                        --reads--> [S3: portfolio, rules, blacklist]
                        --calls--> [Claude Opus 4.6 API]
                        --sends--> [Telegram Bot API]
                        --logs--> [CloudWatch Logs]
```

**Telegram Commands (Interactive):**

```
[User] --sends command--> [Telegram]
                          --webhook POST--> [API Gateway: /webhook]
                                            --triggers--> [Lambda: telegram-handler]
                                                          --reads--> [Parameter Store]
                                                          --reads/writes--> [S3: portfolio, history]
                                                          --responds--> [Telegram]
                                                          --logs--> [CloudWatch Logs]
```

**Connections:**

- Solid arrows: Data/request flow
- Dashed arrows: Read-only
- Label arrows with action (e.g., "webhook POST", "cron trigger")

---

## High-Level Overview

### Core Components

**1. Lambda Functions (Compute)**

- `daily-analysis` - Automated market analysis (Python 3.12)
- `telegram-handler` - Command processing (Python 3.12)

**2. Storage (S3)**

- Portfolio state (`current_positions.json`)
- Trade history (`operations_full.csv`)
- Learned patterns (`patterns_learned.json`)
- Configuration (`rules.json`, `tickers_blacklist.txt`)

**3. Secrets**

- Claude API key (SecureString)
- Telegram bot token (SecureString)
- Telegram chat ID (SecureString)

**4. Triggers**

- EventBridge: Daily cron (8:00 AM CET)
- API Gateway: Telegram webhook

**5. External APIs**

- Claude Opus 4.6 (Anthropic)
- Telegram Bot API
- yfinance (market data)

---

## Data Flow

### Flow 1: Daily Analysis (Automated)

**Trigger:** EventBridge cron rule fires at 7:00 UTC (8:00 CET)

**Execution:**

1. EventBridge invokes `daily-analysis` Lambda
2. Lambda loads:
   - Secrets from Parameter Store (Claude API key, Telegram token)
   - Portfolio from S3 (`current_positions.json`)
   - Rules from S3 (`rules.json`)
   - Blacklist from S3 (`tickers_blacklist.txt`)
3. Lambda fetches market data (yfinance):
   - Current prices for open positions
4. Lambda builds optimized promp
5. Lambda calls Claude Opus 4.6 API
6. Claude analyzes and returns response
7. Lambda sends formatted message to Telegram
8. Lambda logs execution to CloudWatch
9. Lambda saves analysis log to S3

**Duration:** ~10-15 seconds

**Cost per execution:** ~$0.01

---

### Flow 2: Telegram Command (Interactive)

**Trigger:** User sends command (e.g., `/portfolio`)

**Execution:**

1. User sends message in Telegram
2. Telegram sends webhook POST to API Gateway
3. API Gateway invokes `telegram-handler` Lambda
4. Lambda parses command from webhook body
5. Lambda loads secrets from Parameter Store
6. Lambda processes command:
   - `/compro` → Reads portfolio, calculates, writes updated portfolio to S3
   - `/vendo` → Reads portfolio, calculates P&L, writes history + portfolio to S3
   - `/portfolio` → Reads current positions from S3
   - `/balance` → Reads portfolio + history from S3
   - `/stats` → Reads history, calculates stats
   - `/blacklist` → Reads/writes blacklist in S3
   - `/tips` → Reads/writes user tips in S3
7. Lambda formats response message
8. Lambda sends response to Telegram Bot API
9. Lambda logs execution to CloudWatch

**Duration:** ~2-5 seconds

---

## S3 Structure

```
trading-bot-data-victor/
│
├── portfolio/
│   └── current_positions.json          # Current open positions
│
├── history/
│   └── operations_full.csv             # Complete trade history
│
├── learning/
│   ├── patterns_learned.json           # AI-identified patterns (v1.1)
│   └── monthly_performance.json        # Monthly stats (v1.1)
│
├── external/
│   ├── tickers_blacklist.txt           # Unavailable in broker
│   └── user_tips.json                  # External insights
│
├── config/
│   └── rules.json                      # Trading rules
│
├── logs/
│   └── daily_analysis_YYYY-MM-DD.json  # Execution logs
│
└── lambda-code/
    ├── daily_analysis.zip              # Deployment packages
    └── telegram_handler.zip
```

---

## IAM Permissions

### Role: lambda-trading-bot-role

**Policies attached:**

**1. AWSLambdaBasicExecutionRole (AWS managed)**

- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:PutLogEvents`

**Purpose:** Write execution logs to CloudWatch

**2. AmazonS3FullAccess (AWS managed)**

- `s3:GetObject`
- `s3:PutObject`
- `s3:ListBucket`
- `s3:DeleteObject`

**Purpose:** Read/write portfolio, history, config files

**3. AmazonSSMReadOnlyAccess (AWS managed)**

- `ssm:GetParameter`
- `ssm:GetParameters`

**Purpose:** Read API keys and tokens from Parameter Store

**Trust relationship:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Security:** Least-privilege principle - Lambdas can only read secrets, not create/delete them.

---

## Network Configuration

**Region:** eu-west-1 (Ireland)

- Closest to Spain (low latency)
- Full service availability
- Cost-effective

**Connectivity:**

- Lambdas: VPC not required (access AWS services via service endpoints)
- API Gateway: Public endpoint (HTTPS only)
- Telegram webhook: Inbound HTTPS only

**Security:**

- S3 buckets: Block all public access
- Parameter Store: KMS encrypted (SecureString)
- HTTPS everywhere (TLS 1.2+)

---

## Scaling & Limits

### Lambda Concurrency

**daily-analysis:**

- Executions: 1/day (sequential, never concurrent)
- Reserved concurrency: Not needed

**telegram-handler:**

- Max connections: 1 (configured in Telegram webhook)
- Concurrent executions: 1 (one command at a time)
- Reserved concurrency: Not needed

### API Gateway

**Limits (Free Tier):**

- 1 million requests/month
- Expected usage: ~100-300/month
- Well within limits

### S3

**Limits:**

- 5 GB storage (Free Tier)
- Expected usage: <1 MB
- Virtually unlimited

### Parameter Store

**Limits (Standard tier):**

- 10,000 parameters
- Expected usage: 3 parameters
- No cost

---

## Monitoring & Logging

### CloudWatch Logs

**Log Groups:**

- `/aws/lambda/daily-analysis`
- `/aws/lambda/telegram-handler`

**Retention:** 7 days (configurable)

**What's logged:**

- Function start/end
- Token usage (input/output)
- API call costs
- Errors and exceptions
- S3 read/write operations

### Monitoring Metrics

**Lambda metrics (automatic):**

- Invocations
- Duration
- Errors
- Throttles

**Custom metrics (in logs):**

- Claude API tokens consumed
- Estimated costs per execution
- Portfolio value changes
- Trade P&L

---

## Error Handling

### daily-analysis

**Errors caught:**

- yfinance timeout/failure → Log warning, continue without that ticker
- Claude API error → Log error, send notification to Telegram
- S3 read/write failure → Log error, abort execution
- Telegram send failure → Log error (analysis still saved to S3)

**Retry:** Lambda automatic retry (2x) on unhandled exceptions

### telegram-handler

**Errors caught:**

- Invalid command format → Send usage example to user
- S3 read/write failure → Send error message to user
- Telegram API error → Log error, no user feedback (Telegram down)

**Retry:** No automatic retry (user can resend command)

---

## Cost Optimization

### Strategies Applied

**1. Prompt optimization**

- Reduced from ~9,000 → 478 tokens input (95% reduction)
- Reduced from ~15,000 → 319 tokens output (98% reduction)
- Savings: $10.50/month → $0.30/month

**2. Output limiting**

- max_tokens=1000
- 200-word limit in prompt instructions

**3. Lambda right-sizing**

- daily-analysis: 512 MB (needs Claude API, yfinance)
- telegram-handler: 256 MB (lighter workload)

**4. S3 lifecycle**

- No versioning (saves storage costs)
- No lifecycle policies needed (data <1 MB)

**5. Free Tier maximization**

- All services within Free Tier limits
- Only Claude API costs money ($0.30/month)

---

## Security Best Practices

✅ **Secrets management:**

- API keys in Parameter Store (encrypted)
- Never in code or environment variables
- KMS encryption at rest

✅ **S3 security:**

- Block all public access
- No bucket policies (private by default)
- IAM role-based access only

✅ **Lambda security:**

- Least-privilege IAM role
- No VPC (reduces attack surface)
- Environment variables for config only (not secrets)

✅ **API Gateway:**

- HTTPS only
- No API keys (Telegram verifies webhook)
- Regional endpoint (not edge-optimized)

✅ **Telegram:**

- Webhook over polling (more secure)
- max_connections=1 (rate limiting)
- drop_pending_updates (prevents replay attacks)

---

## Disaster Recovery

### Backup Strategy

**Code:**

- Versioned in GitHub
- Lambda ZIP files in S3 (can redeploy anytime)

**Data:**

- Portfolio: Manual backup via `/portfolio` command (copy output)
- History: CSV in S3 (download periodically)
- No automated backups (data is append-only, low risk)

### Recovery Scenarios

**Scenario 1: Lambda deleted accidentally**

- Redeploy from GitHub + S3 ZIP files (5 min)

**Scenario 2: S3 data corrupted**

- Restore from last known good backup
- Rebuild portfolio from Telegram command history
- CSV history is append-only (rarely corrupts)

**Scenario 3: AWS account compromised**

- Secrets in Parameter Store need rotation
- Redeploy entire infrastructure (30 min)
- Data loss: Only since last manual backup

---

## Next Steps

**Understand individual components:**

- [daily-analysis.md](daily-analysis.md) - How daily analysis works
- [telegram-handler.md](telegram-handler.md) - Command processing details
- [costs.md](costs.md) - Detailed cost breakdown

**Start using:**

- [telegram-commands.md](../usage/telegram-commands.md) - Command reference
- [trading-rules.md](../usage/trading-rules.md) - Configure your rules
