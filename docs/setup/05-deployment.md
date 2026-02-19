# Deployment & Updates

How to update Lambda code when making changes to handlers.

## When to Deploy Updates

**Update Lambdas when you modify:**

- Handler code (lambdas/\*/handler.py)
- Dependencies (requirements.txt changes)
- Trading logic or prompts
- Command functionality

**No deployment needed for:**

- Documentation changes
- README updates
- Config file changes (rules.json updates via S3 directly)

---

## Quick Update: AWS CLI (Recommended)

**Fastest method for code changes.**

### Update daily_analysis:

```bash
cd ~/projects/trading-bot
source .venv/bin/activate

# Recreate package
rm -rf lambda_packages/daily_analysis
mkdir -p lambda_packages/daily_analysis
cp lambdas/daily_analysis/handler.py lambda_packages/daily_analysis/
pip install -r lambdas/daily_analysis/requirements.txt -t lambda_packages/daily_analysis/

# Create ZIP
cd lambda_packages/daily_analysis
zip -r ../daily_analysis.zip .
cd ../..

# Deploy directly to Lambda (no S3 needed)
aws lambda update-function-code \
  --function-name daily-analysis \
  --zip-file fileb://lambda_packages/daily_analysis.zip

# Wait for update to complete
aws lambda wait function-updated --function-name daily-analysis

echo "✅ daily-analysis updated"
```

### Update telegram_handler:

```bash
cd ~/projects/trading-bot
source .venv/bin/activate

# Recreate package
rm -rf lambda_packages/telegram_handler
mkdir -p lambda_packages/telegram_handler
cp lambdas/telegram_handler/handler.py lambda_packages/telegram_handler/
pip install -r lambdas/telegram_handler/requirements.txt -t lambda_packages/telegram_handler/

# Create ZIP
cd lambda_packages/telegram_handler
zip -r ../telegram_handler.zip .
cd ../..

# Deploy directly
aws lambda update-function-code \
  --function-name telegram-handler \
  --zip-file fileb://lambda_packages/telegram_handler.zip

aws lambda wait function-updated --function-name telegram-handler

echo "✅ telegram-handler updated"
```

**Update completes in 10-15 seconds. All configuration preserved.**

---

## Alternative: Via S3 + Console

**Use when AWS CLI unavailable or prefer GUI.**

### Step 1: Upload to S3

```bash
cd ~/projects/trading-bot
source .venv/bin/activate

# Package Lambda (example: daily_analysis)
rm -rf lambda_packages/daily_analysis
mkdir -p lambda_packages/daily_analysis
cp lambdas/daily_analysis/handler.py lambda_packages/daily_analysis/
pip install -r lambdas/daily_analysis/requirements.txt -t lambda_packages/daily_analysis/

cd lambda_packages/daily_analysis
zip -r ../daily_analysis.zip .
cd ../..

# Upload to S3
BUCKET="trading-bot-data-victor"  # Your bucket name
aws s3 cp lambda_packages/daily_analysis.zip s3://${BUCKET}/lambda-code/daily_analysis.zip
```

### Step 2: Update Lambda via Console

**AWS Console → Lambda → daily-analysis**

1. **Code source → Upload from → Amazon S3 location**
2. **S3 link URL:** `s3://trading-bot-data-victor/lambda-code/daily_analysis.zip`
3. **Click "Save"**
4. Wait 10-20 seconds

✅ **Lambda updated**

---

## Update Only S3 Files (No Code Change)

**Update trading rules, blacklist, or tips without redeploying Lambda.**

### Update trading rules:

```bash
cd ~/projects/trading-bot

# Edit config/rules.json.example locally
# Then upload to S3:

BUCKET="trading-bot-data-victor"
aws s3 cp config/rules.json.example s3://${BUCKET}/config/rules.json
```

**Next Lambda execution will use new rules.**

### Update blacklist:

