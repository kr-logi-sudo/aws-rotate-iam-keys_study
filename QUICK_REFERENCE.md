# AWS Rotate IAM Keys - Quick Reference Guide

## What Does This Tool Do?

**In one sentence:** Automatically rotates your AWS IAM access keys to keep them fresh and secure, following AWS security best practices.

**The problem it solves:** AWS recommends rotating IAM keys every 30-90 days, but manually doing this is tedious and error-prone. This tool automates it completely.

---

## How It Works (30-Second Explanation)

1. **Reads** your current AWS key from `~/.aws/credentials`
2. **Creates** a new AWS access key via IAM API
3. **Verifies** the new key works (waits up to 60 seconds for propagation)
4. **Updates** your credentials file with the new key
5. **Deletes** the old key from AWS
6. **Done!** Your credentials are now fresh

**Safe:** If anything fails, it rolls back automatically.

---

## Quick Start

### Install & Run Manually

**macOS:**
```bash
brew tap rhyeal/aws-rotate-iam-keys https://github.com/rhyeal/aws-rotate-iam-keys
brew install aws-rotate-iam-keys
aws-rotate-iam-keys
```

**Ubuntu:**
```bash
sudo add-apt-repository ppa:rhyeal/aws-rotate-iam-keys
sudo apt-get update
sudo apt-get install aws-rotate-iam-keys
aws-rotate-iam-keys
```

**Windows:**
```powershell
# Download and run the PowerShell script
# It will rotate keys AND set up automatic daily rotation
.\aws-rotate-iam-keys.ps1
```

### Enable Automatic Daily Rotation

**macOS:**
```bash
brew services start aws-rotate-iam-keys
```

**Ubuntu/Debian:**
Already enabled! A cron job was created during installation.

**Windows:**
Already enabled! A Scheduled Task was created on first run.

---

## Common Commands

### Rotate Default Profile
```bash
aws-rotate-iam-keys
```

### Rotate Specific Profile
```bash
aws-rotate-iam-keys --profile myProfile
```

### Rotate Multiple Profiles (Same Key)
```bash
aws-rotate-iam-keys --profiles dev,staging,prod
```
*Result: All three profiles get identical new keys*

### Rotate Multiple Profiles (Different Keys)
```bash
aws-rotate-iam-keys --profile work
aws-rotate-iam-keys --profile personal
```
*Result: Each profile gets its own unique keys*

### Force Rotation (Delete Extra Keys)
```bash
aws-rotate-iam-keys --force
```
*Use when you have 2 keys and need to rotate*

### Show Version
```bash
aws-rotate-iam-keys --version
```

### Show Help
```bash
aws-rotate-iam-keys --help
```

---

## Key Concepts

### Profile
A named set of AWS credentials in `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
region = us-east-1

[work]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
region = us-west-2
```

### Access Key
An AWS credential consisting of:
- **Access Key ID**: Public identifier (e.g., `AKIAIOSFODNN7EXAMPLE`)
- **Secret Access Key**: Private key (never share!)

### Rotation
Replacing an old access key with a new one:
1. Old key still works
2. Create new key (now you have 2)
3. Switch to new key
4. Delete old key (now you have 1 again)

---

## Configuration

### macOS: Customize Automatic Rotation

**Create custom config:**
```bash
cp $(brew --prefix)/etc/aws-rotate-iam-keys ~/.aws-rotate-iam-keys
nano ~/.aws-rotate-iam-keys
```

**Config format** (one line per execution):
```
--profile default
--profiles work,personal
--profile another
```

**Restart service** to apply:
```bash
brew services restart aws-rotate-iam-keys
```

### Ubuntu/Debian: Customize Cron Job

**Edit crontab:**
```bash
EDITOR=nano crontab -e
```

**Find line like:**
```cron
33 2 * * * /usr/bin/aws-rotate-iam-keys --profile default >/dev/null #rotate AWS keys daily
```

**Modify as needed**, then save (Ctrl+O, Enter, Ctrl+X).

### Windows: Modify Scheduled Task

1. Open **Task Scheduler**
2. Find task named **"AWS Rotate IAM Keys"**
3. Edit the `-profile` parameter in the command

---

## Required AWS Permissions

Your IAM user needs these permissions (add via IAM policy):

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "iam:ListAccessKeys",
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey"
    ],
    "Resource": "arn:aws:iam::*:user/${aws:username}"
  }]
}
```

**What this allows:**
- ✓ List your own keys
- ✓ Create new keys for yourself
- ✓ Delete your own keys
- ✗ Cannot affect other users

---

## Troubleshooting

### "More than 1 access key" Error

**Problem:** You already have 2 keys (AWS maximum).

**Solution 1 (Recommended):**
Manually delete one key via AWS Console, then retry.

**Solution 2 (Force):**
```bash
aws-rotate-iam-keys --force
```
This will automatically delete unknown extra keys.

### "Could not find access key" Error

**Problem:** Profile doesn't exist or is misconfigured.

**Check your profiles:**
```bash
aws configure list --profile yourProfile
```

**Set up profile:**
```bash
aws configure --profile yourProfile
```

### "InvalidClientTokenId" or "SignatureDoesNotMatch"

**Problem:** Keys in credentials file don't match what's in AWS.

**Fix:**
1. Get valid keys from AWS Console
2. Run: `aws configure --profile yourProfile`
3. Enter the valid keys

### Keys Not Rotating Automatically

**macOS:**
```bash
# Check if service is running
brew services list | grep aws-rotate

