# AWS Rotate IAM Keys - Reverse Engineering Analysis

## Executive Summary

**aws-rotate-iam-keys** is a cross-platform automation tool designed to rotate AWS IAM access keys automatically. It addresses the security best practice of regularly rotating IAM credentials (every 30-90 days) by automating the entire process, making it as simple as a single command or a scheduled job.

**Version Analyzed:** 0.9.8.5  
**Primary Language:** Bash (Linux/macOS), PowerShell (Windows)  
**License:** GNU General Public License

---

## Project Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Scheduling Layer                          │
│  (cron/launchd/Task Scheduler)                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Main Rotation Scripts                           │
│  - Linux/macOS: aws-rotate-iam-keys (bash)                  │
│  - Windows: aws-rotate-iam-keys.ps1 (PowerShell)           │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   AWS IAM API                                │
│  - list-access-keys                                          │
│  - create-access-key                                         │
│  - delete-access-key                                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│            Local Credentials Storage                         │
│  ~/.aws/credentials                                          │
└─────────────────────────────────────────────────────────────┘
```

### Core Components

1. **Rotation Script** (`src/bin/aws-rotate-iam-keys`)
   - Primary executable for Linux/macOS
   - Written in Bash
   - Handles command-line argument parsing
   - Orchestrates the entire key rotation process

2. **Windows Script** (`Windows/aws-rotate-iam-keys.ps1`)
   - PowerShell equivalent for Windows
   - Uses AWSPowerShell module
   - Implements same rotation logic with Windows-specific scheduling

3. **Packaging & Distribution**
   - Debian/Ubuntu packages (.deb)
   - Homebrew formula (macOS)
   - Raw script distribution
   - Docker support

4. **Scheduling Components**
   - cron (Linux)
   - launchd (macOS)
   - Task Scheduler (Windows)

---

## Key Rotation Workflow

### Step-by-Step Process (Linux/macOS Script)

The bash script follows this precise sequence:

#### 1. **Initialization & Argument Parsing** (Lines 10-89)

```bash
# Parse command-line arguments
--profile / -p     : Single profile to rotate
--profiles         : Multiple profiles (same key)
--force / -f       : Force rotation even with warnings
--version / -v     : Show version
--help / -h        : Show help
```

**Default behavior:** If no profile specified, uses "default" profile.

#### 2. **Configuration Verification** (Lines 93-105)

```bash
# For each profile:
1. Extract aws_access_key_id
2. Extract aws_secret_access_key  
3. Extract region
4. Validate all required fields exist
```

**Critical check:** If multiple profiles specified, ensures they all use the SAME access key (unless --force is used).

#### 3. **Environment Setup** (Lines 117-129)

```bash
# Set AWS CLI environment variables
export AWS_ACCESS_KEY_ID=$ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION=$DEFAULT_REGION
export AWS_PAGER=""                    # Disable pager
export AWS_SESSION_TOKEN=""            # Clear session tokens
```

**Why?** This allows interaction with AWS API without using profiles directly, enabling deletion of old key after updating credentials.

#### 4. **Pre-Rotation Validation** (Lines 131-146)

```bash
# Check existing key count
KEY_COUNT=$(aws iam list-access-keys --output json | jq '.AccessKeyMetadata | length')

if KEY_COUNT > 1:
    if --force enabled:
        Delete all keys except current one
    else:
        Exit with error
```

**AWS Limitation:** IAM users can have maximum 2 access keys. Script needs space to create new key.

#### 5. **New Key Creation** (Lines 148-153)

```bash
RESPONSE=$(aws iam create-access-key --output json | jq .AccessKey)
NEW_ACCESS_KEY_ID=$(echo $RESPONSE | jq -r '.AccessKeyId')
NEW_SECRET_ACCESS_KEY=$(echo $RESPONSE | jq -r '.SecretAccessKey')
```

**At this point:** User has 2 active keys (old + new).

#### 6. **New Key Verification** (Lines 155-170)

```bash
# Switch to new key in environment
export AWS_ACCESS_KEY_ID=$NEW_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$NEW_SECRET_ACCESS_KEY

# Retry up to 20 times with 3-second delays (60 seconds total)
for i in $(seq 1 20); do
    ERROR=$(aws iam list-access-keys 2>&1 1>/dev/null) && break || sleep 3
done

if ERROR exists:
    Rollback: Delete new key, restore old key
    Exit with error
