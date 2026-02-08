# Repository Study: aws-rotate-iam-keys

## Study Overview

This repository contains **aws-rotate-iam-keys**, a cross-platform automation tool for rotating AWS IAM access keys. I have conducted a comprehensive reverse engineering analysis to understand its architecture, functionality, and implementation details.

## Study Deliverables

This study includes three comprehensive documents:

### 1. [REVERSE_ENGINEERING_ANALYSIS.md](./REVERSE_ENGINEERING_ANALYSIS.md) - Complete Technical Analysis

**Scope:** 400+ lines of in-depth technical documentation

**Contents:**
- Executive summary and project overview
- Detailed architecture analysis
- Step-by-step code walkthrough
- Security analysis and considerations
- Installation and packaging mechanisms
- Platform-specific implementations
- Dependencies and requirements
- Error handling patterns
- Code quality observations
- Real-world usage scenarios
- Technical insights and design decisions

**Best for:** Developers who want to understand the complete codebase, security professionals, or anyone planning to contribute to or fork the project.

### 2. [WORKFLOW_DIAGRAM.md](./WORKFLOW_DIAGRAM.md) - Visual Workflows

**Scope:** ASCII-art diagrams and flowcharts

**Contents:**
- Complete key rotation flow (10-step process)
- Error handling and recovery paths
- Scheduling architecture across platforms
- Multi-profile scenarios
- AWS IAM state transitions
- Eventual consistency handling
- Security model visualization
- Platform-specific execution paths

**Best for:** Visual learners, system architects, or anyone who needs to understand the tool's operation flow at a glance.

### 3. [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - User Guide

**Scope:** Practical quick reference for daily use

**Contents:**
- Quick start instructions
- Common commands and examples
- Configuration guidelines
- Troubleshooting tips
- Security best practices
- FAQ
- Cheat sheet

**Best for:** End users, DevOps engineers, or anyone who needs to use the tool immediately.

---

## Key Findings

### What This Tool Does

**aws-rotate-iam-keys** automates the rotation of AWS IAM access keys, addressing AWS security best practices that recommend rotating credentials every 30-90 days. It reduces a manual, error-prone process to a single command or fully automated scheduled task.

### Core Functionality

**The Rotation Process (10 Steps):**
1. Parse command-line arguments (profile selection)
2. Verify configuration in `~/.aws/credentials`
3. Validate keys are identical across profiles (if multiple)
4. Set up AWS environment variables
5. Verify current key count (max 2 per user)
6. Create new access key via AWS IAM API
7. Verify new key works (60-second retry loop for propagation)
8. Update credentials file with new key
9. Delete old access key from AWS
10. Success - credentials are now fresh

**Safety Features:**
- Automatic rollback if any step fails
- No downtime (old key works until deleted)
- Eventual consistency handling (AWS IAM propagation delays)
- Clear error messages with context

### Architecture Highlights

**Cross-Platform Design:**
- **Linux/macOS:** Bash script using AWS CLI and jq
- **Windows:** PowerShell script using AWSPowerShell module
- **Scheduling:** cron (Linux), launchd (macOS), Task Scheduler (Windows)

**Key Technologies:**
- **Bash 4.0+** with strict error handling (`set -euo pipefail`)
- **GNU getopt** for robust argument parsing
- **jq** for JSON processing
- **AWS CLI / AWSPowerShell** for IAM API interaction

**Distribution:**
- Ubuntu PPA (apt-get)
- Homebrew tap (macOS)
- Debian packages (.deb)
- Direct download (PowerShell script)
- Docker support

### Security Model

**Minimum IAM Permissions Required:**
```json
{
  "Action": [
    "iam:ListAccessKeys",
    "iam:CreateAccessKey", 
    "iam:DeleteAccessKey"
  ],
  "Resource": "arn:aws:iam::*:user/${aws:username}"
}
```

**Key Security Features:**
- Principle of least privilege (user can only manage own keys)
- Atomic operations with rollback
- Session token clearing (avoids conflicts with temporary credentials)
- Environment variable cleanup

**Considerations:**
- Brief credential exposure in environment variables during rotation
- Single-computer design (multi-device requires sync solution)
- Force flag can delete unknown keys (use with caution)

### Code Quality Observations

**Strengths:**
- ✓ Defensive programming with comprehensive error handling
- ✓ Platform compatibility checks and fallbacks
- ✓ Clear user feedback during execution
- ✓ Idempotent operations (safe to run multiple times)
- ✓ Well-structured build and packaging system

