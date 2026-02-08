# AWS Rotate IAM Keys - Python Script Documentation

## Overview

This document provides comprehensive documentation for `aws_rotate_iam_keys.py`, a Python implementation of the AWS IAM key rotation tool. This script automates the process of rotating AWS IAM access keys to help organizations maintain security compliance by regularly refreshing credentials.

---

## Table of Contents

- [What This Script Does](#what-this-script-does)
- [Why Use This Script](#why-use-this-script)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Command-Line Options](#command-line-options)
- [Configuration](#configuration)
- [Examples](#examples)
- [Error Handling](#error-handling)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)
- [Comparison with Bash Version](#comparison-with-bash-version)
- [API Reference](#api-reference)
- [Contributing](#contributing)

---

## What This Script Does

The `aws_rotate_iam_keys.py` script automates the rotation of AWS IAM access keys by:

1. **Reading** your current AWS credentials from `~/.aws/credentials`
2. **Creating** a new access key via the AWS IAM API
3. **Verifying** the new key works (with retry logic for AWS eventual consistency)
4. **Updating** your local credentials file with the new key
5. **Deleting** the old access key from AWS
6. **Rolling back** automatically if any step fails

**Result:** Your AWS access keys are refreshed without manual intervention, and your applications continue to work seamlessly.

---

## Why Use This Script

### Security Benefits
- ✓ **Compliance**: Meets AWS security best practices (rotate keys every 30-90 days)
- ✓ **Automation**: Eliminates manual key rotation errors
- ✓ **Safety**: Automatic rollback prevents credential loss
- ✓ **Auditability**: Clear logging of all rotation activities

### Compliance Standards
This tool helps meet:
- **PCI-DSS 8.2.4**: Change user passwords/passphrases every 90 days
- **NIST 800-53 IA-5**: Authenticator management requirements
- **CIS AWS Benchmark**: Rotate access keys every 90 days
- **SOC 2**: Access control and credential management requirements

---

## Installation

### Prerequisites

- Python 3.6 or higher
- AWS CLI configured (or at minimum, `~/.aws/credentials` file)
- Active AWS IAM user account
- Internet connection to reach AWS APIs

### Install Dependencies

```bash
# Install required Python package
pip install boto3

# Or install from requirements file
pip install -r requirements.txt
```

### Make Script Executable

```bash
# Make the script executable
chmod +x aws_rotate_iam_keys.py

# Optionally, move to a directory in your PATH
sudo cp aws_rotate_iam_keys.py /usr/local/bin/
```

### Verify Installation

```bash
# Test the script
./aws_rotate_iam_keys.py --version

# Or if installed globally
aws_rotate_iam_keys.py --version
```

---

## Dependencies

### Required Python Packages

```
boto3>=1.26.0        # AWS SDK for Python
```

### Required AWS Permissions

Your IAM user must have these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "iam:GetUser",
      "iam:ListAccessKeys",
      "iam:CreateAccessKey",
      "iam:DeleteAccessKey"
    ],
    "Resource": "arn:aws:iam::*:user/${aws:username}"
  }]
}
```

**Key points:**
- ✓ User can only manage their own keys (not other users)
- ✓ Follows principle of least privilege
- ✓ No administrative permissions required

---

## Usage

### Basic Usage

```bash
# Rotate default profile
./aws_rotate_iam_keys.py

# Rotate specific profile
./aws_rotate_iam_keys.py --profile myProfile

# Rotate multiple profiles with same key
./aws_rotate_iam_keys.py --profiles dev,staging,prod

# Force rotation even with 2 keys
./aws_rotate_iam_keys.py --force

# Show help
./aws_rotate_iam_keys.py --help

# Show version
./aws_rotate_iam_keys.py --version
```

### Automated Rotation with Cron

**Linux/macOS:**
```bash
# Edit crontab
crontab -e

# Add daily rotation at 2:00 AM
0 2 * * * /usr/local/bin/aws_rotate_iam_keys.py --profile default >> /var/log/aws-key-rotation.log 2>&1
```

**Windows Task Scheduler:**
```powershell
# Create scheduled task
$action = New-ScheduledTaskAction -Execute "python" -Argument "C:\path\to\aws_rotate_iam_keys.py"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "AWS Key Rotation"
```

---

## How It Works

### Rotation Workflow (10 Steps)

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Parse Command-Line Arguments                        │
│   • Determine which profile(s) to rotate                    │
│   • Check for --force flag                                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Load and Verify Credentials                         │
│   • Read ~/.aws/credentials                                 │
│   • Verify profiles exist                                   │
│   • Extract access_key_id and secret_access_key             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Validate Multiple Profiles (if applicable)          │
│   • Check if profiles use same key                          │
│   • Exit with error if different (unless --force)           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Create IAM Client                                   │
│   • Initialize boto3 IAM client with current credentials    │
│   • Verify credentials work                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Get Current Username                                │
│   • Call iam:GetUser API                                    │
│   • Extract IAM username                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Check Key Count                                     │
│   • Call iam:ListAccessKeys                                 │
│   • Verify user has < 2 keys (AWS limit is 2)              │
│   • Delete extras if --force flag provided                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Create New Access Key                               │
│   • Call iam:CreateAccessKey                                │
│   • Store new AccessKeyId and SecretAccessKey               │
│   • Log the new key ID                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 8: Verify New Key Works                                │
│   • Retry up to 20 times (60 seconds total)                │
│   • Test new key by calling iam:ListAccessKeys              │
│   • Wait for AWS eventual consistency                       │
│   • ROLLBACK if verification fails                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 9: Update Credentials File                             │
│   • Replace old key with new key in ~/.aws/credentials     │
│   • Update all specified profiles                           │
│   • Write changes to disk                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 10: Delete Old Key                                     │
│   • Call iam:DeleteAccessKey with old key ID               │
│   • Confirm deletion                                        │
│   • Log success                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
                 ✓ SUCCESS
```

### Key Features

#### 1. Eventual Consistency Handling
AWS IAM uses eventual consistency, meaning new keys may take seconds to propagate. The script:
- Retries API calls up to 20 times
- Waits 3 seconds between attempts
- Total wait time: up to 60 seconds

#### 2. Automatic Rollback
If verification fails:
- Deletes the newly created key
- Keeps the old key intact
- Exits with error message
- **No data loss or downtime**

#### 3. Multi-Profile Support
Two modes:
- **Same Key**: `--profiles dev,staging` - All profiles get identical keys
- **Different Keys**: Multiple separate runs - Each profile gets unique keys

---

## Command-Line Options

### `--profile` or `-p`
Rotate a single specific profile.

```bash
./aws_rotate_iam_keys.py --profile myProfile
```

### `--profiles`
Rotate multiple profiles that should share the same access key.

```bash
./aws_rotate_iam_keys.py --profiles dev,staging,prod
```

### `--force` or `-f`
Force rotation even if the user has 2 access keys (AWS maximum). Will delete extra keys.

```bash
./aws_rotate_iam_keys.py --force
```

### `--version` or `-v`
Display the script version.

```bash
./aws_rotate_iam_keys.py --version
```

### `--help` or `-h`
Display help message with usage examples.

```bash
./aws_rotate_iam_keys.py --help
```

---

## Configuration

### AWS Credentials File Format

The script reads from `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = AKIAIOSFODNN7EXAMPLE
aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
region = us-east-1

[work]
aws_access_key_id = AKIAI44QH8DHBEXAMPLE
aws_secret_access_key = je7MtGbClwBF/2Zp9Utk/h3yCo8nvbEXAMPLEKEY
region = us-west-2
```

### Required Fields per Profile
- `aws_access_key_id` - Your AWS access key ID (required)
- `aws_secret_access_key` - Your AWS secret access key (required)
- `region` - AWS region (optional, defaults to us-east-1)

---

## Examples

### Example 1: First-Time Manual Rotation

```bash
# Verify current key age
aws iam list-access-keys --profile default

# Rotate the key
./aws_rotate_iam_keys.py --profile default

# Verify new key was created
aws iam list-access-keys --profile default
```

**Output:**
```
Rotating keys for profiles: default
Verifying configuration
Verifying credentials
Creating new access key
Created new key AKIAIOSFODNN7EXAMPLE
Verifying new key works (may take up to 60 seconds)
New key verified successfully on attempt 1
Updating credentials file
Updated profile: default
Deleting old access key
Deleted old key AKIARCPUMEZ3BEXAMPLE
Keys rotated successfully
```

### Example 2: Multiple Profiles with Same Key

```bash
# Set up multiple profiles for same AWS user
./aws_rotate_iam_keys.py --profiles personal,laptop,desktop

# All three profiles now have identical new credentials
```

### Example 3: Handling 2-Key Limit Error

```bash
# If you get error about having 2 keys
./aws_rotate_iam_keys.py --force

# Script will automatically delete the extra key and continue
```

### Example 4: Separate Keys for Different Profiles

```bash
# Rotate work profile
./aws_rotate_iam_keys.py --profile work

# Rotate personal profile separately
./aws_rotate_iam_keys.py --profile personal

# Each profile now has different credentials
```

### Example 5: Automated Daily Rotation

**Create wrapper script** (`/usr/local/bin/rotate-aws-keys.sh`):
```bash
#!/bin/bash
/usr/local/bin/aws_rotate_iam_keys.py --profile default 2>&1 | logger -t aws-key-rotation
```

**Add to crontab:**
```bash
0 3 * * * /usr/local/bin/rotate-aws-keys.sh
```

---

## Error Handling

### Common Errors and Solutions

#### 1. Profile Not Found
```
ERROR: Profile 'myProfile' not found in /home/user/.aws/credentials
```

**Solution:**
```bash
# Create the profile
aws configure --profile myProfile
```

#### 2. Missing Credentials
```
ERROR: aws_access_key_id not found for profile 'default'
```

**Solution:**
```bash
# Configure the profile properly
aws configure --profile default
```

#### 3. More Than One Access Key
```
ERROR: User has 2 access keys (maximum is 2). Delete one manually or use --force flag.
```

**Solution:**
```bash
# Option 1: Use --force to auto-delete
./aws_rotate_iam_keys.py --force

# Option 2: Manually delete via AWS Console
# Go to IAM → Users → Security credentials → Delete extra key
```

#### 4. Permission Denied
```
ERROR: Failed to create new access key: AccessDenied
```

**Solution:**
Ensure your IAM user has the required permissions (see [Dependencies](#dependencies) section).

#### 5. Key Verification Failed
```
ERROR: New key verification failed. Rolled back changes.
```

**Solution:**
- Check internet connectivity
- Verify AWS service status
- Try again (may be temporary AWS issue)
- Check if IAM permissions are correct

---

## Security Considerations

### Best Practices

#### ✓ DO
- ✓ Run rotation regularly (daily or weekly)
- ✓ Use minimum required IAM permissions
- ✓ Monitor AWS CloudTrail for key creation/deletion events
- ✓ Keep the script and dependencies updated
- ✓ Use encrypted storage for the credentials file
- ✓ Set appropriate file permissions (`chmod 600 ~/.aws/credentials`)

#### ✗ DON'T
- ✗ Share your credentials file
- ✗ Commit credentials to version control
- ✗ Run rotation on multiple computers for the same IAM user simultaneously
- ✗ Disable logging (helpful for troubleshooting)
- ✗ Use `--force` without understanding implications

### File Permissions

Ensure your credentials file has secure permissions:
```bash
# Set restrictive permissions
chmod 600 ~/.aws/credentials

# Verify
ls -la ~/.aws/credentials
# Should show: -rw------- (owner read/write only)
```

### Monitoring Rotation

Set up CloudWatch alarms for:
- `CreateAccessKey` API calls
- `DeleteAccessKey` API calls
- Failed API attempts with old keys

---

## Troubleshooting

### Debug Mode

Add verbose logging by modifying the script:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Script Execution

```bash
# Test without actually rotating
# (inspect credentials first)
cat ~/.aws/credentials

# Run with verbose output
python3 -v aws_rotate_iam_keys.py --profile default
```

### Verify AWS Connectivity

```bash
# Test AWS API connectivity
aws sts get-caller-identity --profile default

# Check current keys
aws iam list-access-keys --profile default
```

### Common Issues

#### Script Hangs During Verification
- **Cause**: Slow AWS API propagation
- **Solution**: Wait up to 60 seconds; the script will timeout and rollback if needed

#### Credentials File Not Updated
- **Cause**: File permissions or write error
- **Solution**: Check file permissions and disk space

#### Import Error: boto3
- **Cause**: boto3 not installed
- **Solution**: `pip install boto3`

---

## Comparison with Bash Version

| Feature | Bash Version | Python Version |
|---------|--------------|----------------|
| **Platform Support** | Linux, macOS, Windows (PowerShell) | Linux, macOS, Windows |
| **Dependencies** | bash, jq, aws-cli, gnu-getopt | Python 3.6+, boto3 |
| **Code Readability** | Bash scripting | Object-oriented Python |
| **Error Handling** | Shell error codes | Python exceptions |
| **Testing** | Manual | Unit testable |
| **Extensibility** | Limited | High (Python ecosystem) |
| **Performance** | Fast (native tools) | Fast (boto3 SDK) |
| **Installation** | OS packages | pip install |

### When to Use Which Version

**Use Bash Version if:**
- You're on Linux/macOS exclusively
- You prefer native system tools
- You want OS package manager installation
- You're already using bash scripts

**Use Python Version if:**
- You need cross-platform compatibility
- You prefer Python for scripting
- You want to extend/customize functionality
- You need unit testing capabilities
- You work in Python-heavy environments

---

## API Reference

### Class: `AWSKeyRotator`

The main class that handles AWS IAM key rotation.

#### Constructor

```python
AWSKeyRotator(profiles, force=False)
```

**Parameters:**
- `profiles` (list): List of AWS profile names to rotate
- `force` (bool): Force rotation even if multiple keys exist

**Example:**
```python
rotator = AWSKeyRotator(['default'], force=False)
```

#### Methods

##### `rotate()`
Execute the complete key rotation workflow.

**Returns:** None  
**Raises:** `SystemExit` on error

**Example:**
```python
rotator = AWSKeyRotator(['default'])
rotator.rotate()
```

##### `verify_credentials_file()`
Verify that the AWS credentials file exists.

**Returns:** None  
**Raises:** `SystemExit` if file not found

##### `load_credentials()`
Load AWS credentials from the credentials file.

**Returns:** dict - Credentials for each profile  
**Raises:** `SystemExit` if profiles not found or invalid

##### `get_iam_client(credentials)`
Create and return an IAM client.

**Parameters:**
- `credentials` (dict): AWS credentials dictionary

**Returns:** boto3.client - Configured IAM client

##### `create_new_key(iam_client, username)`
Create a new access key via AWS IAM API.

**Parameters:**
- `iam_client`: Boto3 IAM client
- `username` (str): IAM username

**Returns:** dict - New credentials with access_key_id and secret_access_key

##### `verify_new_key(new_credentials, region)`
Verify that the new key works with retry logic.

**Parameters:**
- `new_credentials` (dict): New credentials to verify
- `region` (str): AWS region

**Returns:** bool - True if verified, False otherwise

##### `update_credentials_file(new_credentials)`
Update the credentials file with new keys.

**Parameters:**
- `new_credentials` (dict): New credentials to write

**Returns:** None

##### `delete_old_key(iam_client, username, old_key_id)`
Delete the old access key from AWS.

**Parameters:**
- `iam_client`: Boto3 IAM client
- `username` (str): IAM username
- `old_key_id` (str): Old access key ID to delete

**Returns:** None

---

## Advanced Usage

### Using as a Python Module

```python
#!/usr/bin/env python3
from aws_rotate_iam_keys import AWSKeyRotator

# Rotate default profile programmatically
try:
    rotator = AWSKeyRotator(['default'], force=False)
    rotator.rotate()
    print("Rotation successful!")
except Exception as e:
    print(f"Rotation failed: {e}")
```

### Custom Retry Logic

Modify retry parameters by editing the class constants:
```python
AWSKeyRotator.MAX_RETRY_ATTEMPTS = 30  # Increase to 90 seconds
AWSKeyRotator.RETRY_DELAY = 5          # Wait 5 seconds between retries
```

### Logging to File

```python
import logging

# Configure logging
logging.basicConfig(
    filename='/var/log/aws-key-rotation.log',
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)

# Add logging to AWSKeyRotator methods
```

---

## Testing

### Manual Testing

```bash
# Test with a non-production profile
./aws_rotate_iam_keys.py --profile test-profile

# Verify new key
aws iam list-access-keys --profile test-profile
```

### Automated Testing

Create a test suite:
```python
import unittest
from aws_rotate_iam_keys import AWSKeyRotator

class TestAWSKeyRotator(unittest.TestCase):
    def test_load_credentials(self):
        rotator = AWSKeyRotator(['default'])
        creds = rotator.load_credentials()
        self.assertIn('default', creds)
        
if __name__ == '__main__':
    unittest.main()
```

---

## Contributing

### How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Code Style

- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to all functions
- Keep functions focused and small

---

## License

This script is licensed under the GNU General Public License (GPL), compatible with the original aws-rotate-iam-keys project.

---

## Support and Resources

### Documentation
- **Study Summary**: See `STUDY_SUMMARY.md` for overview
- **Quick Reference**: See `QUICK_REFERENCE.md` for user guide
- **Workflow Diagrams**: See `WORKFLOW_DIAGRAM.md` for visual flows
- **Technical Analysis**: See `REVERSE_ENGINEERING_ANALYSIS.md` for deep dive

### External Resources
- **AWS IAM Documentation**: https://docs.aws.amazon.com/IAM/latest/UserGuide/
- **boto3 Documentation**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **Original Project**: https://github.com/rhyeal/aws-rotate-iam-keys

### Getting Help

- Open an issue on GitHub
- Check AWS IAM documentation
- Review CloudTrail logs for API errors
- Verify IAM permissions

---

## Version History

### v1.0.0 (Initial Release)
- Complete Python reimplementation
- Feature parity with bash version
- Enhanced error messages
- Object-oriented design
- Cross-platform support

---

## Summary

The `aws_rotate_iam_keys.py` script provides a robust, automated solution for rotating AWS IAM access keys. Key highlights:

✓ **Secure**: Automatic rollback on failures  
✓ **Reliable**: Handles AWS eventual consistency  
✓ **Simple**: Single command to rotate keys  
✓ **Safe**: No downtime during rotation  
✓ **Compliant**: Meets security best practices  

**Remember:** Security is easier when automated! Set up regular rotation and never worry about stale credentials again.

---

*Last Updated: February 8, 2026*