```

**Critical wait period:** New keys take time to propagate through AWS systems. The 60-second retry loop handles eventual consistency.

#### 7. **Credentials File Update** (Lines 172-178)

```bash
# Update all specified profiles
for each profile in PROFILES_ARR:
    aws configure set aws_access_key_id $NEW_ACCESS_KEY_ID --profile $profile
    aws configure set aws_secret_access_key $NEW_SECRET_ACCESS_KEY --profile $profile
```

**Note:** This updates `~/.aws/credentials` file for each profile.

#### 8. **Old Key Deletion** (Lines 180-183)

```bash
aws iam delete-access-key --access-key-id $OLD_ACCESS_KEY_ID
```

**Safe deletion:** Only after verifying new key works and updating credentials file.

#### 9. **Completion** (Lines 185-186)

```bash
echo "Keys rotated"
exit 0
```

---

## Windows Implementation Differences

The PowerShell script (`Windows/aws-rotate-iam-keys.ps1`) follows similar logic but with platform-specific differences:

### Key Differences:

1. **Scheduled Task Setup** (Lines 8-18)
   - Automatically creates Windows Scheduled Task on first run
   - Random time between 2-6 AM to distribute load
   - Task runs daily with hidden window

2. **PowerShell Modules** (Lines 42-75)
   - Uses `AWSPowerShell` module instead of AWS CLI
   - Checks for AWS CLI installation separately
   - Auto-installs required modules

3. **Credential Management** (Lines 84-113)
   - Uses PowerShell credential store
   - Updates both filesystem (`~/.aws/credentials`) and PowerShell credential store
   - Uses `New-IAMAccessKey`, `Remove-IAMAccessKey` cmdlets

4. **No Retry Logic**
   - Simpler implementation without the 60-second retry loop
   - Assumes immediate key availability (may be less robust)

---

## Installation & Packaging

### Build System

The project uses platform-specific package managers:

#### Debian/Ubuntu Packages (`build.sh`)

```bash
# Build process:
1. Extract VERSION from script (0.9.8.5)
2. Create dist/ directory with source files
3. Update debian/changelog with current version
4. Build .deb package using dpkg-deb
5. Build Ubuntu source package using debuild
6. Copy changelog back to source
```

**Output:** `aws-rotate-iam-keys.X.Y.Z.deb`

#### Homebrew Formula (`Formula/aws-rotate-iam-keys.rb`)

```ruby
# Dependencies:
- gnu-getopt (required)
- jq (required)
- awscli (recommended)