**Areas for Improvement:**
- Windows implementation lacks retry logic for key verification
- No automated test suite
- Sparse inline code comments

---

## Technical Insights

### Why the 60-Second Retry Loop?

AWS IAM uses **eventual consistency**. When you create a new access key, it's not immediately available across all AWS regions. The script retries up to 20 times with 3-second delays (60 seconds total) to ensure the new key has fully propagated before deleting the old key.

```bash
for i in $(seq 1 20); do
    ERROR=$(aws iam list-access-keys 2>&1 1>/dev/null) && break || sleep 3
done
```

Without this, you could delete the old key before the new key is usable, leaving you locked out of AWS.

### Why Export Credentials to Environment?

```bash
export AWS_ACCESS_KEY_ID=$NEW_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$NEW_SECRET_ACCESS_KEY
```

After updating the credentials file, if we used `--profile`, AWS CLI would try to use the new key from the file. But environment variables take precedence, allowing us to delete the old key even after updating the file. This ensures the deletion command uses the verified working key.

### Why GNU getopt Instead of getopts?

GNU getopt provides:
- Long option support (`--profile` vs `-p`)
- Robust argument parsing with proper quoting
- Better error messages
- POSIX compliance

The script includes compatibility checks for macOS, which uses BSD getopt by default.

### Multi-Profile Architecture

**Shared Key Mode** (`--profiles p1,p2,p3`):
- All profiles updated with same key atomically
- One rotation operation
- Useful for dev/staging/prod profiles for same account

**Separate Key Mode** (multiple invocations):
- Each profile rotated independently
- Different keys per profile
- Useful for work vs. personal accounts

---

## Build & Package System

### Debian/Ubuntu Build Process

The `build.sh` script:
1. Extracts version from main script
2. Creates distribution directory
3. Updates debian changelog with version and codename
4. Builds .deb package using `dpkg-deb`
5. Builds Ubuntu source package using `debuild`
6. Cleans up temporary files

**Post-installation** (`src/debian/postinst`):
- Detects non-root username (tries multiple methods)
- Installs cron job at random minute (load distribution)
- Format: `MM 2 * * * /usr/bin/aws-rotate-iam-keys --profile default >/dev/null`

### Homebrew Formula

**Installation:**
```ruby
bin.install "src/bin/aws-rotate-iam-keys"
etc.install "aws-rotate-iam-keys"  # Default config
```

**Service Definition:**
```ruby
cron "23 3 * * *"  # Daily at 3:23 AM
run_at_load true
```

**Dependencies:**
- gnu-getopt (required)
- jq (required)
- awscli (recommended)

### Windows Setup

PowerShell script automatically:
1. Checks for AWS CLI installation
2. Installs AWSPowerShell module if missing
3. Creates Scheduled Task on first run
4. Random time between 2-6 AM for load distribution

---

## Use Cases & Scenarios

### Scenario 1: Individual Developer
```bash
# One-time setup
brew install aws-rotate-iam-keys
brew services start aws-rotate-iam-keys

# Keys rotate automatically every night at 3:23 AM
# Never think about it again!
```

### Scenario 2: Multiple AWS Accounts
```bash
# Create custom config
echo "--profile personal" > ~/.aws-rotate-iam-keys
echo "--profile work" >> ~/.aws-rotate-iam-keys

# Restart service
brew services restart aws-rotate-iam-keys

# Both accounts rotate nightly with different keys
```

### Scenario 3: Multi-Computer Setup
```bash
# Sync credentials file across machines
# Use: SpiderOak, Sync.com, or custom sync

# IMPORTANT: Only enable rotation on ONE computer
# Other computers just use synced credentials
```

### Scenario 4: Key Compromise Response
```bash
# Immediately rotate compromised key
aws-rotate-iam-keys --profile compromised

# Old key invalidated within seconds
# Check CloudTrail for unauthorized usage
aws cloudtrail lookup-events --lookup-attributes \
  AttributeKey=Username,AttributeValue=myuser
```

---

## Compliance & Best Practices

### Compliance Standards Addressed

This tool helps meet requirements from:
- **PCI-DSS 8.2.4:** Change passwords/passphrases every 90 days
- **NIST 800-53 IA-5:** Authenticator management
- **CIS AWS Benchmark:** Rotate access keys every 90 days
- **AWS Well-Architected Framework:** Security best practices

### Recommended Practices

✓ **DO:**
- Enable daily or weekly rotation
- Monitor AWS CloudTrail for key events
- Use minimum required IAM permissions
- Keep AWS CLI updated
- Set up alerts for keys older than 90 days