```bash
# Create/edit blacklist locally
cat > temp_blacklist.txt << 'EOF'
PLTR
TSLA
GME
EOF

# Upload
aws s3 cp temp_blacklist.txt s3://${BUCKET}/external/tickers_blacklist.txt
rm temp_blacklist.txt
```

### Clear tips:

```bash
echo "[]" > temp_tips.json
aws s3 cp temp_tips.json s3://${BUCKET}/external/user_tips.json
rm temp_tips.json
```

---

## Verify Deployment

### Check Lambda version:

**AWS Console → Lambda → Function → Code tab**

Look for: "Last modified: X minutes ago"

### Test immediately:

**Lambda console → Test tab → Click "Test"**

Executes Lambda manually to verify changes work.

### Monitor logs:

**Lambda → Monitor → View CloudWatch logs**

Check latest log stream for errors.

---

## Common Update Scenarios

### Scenario 1: Change prompt in daily_analysis

**Edit:** `lambdas/daily_analysis/handler.py` (build_prompt function)

**Deploy:**

```bash
# Quick update via CLI
cd ~/projects/trading-bot
source .venv/bin/activate
# ... package and deploy daily_analysis (see above)
```

**Test:** Lambda console → Test, or wait until 8:00 AM

---

### Scenario 2: Add new Telegram command

**Edit:** `lambdas/telegram_handler/handler.py`

- Add `cmd_new_command()` function
- Add to `process_command()` switch
- Update `cmd_help()` text

**Deploy:**

```bash
# Package and deploy telegram_handler
# ... (see Quick Update section above)
```

**Test:** Send command in Telegram immediately

---

### Scenario 3: Change stop-loss percentage

**Edit:** `config/rules.json.example`

**Deploy:**

```bash
BUCKET="trading-bot-data-victor"
aws s3 cp config/rules.json.example s3://${BUCKET}/config/rules.json
```

**Applies:** Next daily analysis (no Lambda redeploy needed)

---

## Rollback (Emergency)

**If new deployment breaks something:**

### Option 1: Revert code locally and redeploy

```bash
# Git revert
git log  # Find last working commit
git checkout <commit-hash> lambdas/daily_analysis/handler.py

# Redeploy
# ... (package and update Lambda)
```

### Option 2: Previous S3 version (if versioning enabled)

**S3 Console → Bucket → lambda-code/ → daily_analysis.zip**

**Versions tab → Restore previous version**

Then update Lambda from that S3 object.

---

## Best Practices

✅ **Test locally first:**

```bash
cd ~/projects/trading-bot
source .venv/bin/activate
python3 lambdas/daily_analysis/handler.py  # Local test
```

✅ **Git commit before deploying:**

```bash
git add lambdas/daily_analysis/handler.py
git commit -m "feat: update prompt X"
git push
# Then deploy to AWS
```

✅ **Check CloudWatch Logs after deploy:**

- Verify no errors
- Confirm new logic executing

✅ **Small changes, frequent deploys:**

- Change one thing at a time
- Easier to debug if something breaks

---

## Troubleshooting

**"Function not found"**

- Check function name spelling
- Verify AWS region: `aws configure get region`

**"Insufficient permissions"**

- IAM user needs lambda:UpdateFunctionCode permission
- AdministratorAccess policy includes this

**"Invalid request" or "Malformed ZIP"**

- Verify ZIP structure: handler.py at root, not nested in folder
- Recreate package from scratch

**Changes not taking effect**

- Clear browser cache if using AWS Console
- Wait 10-20 seconds for Lambda cold start
- Check CloudWatch Logs for actual execution

---

## Next Steps

Setup complete! Your trading bot is now:

- ✅ Deployed to AWS
- ✅ Automated (daily 8:00 AM analysis)
- ✅ Interactive (Telegram commands)
- ✅ Updatable (via this deployment guide)

**Continue to technical documentation:**

→ [docs/technical/architecture.md](../technical/architecture.md) - System architecture and data flow

→ [docs/usage/telegram-commands.md](../usage/telegram-commands.md) - Command reference