# Installation:
1. Install script to /usr/local/bin/
2. Create default config at /usr/local/etc/aws-rotate-iam-keys
3. Setup launchd service for daily execution
```

**Service Configuration:**
- Runs at 3:23 AM daily
- Reads config from `~/.aws-rotate-iam-keys` or falls back to global config
- Supports multiple invocations (one per line in config)

### Post-Installation Scripts

#### Debian/Ubuntu (`src/debian/postinst`)

```bash
# On package installation:
1. Detect current username (not root)
2. Check if cron job already exists
3. Add cron entry at random minute (0-59) at 2 AM
4. Format: "MM 2 * * * /usr/bin/aws-rotate-iam-keys --profile default >/dev/null"
```

**Intelligence:** Script tries multiple methods to detect username:
- `ps -o user=`
- `logname`
- `whoami`
- `id -u -n`
- Environment variables: `$USER`, `$SUDO_USER`

---

## Security Analysis

### Security Strengths

1. **Minimal Permission Requirements**
   - Only requires: `iam:ListAccessKeys`, `iam:CreateAccessKey`, `iam:DeleteAccessKey`
   - Scoped to user's own credentials: `arn:aws:iam::*:user/${aws:username}`

2. **Atomic Operation**
   - Creates new key before deleting old one
   - Rollback mechanism if new key verification fails

3. **Verification Step**
   - Tests new key works before committing change
   - 60-second retry window handles AWS propagation delays

4. **Session Token Clearing**
   - Explicitly clears `AWS_SESSION_TOKEN` to avoid conflicts
   - Prevents issues with temporary credentials from tools like awsume

### Security Considerations

1. **Credentials in Environment Variables**
   - Script exports keys to environment during execution
   - Could be visible in process listings
   - Mitigated by: short execution time, only during rotation

2. **Single Computer Design**
   - Not designed for multi-device usage
   - Rotating on one machine invalidates keys on other machines
   - Solution: Use file sync services (SpiderOak, Sync.com)

3. **Force Flag Danger**
   - `--force` flag can delete unknown access keys
   - Could delete keys being used elsewhere
   - Should be used with caution

4. **Logging Considerations**
   - Logs to syslog when not attached to terminal
   - Could potentially log sensitive errors
   - Output redirected to `/dev/null` in cron jobs

---

## Command-Line Interface

### Usage Patterns

#### Single Profile Rotation
```bash
aws-rotate-iam-keys
aws-rotate-iam-keys --profile myProfile
```

#### Multiple Profiles (Shared Key)
```bash
aws-rotate-iam-keys --profiles profile1,profile2,profile3
```
**Result:** All three profiles get identical access keys.

#### Multiple Profiles (Separate Keys)
```bash
aws-rotate-iam-keys --profile profile1
aws-rotate-iam-keys --profile profile2
```
**Result:** Each profile gets different access keys.

#### Force Mode
```bash
aws-rotate-iam-keys --force
```
**Effects:**
- Allows rotation when multiple keys exist (deletes extras)
- Allows rotation when profiles have different keys

---

## Dependencies

### Linux/macOS
- **bash** (4.0+)
- **GNU getopt** (enhanced version, not BSD getopt)
- **jq** (JSON processor)
- **aws-cli** (AWS Command Line Interface)
- **Standard utilities:** grep, sed, awk, etc.

### Windows
- **PowerShell** (5.1+)
- **AWSPowerShell** module
- **AWS CLI** (for verification only)

---

## Error Handling

### Robust Error Detection

```bash
# Set strict error handling
set -eu -o errexit -o pipefail -o noclobber -o nounset
```

**Behaviors:**
- `-e`: Exit on any command failure
- `-u`: Error on undefined variables
- `-o pipefail`: Fail on pipe errors
- `-o noclobber`: Prevent file overwrite accidents

### Specific Error Cases

1. **Missing Configuration**
   - Exits if profile not found in `~/.aws/credentials`
   - Shows current profile configuration with `aws configure list`

2. **Multiple Access Keys**
   - Requires exactly 1 key unless `--force` used
   - Can auto-delete extras in force mode

3. **Key Creation Failure**
   - Detects empty/null response from AWS
   - Exits without making changes

4. **New Key Verification Failure**
   - Rolls back by deleting new key
   - Restores old key in environment
   - Safe exit without orphaned credentials

---

## Scheduling Mechanisms

### Linux (cron)

**Entry Format:**
```cron
MM 2 * * * /usr/bin/aws-rotate-iam-keys --profile default >/dev/null
```

**Characteristics:**
- Random minute (0-59) to distribute load
- 2 AM local time
- Output suppressed (`>/dev/null`)
- May skip if computer sleeping

### macOS (launchd)

**Service Definition:**
```ruby
cron "23 3 * * *"
run_at_load true
```

**Advantages over cron:**
- Runs missed jobs on wake
- Better reliability for laptops
- Managed by `brew services`

**Configuration:**
- Global: `$(brew --prefix)/etc/aws-rotate-iam-keys`
- User: `~/.aws-rotate-iam-keys`

### Windows (Task Scheduler)

**Task Creation:**
```powershell
schtasks /create /f /tn "AWS Rotate IAM Keys" 
    /tr "Powershell.exe -ExecutionPolicy Bypass ..." 
    /sc daily 
    /st HH:MM
```

**Features:**
- Random time 2-6 AM
- Hidden window execution
- Auto-created on first script run

---

## File Structure

```
aws-rotate-iam-keys/
├── src/
│   ├── bin/
│   │   └── aws-rotate-iam-keys          # Main bash script
│   ├── debian/                           # Debian packaging files
│   │   ├── changelog                     # Package changelog
│   │   ├── control-debian                # Debian control template
│   │   ├── control-ubuntu                # Ubuntu control template
│   │   ├── postinst                      # Post-installation script
│   │   ├── prerm                         # Pre-removal script
│   │   └── rules                         # Build rules
│   └── Makefile                          # Installation rules
├── Formula/
│   └── aws-rotate-iam-keys.rb           # Homebrew formula
├── Windows/
│   └── aws-rotate-iam-keys.ps1          # PowerShell script
├── build.sh                              # Debian/Ubuntu package builder
├── docker.sh                             # Docker container runner
├── upload.sh                             # Release upload script
├── Dockerfile                            # Docker image definition
└── README.md                             # User documentation
```

---

## Docker Support

The `docker.sh` script provides containerized execution:

```bash
# Build Docker image
docker build -t aws-rotate-iam-keys .

# Run with volume mount
docker run -it --rm \
    -v "${PWD}":/root/aws-rotate-iam-keys \
    -w /root/aws-rotate-iam-keys \
    aws-rotate-iam-keys
