# AWS Rotate IAM Keys - Workflow Diagrams

## Complete Key Rotation Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    START: aws-rotate-iam-keys                    │
│                    (Manual or Scheduled Run)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 1: Parse Command Line Arguments                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ • --profile <name>      : Single profile                  │  │
│  │ • --profiles <n1,n2>    : Multiple profiles (shared key) │  │
│  │ • --force               : Force rotation                  │  │
│  │ • --version / --help    : Info commands                   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                  Default: "default" profile                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Step 2: Verify Configuration for Each Profile            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ For each profile:                                         │  │
│  │   ✓ Load aws_access_key_id                              │  │
│  │   ✓ Load aws_secret_access_key                          │  │
│  │   ✓ Load region                                          │  │
│  │   ✗ Exit if any missing                                  │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 3: Validate Keys Are Identical                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ If multiple profiles specified:                          │  │
│  │   Check all profiles use SAME access key                 │  │
│  │   ├─ Different keys + no --force → EXIT ERROR           │  │
│  │   └─ Different keys + --force    → WARN and CONTINUE    │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│             Step 4: Set Up AWS Environment Variables             │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ export AWS_ACCESS_KEY_ID=<current_key>                   │  │
│  │ export AWS_SECRET_ACCESS_KEY=<current_secret>            │  │
│  │ export AWS_DEFAULT_REGION=<region>                       │  │
│  │ export AWS_PAGER=""           # Disable pagination       │  │
│  │ export AWS_SESSION_TOKEN=""   # Clear temp credentials   │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│          Step 5: Verify Current Key Count (Pre-Check)            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ KEY_COUNT = aws iam list-access-keys | jq 'length'       │  │
│  │                                                            │  │
│  │ If KEY_COUNT > 1:                                         │  │
│  │   ├─ No --force → EXIT ERROR                             │  │
│  │   └─ With --force:                                        │  │
│  │       • Delete all keys except current                    │  │
│  │       • Continue with rotation                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│  AWS Limit: Maximum 2 keys per IAM user                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               Step 6: Create New Access Key                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ RESPONSE = aws iam create-access-key --output json       │  │
│  │ NEW_ACCESS_KEY_ID = jq '.AccessKey.AccessKeyId'          │  │
│  │ NEW_SECRET_ACCESS_KEY = jq '.AccessKey.SecretAccessKey'  │  │
│  │                                                            │  │
│  │ Status: User now has 2 active keys (old + new)           │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│            Step 7: Verify New Key Works (Critical!)              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ # Switch to new key in environment                        │  │
│  │ export AWS_ACCESS_KEY_ID=$NEW_ACCESS_KEY_ID              │  │
│  │ export AWS_SECRET_ACCESS_KEY=$NEW_SECRET_ACCESS_KEY      │  │
│  │                                                            │  │
│  │ # Retry up to 20 times (60 seconds total)                │  │
│  │ for i in 1..20:                                           │  │
│  │   test_result = aws iam list-access-keys                 │  │
│  │   if success: break                                       │  │
│  │   else: sleep 3 seconds                                   │  │
│  │                                                            │  │
│  │ If still failing after 60 seconds:                        │  │
│  │   ├─ DELETE new key (cleanup)                            │  │
│  │   ├─ RESTORE old key in environment                      │  │
│  │   └─ EXIT with error                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│  Note: AWS IAM has eventual consistency; new keys take time     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Step 8: Update Credentials File(s)                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ For each profile in profiles list:                        │  │
│  │   Update ~/.aws/credentials:                              │  │
│  │   ├─ aws_access_key_id = NEW_ACCESS_KEY_ID              │  │
│  │   └─ aws_secret_access_key = NEW_SECRET_ACCESS_KEY      │  │
│  │                                                            │  │
│  │ Commands:                                                  │  │
│  │   aws configure set aws_access_key_id <new> --profile X  │  │
│  │   aws configure set aws_secret_access_key <new> --profile│  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              Step 9: Delete Old Access Key                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ aws iam delete-access-key --access-key-id OLD_KEY_ID     │  │
│  │                                                            │  │
│  │ Safe to delete now because:                               │  │
│  │   ✓ New key verified working                             │  │
│  │   ✓ Credentials file updated                             │  │
│  │   ✓ Environment still using new key                      │  │
│  └───────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Step 10: Success!                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Display:                                                   │  │
│  │   • "Keys rotated"                                        │  │
│  │   • New key ID                                            │  │
│  │   • Deleted old key ID                                    │  │
│  │                                                            │  │
│  │ Result:                                                    │  │
│  │   • All specified profiles updated                        │  │
│  │   • Only 1 active key remaining (new)                     │  │
│  │   • Old key permanently deleted                           │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Error Handling & Recovery Paths

