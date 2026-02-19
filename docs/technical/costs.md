# Cost Analysis

Detailed breakdown of operating costs and optimization strategies.

## Monthly Cost Summary

**Total: $0.30/month**

| Service             | Cost      | Notes                   |
| ------------------- | --------- | ----------------------- |
| Claude Opus 4.6 API | $0.30     | Only paid service       |
| AWS Lambda          | $0.00     | Free Tier (1M requests) |
| AWS S3              | $0.00     | Free Tier (<5 GB)       |
| AWS Parameter Store | $0.00     | Standard tier free      |
| AWS EventBridge     | $0.00     | Free Tier               |
| AWS API Gateway     | $0.00     | Free Tier (1M requests) |
| AWS CloudWatch Logs | $0.00     | Free Tier (5 GB)        |
| **TOTAL**           | **$0.30** | 99% within Free Tier    |

---

## Claude API Costs (Detailed)

### Pricing Model

**Claude Opus 4.6:**

- Input: $5.00 per 1M tokens
- Output: $25.00 per 1M tokens

### Daily Analysis (Automated)

**Actual consumption per execution:**

- Input tokens: 478
- Output tokens: 319
- Cost per execution: $0.01036

**Calculation:**

```
Input:  478 × ($5 / 1,000,000) = $0.00239
Output: 319 × ($25 / 1,000,000) = $0.00797
Total: $0.01036 per analysis
```

**Monthly cost:**

```
30 days × $0.01036 = $0.31 ≈ $0.30/month
```

**Annual cost:**

```
365 days × $0.01036 = $3.78/year
```

### Cost Optimization History

**Version 0.1 (Pre-optimization):**

- Input: ~9,000 tokens
- Output: ~15,000 tokens
- Cost per execution: $0.36
- **Monthly: $10.80**

**Version 1.0 (Current - Optimized):**

- Input: 478 tokens (95% reduction ⬇️)
- Output: 319 tokens (98% reduction ⬇️)
- Cost per execution: $0.01
- **Monthly: $0.30** (97% savings 💰)

**How we achieved this:**

1. Removed verbose instructions
2. Eliminated market data from prompt (Claude uses web search)
3. Strict 200-word output limit
4. No tables, no examples in prompt
5. Only include position data if positions exist
6. max_tokens=1000 hard cap

---

## AWS Free Tier Breakdown

### Lambda

**Free Tier limits:**

- 1,000,000 requests per month
- 400,000 GB-seconds compute time

**Our usage:**

- `daily-analysis`: 30 executions/month (512 MB, 15 sec avg)
- `telegram-handler`: ~100 executions/month (256 MB, 3 sec avg)

**Compute calculation:**

```
daily-analysis:   30 × (512/1024 GB × 15 sec) = 225 GB-seconds
telegram-handler: 100 × (256/1024 GB × 3 sec) = 75 GB-seconds
Total: 300 GB-seconds (0.075% of Free Tier)
```

**Verdict:** ✅ Completely free (nowhere near limits)

---

### S3

**Free Tier limits (first 12 months):**

- 5 GB storage
- 20,000 GET requests
- 2,000 PUT requests

**Our usage:**

- Storage: <1 MB (0.02% of limit)
- GET requests: ~150/month (0.75% of limit)
- PUT requests: ~50/month (2.5% of limit)

**After 12 months:**

- Storage: $0.023 per GB/month
- Our cost: $0.023 × 0.001 GB = **$0.00002/month** (negligible)

**Verdict:** ✅ Free during first year, essentially free after

---

### API Gateway

**Free Tier limits:**

- 1,000,000 API calls per month (first 12 months)

**Our usage:**

- ~100 webhook calls/month (commands)
- 0.01% of Free Tier

**After 12 months:**

- $3.50 per million requests
- Our cost: $3.50 × 0.0001 = **$0.00035/month**

**Verdict:** ✅ Free first year, negligible after

---

### EventBridge

**Free Tier:**

- All state change events are free
- Custom events: 14M per month free

**Our usage:**

- 30 cron events/month
- 0.0002% of limit

**Verdict:** ✅ Always free

---

### Parameter Store

**Standard tier:**

- 10,000 parameters free
- No throughput limits for standard parameters

**Our usage:**

- 3 parameters
- 0.03% of limit

**Verdict:** ✅ Always free

---

### CloudWatch Logs

**Free Tier:**

- 5 GB ingestion per month
- 5 GB archive storage

**Our usage:**

- ~50 MB logs/month (1% of limit)

**After Free Tier:**

- $0.50 per GB ingestion
- Our cost: $0.50 × 0.05 = **$0.025/month**

**Verdict:** ✅ Free first year, negligible after

---

## Cost Projections

### Year 1 (with Free Tier)

| Month            | Claude API | AWS       | Total     |
| ---------------- | ---------- | --------- | --------- |
| 1-12             | $0.30      | $0.00     | $0.30     |
| **Year 1 Total** | **$3.60**  | **$0.00** | **$3.60** |

### Year 2+ (post Free Tier)

| Service     | Monthly   | Annual    |
| ----------- | --------- | --------- |
| Claude API  | $0.30     | $3.60     |
| S3          | $0.00     | $0.00     |
| API Gateway | $0.00     | $0.00     |
| CloudWatch  | $0.03     | $0.36     |
| Lambda      | $0.00     | $0.00     |
| **Total**   | **$0.33** | **$3.96** |

**Increase after Year 1:** +$0.03/month (+10%)

---

## Scaling Scenarios