```

**Use cases:**
- Testing builds
- Cross-platform development
- CI/CD pipelines

---

## Code Quality Observations

### Strengths

1. **Defensive Programming**
   - Strict error handling (`set -eu`)
   - Input validation at multiple stages
   - Rollback mechanisms on failure

2. **Platform Compatibility**
   - Handles GNU getopt vs BSD getopt
   - Checks for required tools before execution
   - Platform-specific implementations

3. **User Experience**
   - Clear progress messages
   - Helpful error messages with context
   - Safe defaults (rotates 'default' profile)

4. **Idempotency**
   - Can be run multiple times safely
   - Handles edge cases (multiple keys, etc.)

### Areas for Improvement

1. **Windows Script Simplicity**
   - No retry logic for new key verification
   - Less robust error handling than bash version

2. **Testing**
   - No automated test suite
   - Manual testing required

3. **Documentation**
   - Inline code comments sparse in bash script
   - Logic could benefit from more explanation

---

## Distribution Channels

1. **Ubuntu PPA**
   - `ppa:rhyeal/aws-rotate-iam-keys`
   - Automatic updates via apt

2. **Homebrew Tap**
   - Custom tap installation
   - Service management via `brew services`

3. **Direct Download**
   - .deb packages from GitHub releases
   - PowerShell script direct download

4. **Git Clone**
   - Manual installation from source
   - For unsupported platforms

---

## Configuration Management

### Profile Configuration

**Single line per invocation:**
```
--profile default
--profiles profile1,profile2
--profile another-profile
```

### Credential Storage

**Linux/macOS:** `~/.aws/credentials`
```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
region = us-east-1
```

**Windows:** 
- `C:\Users\username\.aws\credentials`
- `AppData\Local\AWSToolkit\RegisteredAccounts.json`

---

## Real-World Usage Scenarios

### Scenario 1: Single User, Single Computer
```bash
# Installation
brew install aws-rotate-iam-keys
brew services start aws-rotate-iam-keys

# Keys rotate automatically every night
```

### Scenario 2: Multiple AWS Profiles
```bash
# Config: ~/.aws-rotate-iam-keys
--profile work
--profile personal
--profiles shared-dev,shared-prod
```

### Scenario 3: Multi-Computer Setup
```bash
# Use file sync service to share ~/.aws/credentials
# Only run rotation on ONE computer
# Synced credentials propagate to other computers
```

### Scenario 4: Manual Rotation
```bash
# One-time rotation before important work
aws-rotate-iam-keys --profile production

# Verify new keys
aws iam list-access-keys --profile production
```

---

## Technical Insights

### Why Parse Arguments This Way?

The script uses GNU getopt for robust argument parsing:

```bash
! PARSED=$(getopt --options=hvfp: --longoptions=force,profile:,profiles:,version,help --name "$0" -- "$@")
```

**Benefits:**
- Handles long and short options
- Properly quotes arguments
- Validates option syntax
- POSIX compliant

### Why the Retry Loop?

```bash
for i in $(seq 1 20); do
    ERROR=$(aws iam list-access-keys 2>&1 1>/dev/null) && break || sleep 3
done
```

**AWS IAM Eventual Consistency:**
- New keys aren't immediately available globally
- Can take up to 60 seconds to propagate
- Retry loop handles this gracefully

### Why Export Then Update Credentials?

```bash
export AWS_ACCESS_KEY_ID=$NEW_ACCESS_KEY_ID
# ... update credentials file ...
aws iam delete-access-key --access-key-id $OLD_ACCESS_KEY_ID
```

**Reason:** After updating credentials file, if we used `--profile`, AWS CLI would try to use the new key from the file, but environment variables take precedence. This ensures we can still delete the old key even after updating the file.

---

## Conclusion

**aws-rotate-iam-keys** is a well-designed, production-ready tool that solves a real security problem with minimal user friction. The implementation shows careful consideration of:

- Security best practices
- Cross-platform compatibility  
- Error handling and recovery
- User experience
- AWS API quirks and limitations

The project demonstrates solid software engineering principles while maintaining simplicity—it's just a bash script (and a PowerShell script) with good packaging around it. This makes it auditable, maintainable, and trustworthy for managing sensitive AWS credentials.

**Core Philosophy:** Make security easier by reducing it to less than 3 lines of copy-paste commands, then automating it completely.

---

## Additional Resources

- **GitHub Repository:** https://github.com/rhyeal/aws-rotate-iam-keys
- **Website:** https://aws-rotate-iam-keys.com
- **Author Contact:** awsRotateKeys@rhyeal.com
- **AWS IAM Best Practices:** https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
