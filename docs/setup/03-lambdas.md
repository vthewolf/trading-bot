# Lambda Functions Deployment

Deploy both Lambda functions (daily_analysis and telegram_handler) to AWS.

## Prerequisites

- Infrastructure setup complete ([02-infrastructure.md](02-infrastructure.md))
- Project cloned locally
- Python virtual environment configured

---

## Step 1: Prepare Environment

**Terminal:**

```bash
cd ~/projects/trading-bot

# Activate virtual environment
source .venv/bin/activate

# Verify dependencies installed
pip list | grep -E "anthropic|boto3|yfinance|python-telegram-bot"
```

---

## Step 2: Package daily_analysis Lambda

### Create deployment package:

```bash
# Clean previous builds
rm -rf lambda_packages/

# Create package folder
mkdir -p lambda_packages/daily_analysis

# Copy handler
cp lambdas/daily_analysis/handler.py lambda_packages/daily_analysis/

# Install dependencies into package
pip install -r lambdas/daily_analysis/requirements.txt -t lambda_packages/daily_analysis/

# Create ZIP
cd lambda_packages/daily_analysis
zip -r ../daily_analysis.zip .
cd ../..

# Verify ZIP size
ls -lh lambda_packages/daily_analysis.zip
# Should be ~50-60 MB
```

### Upload to S3:

```bash
# Replace with your bucket name
BUCKET="trading-bot-data-victor"

aws s3 cp lambda_packages/daily_analysis.zip s3://${BUCKET}/lambda-code/daily_analysis.zip
```

---

## Step 3: Create daily_analysis Lambda

**AWS Console → Search: Lambda → Create function**

### Basic information:

- **Function name:** `daily-analysis`
- **Runtime:** Python 3.12
- **Architecture:** x86_64

### Permissions:

- **Execution role:** Use an existing role
- **Existing role:** `lambda-trading-bot-role`

**Click "Create function"**

### Upload code:

1. Scroll to **Code source**
2. **Upload from → Amazon S3 location**
3. **S3 link URL:** `s3://trading-bot-data-victor/lambda-code/daily_analysis.zip`
4. **Click "Save"**
5. Wait 10-20 seconds for upload

### Configure handler:

1. **Configuration → General configuration → Edit**
2. **Handler:** `handler.lambda_handler` (not lambda_function.lambda_handler)
3. **Click "Save"**

### Configure timeout and memory:

1. **Configuration → General configuration → Edit**
2. **Timeout:** 1 min 0 sec
3. **Memory:** 512 MB
4. **Click "Save"**

### Add environment variables:

1. **Configuration → Environment variables → Edit**
2. **Add environment variable:**
   - Key: `S3_BUCKET`
   - Value: `trading-bot-data-victor`
3. **Add environment variable:**
   - Key: `ENVIRONMENT`
   - Value: `aws`
4. **Click "Save"**

---

## Step 4: Test daily_analysis

**Lambda console → Test tab**

**Create test event:**

- **Event name:** `test-analysis`
- **Template:** hello-world (default)
- **Click "Save"**

**Click "Test"**

**Expected result:**

```json
{
  "statusCode": 200,
  "body": "Análisis completado"
}
```

**Check Telegram:** You should receive analysis message.

✅ **daily_analysis Lambda working**

---

## Step 5: Package telegram_handler Lambda

**Terminal:**

```bash
cd ~/projects/trading-bot

# Clean and create package
rm -rf lambda_packages/telegram_handler
mkdir -p lambda_packages/telegram_handler

# Copy handler
cp lambdas/telegram_handler/handler.py lambda_packages/telegram_handler/

# Install dependencies
pip install -r lambdas/telegram_handler/requirements.txt -t lambda_packages/telegram_handler/

# Create ZIP
cd lambda_packages/telegram_handler
zip -r ../telegram_handler.zip .
cd ../..

# Upload to S3
aws s3 cp lambda_packages/telegram_handler.zip s3://${BUCKET}/lambda-code/telegram_handler.zip
```

---

## Step 6: Create telegram_handler Lambda

**AWS Console → Lambda → Create function**

### Basic information:

- **Function name:** `telegram-handler`
- **Runtime:** Python 3.12
- **Architecture:** x86_64

### Permissions:

- **Execution role:** Use an existing role
- **Existing role:** `lambda-trading-bot-role`

**Click "Create function"**

### Upload code:

1. **Code source → Upload from → Amazon S3 location**
2. **S3 link URL:** `s3://trading-bot-data-victor/lambda-code/telegram_handler.zip`
3. **Click "Save"**

### Configure handler:

1. **Configuration → General configuration → Edit**
2. **Handler:** `handler.lambda_handler`
3. **Timeout:** 30 sec
4. **Memory:** 256 MB
5. **Click "Save"**

### Add environment variables:

1. **Configuration → Environment variables → Edit**
2. **Add:**
   - Key: `S3_BUCKET`, Value: `trading-bot-data-victor`
   - Key: `ENVIRONMENT`, Value: `aws`
3. **Click "Save"**

---

## Step 7: Test telegram_handler

**Lambda console → Test tab**

**Create test event:**

- **Event name:** `test-help`
- **Event JSON:**

```json
{
  "body": "{\"message\":{\"text\":\"/help\",\"chat\":{\"id\":YOUR_CHAT_ID}}}"
}
```

Replace `YOUR_CHAT_ID` with your actual Telegram chat ID.

**Click "Save" → Click "Test"**

**Expected:**

- Response: 200 OK
- Telegram: Receive /help message

✅ **telegram_handler Lambda working**

---

## Verification Checklist

✅ daily-analysis Lambda created and tested
✅ telegram-handler Lambda created and tested
✅ Both functions have correct handler configured
✅ Both functions have S3_BUCKET and ENVIRONMENT variables
✅ Both functions use lambda-trading-bot-role

---

## Next Steps

→ [04-automation.md](04-automation.md) - Configure EventBridge and Telegram webhook

---

## Troubleshooting

**"Unable to import module 'lambda_function'"**

- Handler is incorrect
- Change to: `handler.lambda_handler`

**"Task timed out after 3.00 seconds"**

- Increase timeout (Configuration → General configuration)
- daily-analysis: 60 sec
- telegram-handler: 30 sec

**"Access Denied" reading Parameter Store**

- Verify lambda-trading-bot-role has AmazonSSMReadOnlyAccess policy

**Lambda test succeeds but no Telegram message**

- Check CloudWatch Logs for errors
- Verify Parameter Store has correct telegram-token and telegram-chat-id