✗ **DON'T:**
- Share credentials files
- Commit credentials to version control
- Run rotation on multiple computers for same user
- Disable scheduled rotation
- Use `--force` without understanding implications

---

## Project Stats

- **Lines of Code:** ~190 lines (bash), ~115 lines (PowerShell)
- **Version Analyzed:** 0.9.8.5
- **License:** GNU General Public License
- **Languages:** Bash, PowerShell, Ruby (Homebrew formula)
- **Platforms:** Linux, macOS, Windows
- **Dependencies:** Minimal (aws-cli, jq, gnu-getopt)
- **Distribution Channels:** 4 (PPA, Homebrew, direct download, Docker)
- **GitHub:** https://github.com/rhyeal/aws-rotate-iam-keys

---

## Testing the Tool (Optional)

If you want to test this tool:

### Prerequisites
1. AWS account with IAM user
2. AWS credentials configured (`~/.aws/credentials`)
3. Required IAM permissions (ListAccessKeys, CreateAccessKey, DeleteAccessKey)

### Safe Testing
```bash
# Check current keys
aws iam list-access-keys

# Note the creation date of current key
# Run rotation
aws-rotate-iam-keys --profile default

# Verify new key created
aws iam list-access-keys
# You should see a newly created key (different ID, recent date)

# Test AWS CLI still works
aws sts get-caller-identity
```

### Rollback Test
```bash
# Create a second key manually
aws iam create-access-key

# Try rotation (should fail - too many keys)
aws-rotate-iam-keys
# Expected: Error about having more than 1 key

# Try with force
aws-rotate-iam-keys --force
# Expected: Deletes unknown key, rotates successfully
```

---

## Learning Outcomes

From this study, I've gained understanding of:

1. **Secure Credential Management**
   - How to safely rotate credentials without downtime
   - Handling AWS IAM eventual consistency
   - Implementing atomic operations with rollback

2. **Cross-Platform Scripting**
   - Writing portable bash scripts
   - Platform-specific quirks (GNU vs BSD tools)
   - PowerShell equivalents for Windows

3. **Package Management**
   - Building Debian/Ubuntu packages
   - Creating Homebrew formulae
   - Distribution via multiple channels

4. **Scheduling Systems**
   - cron vs launchd vs Task Scheduler
   - Load distribution strategies (random times)
   - Reliability considerations (sleeping computers)

5. **Error Handling Patterns**
   - Strict error modes in bash
   - Graceful degradation
   - User-friendly error messages

6. **AWS IAM API**
   - Key management operations
   - IAM permission scoping
   - Propagation delays and retry strategies

---

## Conclusion

**aws-rotate-iam-keys** is a well-engineered, production-ready tool that solves a real security problem with minimal complexity. The implementation demonstrates:

- **Good engineering:** Defensive programming, error handling, platform compatibility
- **User focus:** Simple installation, automatic scheduling, clear feedback
- **Security-first:** Minimal permissions, atomic operations, rollback on failure
- **Practical design:** Addresses AWS API quirks (eventual consistency)

The project's philosophy is embodied in its tagline: *"Security is easier when it's less than 3 lines that you need to copy + paste to be secure."*

By automating a tedious but critical security practice, this tool makes it feasible to follow AWS best practices consistently.

---

## Additional Resources

- **GitHub Repository:** https://github.com/rhyeal/aws-rotate-iam-keys
- **Project Website:** https://aws-rotate-iam-keys.com
- **Author Contact:** awsRotateKeys@rhyeal.com
- **AWS IAM Documentation:** https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html
- **AWS Best Practices:** https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html

---

## Study Methodology

This reverse engineering study was conducted by:

1. **Code Analysis:** Reading and annotating every line of the main scripts
2. **Architecture Mapping:** Understanding component relationships and data flow
3. **Workflow Tracing:** Following execution paths through the code
4. **Security Review:** Analyzing permissions, error handling, and attack vectors
5. **Build System Analysis:** Understanding packaging and distribution
6. **Platform Comparison:** Identifying differences between Linux/macOS/Windows implementations
7. **Documentation Creation:** Synthesizing findings into comprehensive guides

**Total Analysis Time:** Approximately 2-3 hours  
**Documentation Created:** 3 comprehensive documents, 1,300+ lines of documentation  
**Study Date:** 2026-02-08

---

*This study provides a complete understanding of the aws-rotate-iam-keys project through reverse engineering. All three documentation files are independent and can be read separately based on your needs.*