# Start service if not running
brew services start aws-rotate-iam-keys

# Check logs
cat /tmp/homebrew.mxcl.aws-rotate-iam-keys.log
```

**Ubuntu/Debian:**
```bash
# Check crontab
crontab -l | grep aws-rotate

# Check syslog
grep aws-rotate-iam-keys /var/log/syslog
```

**Windows:**
```powershell
# Open Task Scheduler
# Find "AWS Rotate IAM Keys" task
# Check "Last Run Result" column
```

### Multi-Computer Issues

**Problem:** Rotating keys on Computer A breaks credentials on Computer B.

**Solution:** Only run rotation on ONE computer, then sync the credentials file.

**Sync methods:**
- SpiderOak (encrypted sync)
- Sync.com (encrypted sync)
- Dropbox (manual symlink of `~/.aws/`)
- Custom sync solution

**Setup symlink example:**
```bash
# Move credentials to synced folder
mv ~/.aws/credentials ~/Dropbox/aws-credentials

# Create symlink
ln -s ~/Dropbox/aws-credentials ~/.aws/credentials
```

---

## Advanced Usage

### Check When Keys Were Last Rotated

```bash
aws iam list-access-keys --profile default
```

Output shows `CreateDate` for each key.

### Dry Run (Check What Would Happen)

There's no dry-run mode, but you can check your current state:
```bash
# Check credentials
aws configure list --profile default

# Check keys in AWS
aws iam list-access-keys --profile default

# Check key age
aws iam list-access-keys --profile default --output json | jq '.AccessKeyMetadata[].CreateDate'
```

### Rotate During Specific Time Window

**Edit your schedule** to match your needs:

**macOS** (`$(brew --prefix)/etc/aws-rotate-iam-keys.rb`):
```ruby
cron "23 3 * * *"  # 3:23 AM daily
```

**Linux** (crontab):
```cron
23 3 * * * /usr/bin/aws-rotate-iam-keys --profile default >/dev/null
```

**Windows** (Task Scheduler):
Modify the "Start time" in task properties.

### Rotate Only When Connected to Specific Network

**macOS/Linux:**
Wrap command in a script that checks network:
```bash
#!/bin/bash
# Only rotate on corporate VPN
if ip addr show tun0 &>/dev/null; then
  aws-rotate-iam-keys --profile work
fi
```

---

## Security Best Practices

### ✓ DO

- ✓ Run rotation daily or weekly
- ✓ Use minimum required IAM permissions
- ✓ Keep AWS CLI updated
- ✓ Monitor AWS CloudTrail for key creation/deletion
- ✓ Use different keys for work vs. personal profiles
- ✓ Set up alerts for keys older than 90 days

### ✗ DON'T

- ✗ Share your `~/.aws/credentials` file
- ✗ Commit credentials to version control
- ✗ Run rotation on multiple computers for same IAM user
- ✗ Disable the scheduled job (defeats the purpose!)
- ✗ Use `--force` flag without understanding what it does
- ✗ Rotate keys while actively using them (brief outage possible)

### AWS CloudTrail Monitoring

Set up alerts for these events:
- `CreateAccessKey`
- `DeleteAccessKey`
- Failed API calls with old keys

### Compliance

This tool helps meet:
- **PCI-DSS 8.2.4**: Change user passwords/passphrases every 90 days
- **NIST 800-53 IA-5**: Authenticator management requirements
- **CIS AWS Benchmark**: Rotate access keys every 90 days

---

## File Locations

### Credentials File
**Linux/macOS:** `~/.aws/credentials`  
**Windows:** `C:\Users\YourName\.aws\credentials`

### Script Location
**Linux:** `/usr/bin/aws-rotate-iam-keys`  
**macOS:** `/usr/local/bin/aws-rotate-iam-keys`  
**Windows:** Wherever you downloaded the `.ps1` file

### Config Files
**macOS Global:** `$(brew --prefix)/etc/aws-rotate-iam-keys`  
**macOS User:** `~/.aws-rotate-iam-keys`

### Logs
**macOS:** `/tmp/homebrew.mxcl.aws-rotate-iam-keys.log`  
**Linux:** `/var/log/syslog` (search for `aws-rotate-iam-keys`)  
**Windows:** Task Scheduler log

---

## Dependencies

### Required
**Linux/macOS:**
- bash (4.0+)
- GNU getopt
- jq
- aws-cli

**Windows:**
- PowerShell 5.1+
- AWSPowerShell module
- AWS CLI

### Installation of Dependencies

**macOS:**
```bash
# Usually installed with the tool
brew install gnu-getopt jq awscli
```

**Ubuntu/Debian:**
```bash
sudo apt-get install jq awscli
```

**Windows:**
```powershell
# Install AWS CLI
choco install awscli