```
                        ┌──────────────────┐
                        │   Any Step       │
                        │   Encounters     │
                        │   Error          │
                        └────────┬─────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Config Missing  │    │  AWS API Error  │    │  Key Count > 1  │
│                 │    │                 │    │                 │
│ • Missing       │    │ • Network fail  │    │ Without --force:│
│   credentials   │    │ • Permission    │    │   → Exit error  │
│ • Invalid       │    │   denied        │    │                 │
│   profile       │    │ • Throttling    │    │ With --force:   │
│                 │    │                 │    │   → Delete extra│
│ Action:         │    │ Action:         │    │   → Continue    │
│ → Exit Error    │    │ → Exit Error    │    │                 │
│ → Show config   │    │ → Show AWS msg  │    │ Action:         │
└─────────────────┘    └─────────────────┘    │ → As specified  │
                                               └─────────────────┘

         ┌─────────────────────────────────┐
         │   CRITICAL: New Key Verify Fail │
         │   (Step 7 Failure)              │
         └────────┬────────────────────────┘
                  │
                  ▼
         ┌─────────────────────────────────┐
         │    Automatic Rollback:          │
         │    1. Delete new key from AWS   │
         │    2. Restore old key in env    │
         │    3. Exit with error           │
         │                                 │
         │ Result: No changes made         │
         │         System left in original │
         │         working state           │
         └─────────────────────────────────┘
```

---

## Scheduling Architecture

### Three-Tier Scheduling System

```
┌─────────────────────────────────────────────────────────────┐
│                   Operating System Layer                     │
└───────────┬─────────────────┬─────────────────┬─────────────┘
            │                 │                 │
    ┌───────▼──────┐  ┌──────▼──────┐  ┌──────▼──────┐
    │   Linux      │  │    macOS    │  │   Windows   │
    │   (cron)     │  │  (launchd)  │  │   (Task     │
    │              │  │             │  │  Scheduler)  │
    └───────┬──────┘  └──────┬──────┘  └──────┬──────┘
            │                │                │
            ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│              Cron Entry / Service Definition                 │
│                                                              │
│  Linux:   MM 2 * * * /usr/bin/aws-rotate-iam-keys ...      │
│  macOS:   cron "23 3 * * *" + run_at_load                  │
│  Windows: schtasks /create ... /sc daily /st HH:MM         │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                Configuration File (Optional)                 │
│                                                              │
│  macOS:   ~/.aws-rotate-iam-keys or                        │
│           $(brew --prefix)/etc/aws-rotate-iam-keys         │
│                                                              │
│  Content (one invocation per line):                         │
│    --profile default                                        │
│    --profiles work,personal                                 │
│    --profile special --force                                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Script Execution                                │
│                                                              │
│  Each line → one execution of aws-rotate-iam-keys           │
│                                                              │
│  Logs:                                                       │
│  • syslog (when no TTY)                                     │
│  • /tmp/homebrew.mxcl.aws-rotate-iam-keys.log (macOS)      │
│  • Task Scheduler logs (Windows)                            │
└─────────────────────────────────────────────────────────────┘
```

### Time Distribution Strategy

