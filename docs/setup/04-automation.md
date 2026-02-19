# Automation Setup

Configure daily triggers and Telegram webhook for instant responses.

## Prerequisites

- Both Lambda functions deployed ([03-lambdas.md](03-lambdas.md))
- Lambdas tested and working

---

## Part 1: EventBridge - Daily Trigger (8:00 AM)

**Why:** Automatically execute daily_analysis every morning at 8:00 AM CET.

### Option A: Add Trigger from Lambda (Recommended)

**Lambda console → daily-analysis**

1. **Configuration tab → Triggers → Add trigger**

2. **Select a source:** EventBridge (CloudWatch Events)

3. **Rule:** Create a new rule

4. **Rule configuration:**
   - **Rule name:** `daily-analysis-trigger`
   - **Rule description:** `Trigger daily analysis at 8AM CET`
   - **Rule type:** Schedule expression
   - **Schedule expression:**

```
     cron(0 7 * * ? *)
```

**Why 7 and not 8?**

- EventBridge uses UTC timezone
- Spain CET = UTC+1
- 8:00 AM CET = 7:00 AM UTC

5. **Click "Add"**

✅ **Trigger configured - will execute daily at 8:00 AM CET**

### Verify Trigger

**Lambda → daily-analysis → Configuration → Triggers**

You should see:

```
EventBridge (CloudWatch Events): daily-analysis-trigger
```

---

## Part 2: API Gateway - Telegram Webhook

**Why:** Enable instant responses to Telegram commands (instead of polling).

### Step 1: Create REST API

**AWS Console → Search: API Gateway**

**Click "Create API"**

**Choose:** REST API (not private) → **Build**

**Create new API:**

- **API name:** `telegram-webhook-api`
- **Description:** `Webhook for Telegram bot`
- **Endpoint Type:** Regional

**Click "Create API"**

---

### Step 2: Create Resource

**Actions dropdown → Create Resource**

**Resource configuration:**

- **Resource Name:** `webhook`
- **Resource Path:** `/webhook`

**Click "Create Resource"**

---

### Step 3: Create POST Method

**With `/webhook` selected:**

**Actions → Create Method**

**Dropdown:** Select **POST** → Click checkmark ✓

**POST Setup:**

- **Integration type:** Lambda Function ✅
- **Use Lambda Proxy integration:** ✅ Checked
- **Lambda Region:** eu-west-1
- **Lambda Function:** `telegram-handler`

**Click "Save"**

**Popup "Add Permission to Lambda Function"** → **OK**

---

### Step 4: Deploy API

**Actions → Deploy API**

**Deployment stage:** [New Stage]

**Stage name:** `prod`

**Click "Deploy"**

**You'll see:** Invoke URL

```
https://abc123xyz.execute-api.eu-west-1.amazonaws.com/prod
```

**Copy this URL** - you'll need it for Telegram webhook.

---

### Step 5: Configure Telegram Webhook

**Terminal:**

```bash
# Replace <YOUR_TOKEN> with your actual Telegram bot token
# Replace <YOUR_INVOKE_URL> with your API Gateway invoke URL

curl -X POST https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{"url": "<YOUR_INVOKE_URL>/webhook", "max_connections": 1, "drop_pending_updates": true}'
```

**Example:**

```bash
curl -X POST https://api.telegram.org/bot123456:ABC-DEF/setWebhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://abc123.execute-api.eu-west-1.amazonaws.com/prod/webhook", "max_connections": 1, "drop_pending_updates": true}'
```

**Expected response:**

```json
{ "ok": true, "result": true, "description": "Webhook was set" }
```

**Important parameters:**

- `max_connections: 1` - Prevents overwhelming Lambda with concurrent requests
- `drop_pending_updates: true` - Clears any old pending messages

---

### Step 6: Verify Webhook

**Check webhook info:**

```bash
curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
```

**Expected:**

```json
{
  "ok": true,
  "result": {
    "url": "https://abc123.execute-api.eu-west-1.amazonaws.com/prod/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0,
    "max_connections": 1
  }
}
```

---

### Step 7: Test Live

**Open Telegram → Message your bot:**

```
/help
```

**Expected:** Instant response with command list.

**Test other commands:**

```
/portfolio
/balance
/stats
```

✅ **Webhook working - instant command responses**

---

## Verification Checklist

✅ EventBridge trigger configured for 8:00 AM daily
✅ API Gateway created with /webhook POST method
✅ Telegram webhook configured with API Gateway URL
✅ Commands respond instantly in Telegram
✅ Tomorrow 8:00 AM will receive first automatic analysis

---

## Next Steps

→ [05-deployment.md](05-deployment.md) - How to update Lambda code when making changes

---

## Troubleshooting

### EventBridge not triggering

**Check CloudWatch Logs:**

- Lambda → Monitor → View CloudWatch logs
- Look for executions around 7:00 UTC (8:00 CET)

**Verify trigger:**

- Lambda → Configuration → Triggers
- Should show EventBridge rule

### Telegram webhook not responding

**Delete and reconfigure webhook:**

```bash
# Delete webhook
curl -X POST https://api.telegram.org/bot<YOUR_TOKEN>/deleteWebhook

# Wait 30 seconds

# Set webhook again (with drop_pending_updates)
curl -X POST https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook \
  -H "Content-Type: application/json" \
  -d '{"url": "<YOUR_INVOKE_URL>/webhook", "max_connections": 1, "drop_pending_updates": true}'
```

**Check Lambda logs:**

- Lambda → telegram-handler → Monitor → View CloudWatch logs
- Should see execution when you send Telegram command

### API Gateway 502/503 errors

**Verify Lambda permissions:**

- API Gateway → Resources → POST → Integration Request
- Lambda should have permission from API Gateway
- If not, recreate method integration

**Check Lambda timeout:**

- telegram-handler should have 30 sec timeout minimum
- Configuration → General configuration
