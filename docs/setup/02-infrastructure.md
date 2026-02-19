# AWS Infrastructure Setup

Set up S3 storage, Parameter Store for secrets, and IAM roles.

## Prerequisites

- AWS account configured ([01-aws-account.md](01-aws-account.md))
- AWS CLI installed and configured
- Terminal access

---

## Step 1: Create S3 Bucket

**Why:** Store portfolio data, trade history, and learned patterns.

### Via AWS Console:

**Search bar:** Type `S3` → Click **S3**

**Click:** "Create bucket"

**Configuration:**

- **Bucket name:** `trading-bot-data-YOUR-NAME` (must be globally unique)
  - Example: `trading-bot-data-victor`
  - Only lowercase, numbers, hyphens
- **AWS Region:** EU (Ireland) eu-west-1 ✅
- **Object Ownership:** ACLs disabled (recommended) ✅
- **Block Public Access:** Keep ALL boxes checked ✅ (security)
- **Bucket Versioning:** Disable (saves costs)
- **Default encryption:** SSE-S3 (enabled by default) ✅

**Click "Create bucket"**

✅ **Bucket created successfully**

---

## Step 2: Create S3 Folder Structure

**Terminal:**

```bash
cd ~/projects/trading-bot

# Create temporary folder
mkdir -p temp_s3_init

# Portfolio initial state
cat > temp_s3_init/current_positions.json << 'EOF'
{
  "positions": [],
  "cash_eur": 2300,
  "last_updated": "2026-02-17T22:00:00"
}
EOF

# Trade history (header only)
cat > temp_s3_init/operations_full.csv << 'EOF'
ticker,quantity,entry_price,exit_price,date_close,gross_pnl,net_pnl,pnl_pct,result
EOF

# Patterns (empty initially)
cat > temp_s3_init/patterns_learned.json << 'EOF'
{
  "patterns": [],
  "key_learnings": [],
  "next_month_focus": ""
}
EOF

# Blacklist (empty)
cat > temp_s3_init/tickers_blacklist.txt << 'EOF'
EOF

# User tips (empty)
cat > temp_s3_init/user_tips.json << 'EOF'
[]
EOF

# Upload to S3 (replace YOUR-BUCKET-NAME)
BUCKET="trading-bot-data-victor"  # Change this

aws s3 cp temp_s3_init/current_positions.json s3://${BUCKET}/portfolio/current_positions.json
aws s3 cp temp_s3_init/operations_full.csv s3://${BUCKET}/history/operations_full.csv
aws s3 cp temp_s3_init/patterns_learned.json s3://${BUCKET}/learning/patterns_learned.json
aws s3 cp temp_s3_init/tickers_blacklist.txt s3://${BUCKET}/external/tickers_blacklist.txt
aws s3 cp temp_s3_init/user_tips.json s3://${BUCKET}/external/user_tips.json

# Cleanup
rm -rf temp_s3_init
```

**Verify structure:**

```bash
aws s3 ls s3://trading-bot-data-victor/ --recursive
```

**Expected output:**

```
portfolio/current_positions.json
history/operations_full.csv
learning/patterns_learned.json
external/tickers_blacklist.txt
external/user_tips.json
```

---

## Step 3: Upload Trading Rules

**Terminal:**

```bash
cd ~/projects/trading-bot

# Upload rules template to S3
aws s3 cp config/rules.json.example s3://${BUCKET}/config/rules.json
```

---

## Step 4: Configure Parameter Store (Secrets)

**Why:** Store API keys and tokens securely (encrypted).

**Search bar:** Type `Systems Manager` → Click **Systems Manager**

**Left menu:** Parameter Store → **Create parameter**

### Parameter 1: Claude API Key

**Details:**

- **Name:** `/trading-bot/claude-api-key`
- **Description:** `Claude API key for Opus 4.6`
- **Tier:** Standard
- **Type:** SecureString ✅ (encrypted)
- **KMS key source:** My current account
- **KMS Key ID:** alias/aws/ssm (default)
- **Value:** `sk-ant-YOUR-ACTUAL-KEY` (from console.anthropic.com)

**Click "Create parameter"**

### Parameter 2: Telegram Token

**Click "Create parameter"**

**Details:**

- **Name:** `/trading-bot/telegram-token`
- **Description:** `Telegram bot token`
- **Tier:** Standard
- **Type:** SecureString
- **Value:** `YOUR_TELEGRAM_BOT_TOKEN` (from @BotFather)

**Click "Create parameter"**

### Parameter 3: Telegram Chat ID

**Click "Create parameter"**

**Details:**

- **Name:** `/trading-bot/telegram-chat-id`
- **Description:** `Telegram chat ID`
- **Tier:** Standard
- **Type:** String (not SecureString, not sensitive)
- **Value:** `YOUR_CHAT_ID` (your Telegram user ID)

**Click "Create parameter"**

**Verify all 3 parameters exist:**

```
/trading-bot/claude-api-key      SecureString
/trading-bot/telegram-token      SecureString
/trading-bot/telegram-chat-id    String
```

---

## Step 5: Create IAM Role for Lambdas

**Why:** Lambda functions need permissions to access S3, Parameter Store, and CloudWatch Logs.

**Search bar:** Type `IAM` → Click **IAM**

**Left menu:** Roles → **Create role**

### Trusted entity:

- **Trusted entity type:** AWS service
- **Use case:** Lambda ✅

**Click "Next"**

### Permissions:

**Search and select these 3 policies:**

1. ✅ `AWSLambdaBasicExecutionRole` (CloudWatch Logs)
2. ✅ `AmazonS3FullAccess` (S3 read/write)
3. ✅ `AmazonSSMReadOnlyAccess` (Parameter Store read)

**Click "Next"**

### Role details:

- **Role name:** `lambda-trading-bot-role`
- **Description:** `Execution role for trading bot Lambda functions`

**Click "Create role"**

✅ **Role created successfully**

---

## Verification Checklist

Before proceeding to Lambda deployment:

✅ S3 bucket created with proper structure
✅ 5 files uploaded to S3 (portfolio, history, patterns, blacklist, tips)
✅ Trading rules uploaded to S3
✅ 3 parameters in Parameter Store (claude-api-key, telegram-token, telegram-chat-id)
✅ IAM role `lambda-trading-bot-role` created with 3 policies

---

## Next Steps

→ [03-lambdas.md](03-lambdas.md) - Deploy Lambda functions

---

## Troubleshooting

**"Bucket name already exists"**

- S3 bucket names are globally unique
- Add unique suffix: `trading-bot-data-victor-2026`

**"Access Denied" uploading to S3**

- Verify AWS CLI is configured: `aws sts get-caller-identity`
- Check IAM user has S3 permissions

**"Parameter already exists"**

- If recreating, delete old parameter first
- Or use "Edit" instead of "Create"