```
┌─────────────────────────────────────────────────────────────┐
│         Why Random Times? Load Distribution                  │
└─────────────────────────────────────────────────────────────┘

Without Randomization:
─────────────────────────────────────────────────────────────
All users hit AWS API at same time
    │
    ▼
AWS: ┌────┐
     │████│ ← Spike at 2:00 AM
     │    │
     └────┘

With Randomization:
─────────────────────────────────────────────────────────────
Users distributed across time window
    │
    ▼
AWS: ┌────┐
     │▓▓▓▓│ ← Spread load 2:00-6:00 AM
     └────┘

Implementation:
• Linux/Ubuntu:   Random minute (0-59) at 2 AM
• macOS:          Fixed at 3:23 AM (per formula)
• Windows:        Random hour (2-6 AM) + random minute
```

---

## Multi-Profile Scenarios

### Scenario 1: Single Shared Key Across Multiple Profiles

```
BEFORE Rotation:
─────────────────────────────────────────
~/.aws/credentials:
[work]
aws_access_key_id = AKIA...OLD
aws_secret_access_key = abc...old

[personal]
aws_access_key_id = AKIA...OLD  ← Same key
aws_secret_access_key = abc...old

[shared]
aws_access_key_id = AKIA...OLD  ← Same key
aws_secret_access_key = abc...old

Command:
$ aws-rotate-iam-keys --profiles work,personal,shared

AFTER Rotation:
─────────────────────────────────────────
[work]
aws_access_key_id = AKIA...NEW
aws_secret_access_key = xyz...new

[personal]
aws_access_key_id = AKIA...NEW  ← Same NEW key
aws_secret_access_key = xyz...new

[shared]
aws_access_key_id = AKIA...NEW  ← Same NEW key
aws_secret_access_key = xyz...new

Result: All three profiles updated atomically
```

### Scenario 2: Different Keys for Different Profiles

```
BEFORE Rotation:
─────────────────────────────────────────
~/.aws/credentials:
[work]
aws_access_key_id = AKIA...WORK_OLD
aws_secret_access_key = abc...work_old

[personal]
aws_access_key_id = AKIA...PERS_OLD
aws_secret_access_key = xyz...pers_old

Commands (separate invocations):
$ aws-rotate-iam-keys --profile work
$ aws-rotate-iam-keys --profile personal

AFTER Rotation:
─────────────────────────────────────────
[work]
aws_access_key_id = AKIA...WORK_NEW
aws_secret_access_key = abc...work_new

[personal]
aws_access_key_id = AKIA...PERS_NEW
aws_secret_access_key = xyz...pers_new

Result: Each profile has its own unique key pair
```

---

## AWS IAM State Transitions

```
┌─────────────────────────────────────────────────────────────┐
│                    IAM User State                            │
└─────────────────────────────────────────────────────────────┘

Initial State:
───────────────────────────────────────────────────────────────
AWS IAM: 1 Active Key
         ├─ AKIA...OLD123 (Active, Created: 30 days ago)

Local:   ~/.aws/credentials
         └─ aws_access_key_id = AKIA...OLD123


During Rotation:
───────────────────────────────────────────────────────────────
Step 6 - After Create:
AWS IAM: 2 Active Keys  ← Maximum reached
         ├─ AKIA...OLD123 (Active)
         └─ AKIA...NEW456 (Active, just created)

Local:   ~/.aws/credentials
         └─ aws_access_key_id = AKIA...OLD123  (not yet updated)


Step 8 - After Update:
AWS IAM: 2 Active Keys  
         ├─ AKIA...OLD123 (Active, will be deleted)
         └─ AKIA...NEW456 (Active, verified working)

Local:   ~/.aws/credentials
         └─ aws_access_key_id = AKIA...NEW456  ← Updated


Final State:
───────────────────────────────────────────────────────────────
AWS IAM: 1 Active Key
         └─ AKIA...NEW456 (Active, just rotated)

Local:   ~/.aws/credentials
         └─ aws_access_key_id = AKIA...NEW456

Old key AKIA...OLD123 permanently deleted
```

---

## Eventual Consistency Handling

