# AWS Account Setup

Complete guide to create and secure your AWS account.

## Prerequisites

- Valid email address
- Credit/debit card (required for verification, won't be charged if using Free Tier)
- Phone number for verification

---

## Step 1: Create AWS Account

**Go to:** https://aws.amazon.com

**Click:** "Create an AWS Account"

**Provide:**

1. **Email address** - Your primary email
2. **AWS account name** - e.g., `trading-bot-prod` or your name
3. **Password** - Strong password (save in password manager)

**Follow prompts:**

- Contact information (Personal)
- Payment information (card verification - $1 charge refunded in 3-5 days)
- Identity verification (phone call or SMS)
- Support plan: **Basic Support - Free**

**You'll see:** AWS Management Console dashboard

---

## Step 2: Enable MFA (Multi-Factor Authentication)

**Why:** Protects your root account from unauthorized access.

**In AWS Console:**

1. Click your **account name** (top right)
2. **Security credentials**
3. Scroll to **Multi-factor authentication (MFA)**
4. Click **Assign MFA device**

**Setup:**

- **Device name:** `iPhone YourName` (or your device)
- **MFA device type:** Authenticator app (Google Authenticator, Authy, Microsoft Authenticator)
- Scan QR code with your app
- Enter two consecutive codes
- Click **Assign MFA**

✅ **Root account now secured with MFA**

---

## Step 3: Create IAM User (Daily Work)

**Why:** Never use root account for daily tasks. Create limited-privilege user instead.

**In search bar:** Type `IAM` → Click **IAM**

**Left menu:** Users → **Create user**

### User details:

- **User name:** `your-name-dev` (e.g., `victor-dev`)
- ✅ Check: "Provide user access to the AWS Management Console"
- **Console password:** Custom password (different from root)
- ❌ Uncheck: "Users must create a new password at next sign-in"

**Click "Next"**

### Set permissions:

- **Permissions options:** Attach policies directly
- **Search and select:** `AdministratorAccess`

**Click "Next"** → **Create user**

### ⚠️ Save credentials:

- **Download .csv file** → save securely
- Note the **Console sign-in URL** (you'll use this instead of root login)

✅ **IAM user created**

---

## Step 4: Install AWS CLI

**Why:** Manage AWS services from terminal (deploy code, configure services).

### Linux (Ubuntu/Debian):

```bash
# Download installer
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"

# Unzip (install unzip if needed: sudo apt install unzip)
unzip awscliv2.zip

# Install
sudo ./aws/install

# Verify
aws --version
# Should show: aws-cli/2.x.x Python/3.x.x Linux/...
```

---

## Step 5: Create Access Keys

**Why:** Allow AWS CLI to authenticate with your account.

**In IAM Console:**

1. **IAM** → **Users** → Click your user (`victor-dev`)
2. **Security credentials** tab
3. Scroll to **Access keys** → **Create access key**

**Use case:** Command Line Interface (CLI)

✅ Check: "I understand the above recommendation..."

**Click "Next"**

**Description tag (optional):** `Linux laptop`

**Click "Create access key"**

### ⚠️ Save credentials:

- **Access key ID:** `AKIA...`
- **Secret access key:** `wJalrX...`
- **Download .csv file** → save securely

**This is the ONLY time you'll see the secret key. If lost, create new keys.**

---

## Step 6: Configure AWS CLI

**Terminal:**

```bash
aws configure
```

**You'll be prompted for 4 values:**

```
AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE  # Paste from CSV
AWS Secret Access Key [None]: wJalrXUtn...       # Paste from CSV
Default region name [None]: eu-west-1            # Ireland (closest to Spain)
Default output format [None]: json               # JSON output
```

---

## Step 7: Verify Setup

**Test AWS CLI connection:**

```bash
aws sts get-caller-identity
```

**Expected output:**

```json
{
  "UserId": "AIDAI...",
  "Account": "123456789012",
  "Arn": "arn:aws:iam::123456789012:user/victor-dev"
}
```

✅ **If you see your Account number and user ARN → SUCCESS**

---

## Region Configuration

**Why eu-west-1 (Ireland)?**

- Closest AWS region to Spain (lowest latency)
- Full service availability
- Most common EU region

**Change region in Console:**

- Top right dropdown → Select **Europe (Ireland) eu-west-1**
- Keep this consistent across all services

---

## Security Best Practices

✅ **Root account:**

- Use ONLY for initial setup and billing
- MFA enabled
- Sign out after setup

✅ **IAM user:**

- Use for all daily work
- AdministratorAccess for this project (single user)
- Can create restricted roles later if needed

✅ **Access keys:**

- Stored in `~/.aws/credentials` (never commit to git)
- Rotate periodically (every 90 days recommended)

---

## Next Steps

→ [02-infrastructure.md](02-infrastructure.md) - Set up S3, Parameter Store, and IAM roles

---

## Troubleshooting

**"Command not found: aws"**

- Verify installation: `which aws`
- Try: `sudo ./aws/install --update`

**"Unable to locate credentials"**

- Run `aws configure` again
- Verify credentials are correct

**"Access Denied"**

- Ensure IAM user has AdministratorAccess policy
- Check you're using IAM user credentials, not root