# AWSPowerShell module auto-installs on first run
```

---

## Under the Hood

### What Happens During Rotation?

```
1. Read current key from credentials file
2. Call: aws iam create-access-key
3. Get back: NEW_KEY_ID + NEW_SECRET
4. Test new key (retry up to 60 seconds)
5. Update credentials file with new key
6. Call: aws iam delete-access-key OLD_KEY_ID
7. Done!
```

**Total time:** ~10-15 seconds  
**Downtime:** None (old key works until deleted)

### Why the 60-Second Wait?

AWS IAM uses **eventual consistency**. New keys take time (seconds to minutes) to propagate globally. The script waits and retries to ensure the new key works before deleting the old one.

### What If Something Fails?

**Automatic rollback:**
1. Delete the new key from AWS
2. Keep using the old key
3. Exit with error message
4. Your system is left in its original working state

**No data loss possible.**

---

## Example Scenarios

### Scenario 1: First-Time Setup
```bash
# Install
brew install aws-rotate-iam-keys

# Run manually once to test
aws-rotate-iam-keys

# Enable daily automation
brew services start aws-rotate-iam-keys

# Verify it's scheduled
brew services list | grep aws-rotate
```

### Scenario 2: Multiple AWS Accounts
```bash
# Set up profiles
aws configure --profile personal
aws configure --profile work

# Rotate both (different keys)
aws-rotate-iam-keys --profile personal
aws-rotate-iam-keys --profile work

# Or schedule both in config
echo "--profile personal" >> ~/.aws-rotate-iam-keys
echo "--profile work" >> ~/.aws-rotate-iam-keys
brew services restart aws-rotate-iam-keys
```

### Scenario 3: Shared Dev/Staging/Prod
```bash
# All use same key (you wear all hats in small team)
aws-rotate-iam-keys --profiles dev,staging,prod

# Check all profiles were updated
aws configure get dev.aws_access_key_id
aws configure get staging.aws_access_key_id
aws configure get prod.aws_access_key_id
# All should show same key ID
```

### Scenario 4: Key Compromise Recovery
```bash
# Immediately rotate compromised key
aws-rotate-iam-keys --profile compromised

# Old key now invalid within seconds
# Attacker's copy is useless

# Check CloudTrail for unauthorized usage
aws cloudtrail lookup-events --lookup-attributes \
  AttributeKey=Username,AttributeValue=myuser
```

---

## FAQ

**Q: How often should I rotate?**  
A: AWS recommends every 30-90 days. Daily rotation is safest.

**Q: Will this break running applications?**  
A: Applications using the old key will need to reload credentials. Most AWS SDKs do this automatically.

**Q: Can I rotate keys for IAM roles?**  
A: No, this is for IAM user access keys only. IAM roles use temporary credentials that auto-rotate.

**Q: What if I have 2 keys already?**  
A: Use `--force` flag, or manually delete one key in AWS Console.

**Q: Is this safe to run in production?**  
A: Yes! It's designed for production use with automatic rollback on failure.

**Q: Does this work with MFA?**  
A: Yes, MFA is separate from access keys. This only rotates the access keys.

**Q: Can I rotate keys for multiple IAM users?**  
A: No, each IAM user must rotate their own keys (security best practice).

**Q: What about AWS SSO or temporary credentials?**  
A: This tool is for long-term IAM user access keys. AWS SSO and temporary credentials auto-expire.

**Q: Will this affect my AWS CLI usage?**  
A: No interruption. The rotation is atomic and updates your credentials file.

**Q: How do I uninstall?**  
- **macOS:** `brew services stop aws-rotate-iam-keys && brew uninstall aws-rotate-iam-keys`
- **Ubuntu:** `sudo apt-get remove aws-rotate-iam-keys`
- **Windows:** Delete the `.ps1` file and remove the Scheduled Task

---

## Getting Help

**GitHub Issues:** https://github.com/rhyeal/aws-rotate-iam-keys/issues  
**Email:** awsRotateKeys@rhyeal.com  
**Website:** https://aws-rotate-iam-keys.com  
**AWS IAM Docs:** https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html

---

## Summary Cheat Sheet

```bash
# Install (macOS)
brew install aws-rotate-iam-keys

# Install (Ubuntu)
sudo apt-get install aws-rotate-iam-keys

# Manual rotation
aws-rotate-iam-keys

# Rotate specific profile
aws-rotate-iam-keys --profile myProfile

# Multiple profiles (same key)
aws-rotate-iam-keys --profiles p1,p2,p3

# Enable automation (macOS)
brew services start aws-rotate-iam-keys

# Check logs (macOS)
cat /tmp/homebrew.mxcl.aws-rotate-iam-keys.log

# Check when last rotated
aws iam list-access-keys

# Force rotation (delete extras)
aws-rotate-iam-keys --force

# Customize schedule (macOS)
cp $(brew --prefix)/etc/aws-rotate-iam-keys ~/.aws-rotate-iam-keys
nano ~/.aws-rotate-iam-keys

# Customize schedule (Linux)
crontab -e
```

**Remember:** Security is easier when automated!