```
┌─────────────────────────────────────────────────────────────┐
│   AWS IAM Propagation: Why the 60-Second Retry Loop?        │
└─────────────────────────────────────────────────────────────┘

Problem:
AWS IAM is eventually consistent, not immediately consistent

Create Key at t=0:
───────────────────────────────────────────────────────────────
t=0s:  aws iam create-access-key
       │
       ├─ Key created in IAM database
       ├─ Returns: AKIA...NEW + secret
       │
       └─ BUT: Key not yet propagated globally

t=1s:  Immediate use attempt
       │
       └─> ERROR: "InvalidAccessKeyId" or "SignatureDoesNotMatch"

Why?
AWS uses distributed systems:
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  us-east-1  │    │  eu-west-1  │    │  ap-south-1 │
│  ✓ Has key  │    │  ⏳ Waiting  │    │  ⏳ Waiting  │
└─────────────┘    └─────────────┘    └─────────────┘


Solution: Retry Loop with Exponential Backoff
───────────────────────────────────────────────────────────────
for i in 1..20:  # 20 attempts × 3 seconds = 60 seconds max
    try:
        aws iam list-access-keys  # Test if new key works
        success → break
    except:
        sleep 3 seconds
        continue

Timeline:
t=0s:   Create key
t=1s:   Test (fail) → sleep 3s
t=4s:   Test (fail) → sleep 3s
t=7s:   Test (fail) → sleep 3s
t=10s:  Test (fail) → sleep 3s
t=13s:  Test (SUCCESS!) → proceed
        │
        └─> Key fully propagated, safe to use

Fallback:
After 60 seconds of retries:
  → Assume propagation failed
  → Delete new key
  → Restore old key
  → Exit with error
```

---

## Security Model

```
┌─────────────────────────────────────────────────────────────┐
│              Minimum Required IAM Permissions                │
└─────────────────────────────────────────────────────────────┘

{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "iam:ListAccessKeys",      ← Check current keys
      "iam:CreateAccessKey",     ← Make new key
      "iam:DeleteAccessKey"      ← Remove old key
    ],
    "Resource": [
      "arn:aws:iam::*:user/${aws:username}"  ← Self only
    ]
  }]
}

Key Points:
• User can ONLY manage their OWN keys
• Cannot affect other IAM users
• Cannot modify IAM policies
• Cannot access other IAM resources
• Principle of least privilege


Threat Model:
───────────────────────────────────────────────────────────────
✓ Protected Against:
  • Stolen old keys after rotation
  • Long-lived credentials
  • Compliance violations (90-day rules)

⚠ Potential Risks:
  • Keys in environment during execution (brief)
  • Keys in process list (very brief)
  • Logs may contain error messages
  • Multi-device sync conflicts

Mitigations:
  • Fast execution time (~10 seconds)
  • Redirect output to /dev/null in cron
  • Clear session tokens before use
  • Rollback on any failure
```

---

## Platform-Specific Execution Paths

```
                    ┌──────────────────────┐
                    │   User Invokes       │
                    │ aws-rotate-iam-keys  │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
    ┌────────────────┐ ┌──────────────┐ ┌──────────────┐
    │     Linux      │ │    macOS     │ │   Windows    │
    │   /usr/bin/    │ │ /usr/local/  │ │  PowerShell  │
    │ aws-rotate-... │ │    bin/...   │ │    Script    │
    └────────┬───────┘ └──────┬───────┘ └──────┬───────┘
             │                │                 │
             ▼                ▼                 ▼
    ┌────────────────────────────────────────────────────┐
    │           Bash Script          │  PowerShell Script│
    │                                │                   │
    │  • GNU getopt parsing          │ • param() parsing │
    │  • aws cli commands            │ • AWSPowerShell   │
    │  • jq for JSON                 │ • Native objects  │
    │  • 60s retry loop              │ • No retry        │
    │  • Syslog integration          │ • Event Log       │
    └────────────────┬───────────────┴───────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────────────────────┐
    │               AWS IAM API                          │
    │                                                     │
    │  • list-access-keys                                │
    │  • create-access-key                               │
    │  • delete-access-key                               │
    └────────────────┬───────────────────────────────────┘
                     │
                     ▼
    ┌────────────────────────────────────────────────────┐
    │          Local Credentials File                    │
    │                                                     │
    │  Linux/macOS:  ~/.aws/credentials                  │
    │  Windows:      C:\Users\X\.aws\credentials         │
    └────────────────────────────────────────────────────┘
```