### What if usage increases?

**Scenario 1: 3x command usage**

- Telegram commands: 100 → 300/month
- Lambda cost: Still $0.00 (within Free Tier)
- API Gateway: Still $0.00 (within Free Tier)

**Scenario 2: Multiple daily analyses**

- Current: 1/day (30/month)
- New: 3/day (90/month)
- Claude API: $0.30 → $0.90/month (+$0.60)
- Lambda: Still $0.00 (within Free Tier)

**Scenario 3: Add monthly consolidation**

- Executions: +1/month
- Claude API: +$0.02/month
- Lambda: Still $0.00

**Scenario 4: 10x all usage**

- Commands: 1,000/month
- Analyses: 300/month
- Claude API: ~$3/month
- Lambda: $0.00 (still within 1M requests)
- S3: $0.00 (still <1 MB)
- API Gateway: $0.00 (still within 1M)

**Break-even point:** Would need >100,000 commands/month to exceed Free Tier limits

---

## Cost Comparison

### vs Traditional Cloud Solutions

**Comparable setup with EC2:**

- t3.micro (smallest): $8.32/month
- Plus EBS storage: $0.80/month
- Plus data transfer: $0.50/month
- **Total: ~$10/month**

**Our serverless approach:**

- $0.30/month (97% cheaper)

### vs Paid Trading Tools

**TradingView Premium:** $14.95/month
**Bloomberg Terminal:** $2,000/month
**Our AI bot:** $0.30/month

**Savings vs cheapest alternative:** $14.65/month ($175.80/year)

---

## Token Usage Analysis

### Input Token Breakdown (478 tokens)

**Prompt structure:**

- Header + date: ~20 tokens
- Position data (if any): ~50-100 tokens
- Rules: ~40 tokens
- Blacklist: ~20 tokens
- Instructions: ~300 tokens

**Optimization opportunities:**

- ✅ Already minimal
- ✅ Only includes positions if they exist
- ✅ No market data (Claude fetches via web search)

### Output Token Breakdown (319 tokens)

**Response structure:**

- Macro: ~40 tokens
- Positions (if any): ~50-80 tokens
- Opportunities: ~60-100 tokens
- Crypto: ~30 tokens
- Summary: ~50 tokens

**Hard limit:** max_tokens=1000 (never exceeded)

**Average:** 319 tokens (~200 words as specified)

---

## Cost Monitoring

### Real-Time Tracking

**Anthropic Console:**

- https://console.anthropic.com/settings/usage
- Shows daily/monthly token usage
- Set spending limits
- Enable billing alerts

**AWS Cost Explorer:**

- AWS Console → Cost Management
- Shows per-service costs
- Set budgets and alerts

### Recommended Alerts

**Anthropic:**

- Alert at $2/month (67% of expected)
- Hard limit at $3/month (safety net)

**AWS:**

- Budget: $1/month (should stay at $0)
- Alert if >$0.10/month (investigate unexpected charges)

---

## Cost Reduction Tips

### Already Implemented

✅ **Prompt optimization** (97% reduction)
✅ **Output limiting** (max_tokens=1000)
✅ **Efficient S3 usage** (no versioning)
✅ **Webhook over polling** (Telegram)
✅ **Right-sized Lambdas** (512/256 MB)
✅ **No unnecessary services** (no VPC, no NAT, no ALB)

### Future Optimizations (if needed)

**Multi-model approach (v2.0):**

- Haiku ($0.25/$1.25 per 1M) for simple checks
- Sonnet ($3/$15 per 1M) for medium analysis
- Opus ($5/$25 per 1M) only when needed
- Potential savings: 40-60%

**Conditional analysis:**

- Skip analysis if no positions and no market volatility
- Potential savings: ~20%

**Batch processing:**

- Analyze multiple days together (not really applicable here)

---

## Hidden Costs (None)

**Common AWS gotchas we avoid:**

❌ **Data transfer fees** - Minimal (API responses <10 KB)
❌ **NAT Gateway** - Not needed (no VPC)
❌ **Load balancer** - Not needed (API Gateway)
❌ **RDS/DynamoDB** - Not needed (S3 sufficient)
❌ **CloudFront** - Not needed (no static website)
❌ **Route53** - Not needed (no custom domain)

**Truly transparent pricing:** What you see is what you pay.

---

## Return on Investment

### Time Saved

**Manual equivalent tasks:**

- Daily market research: 30 min/day = 15 hours/month
- Portfolio tracking: 10 min/day = 5 hours/month
- Trade logging: 5 min/trade = 1 hour/month
- **Total: ~21 hours/month**

**Your hourly rate assumption: $20/hour**

- Time saved value: $420/month
- Bot cost: $0.30/month
- **ROI: 1,400x** 🚀

### Educational Value

**Learning AWS, Claude API, Python automation:**

- Equivalent bootcamp course: $500-2,000
- Your cost: $3.60/year to maintain real production system

---

## Summary

**Current state:**

- ✅ $0.30/month operational cost
- ✅ 99% of infrastructure free (AWS Free Tier)
- ✅ Only pay for AI analysis (Claude API)
- ✅ Highly optimized (97% cost reduction from v1)
- ✅ Room to scale 100x without leaving Free Tier

**Bottom line:** Professional-grade trading assistant for less than a coffee per month. ☕

---

## Related Documentation

- [architecture.md](architecture.md) - System design
- [daily-analysis.md](daily-analysis.md) - How analysis works
- [telegram-handler.md](telegram-handler.md) - Command processing
