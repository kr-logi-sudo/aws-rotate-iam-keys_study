#!/usr/bin/env python3
"""
AWS Rotate IAM Keys - Python Implementation

A tool to automatically rotate AWS IAM access keys following security best practices.
This script automates the rotation of AWS IAM access keys to help maintain compliance
with security standards that recommend key rotation every 30-90 days.

Author: Adapted from aws-rotate-iam-keys bash implementation
Version: 1.0.0
License: GNU General Public License
"""

import argparse
import sys
import os
import time
import json
import configparser
from pathlib import Path
import boto3
from botocore.exceptions import ClientError, ProfileNotFound


class AWSKeyRotator:
    """Handles the rotation of AWS IAM access keys."""
    
    VERSION = "1.0.0"
    MAX_RETRY_ATTEMPTS = 20
    RETRY_DELAY = 3  # seconds
    
    def __init__(self, profiles, force=False):
        """
        Initialize the key rotator.
        
        Args:
            profiles (list): List of AWS profile names to rotate
            force (bool): Force rotation even if multiple keys exist
        """
        self.profiles = profiles if isinstance(profiles, list) else [profiles]
        self.force = force
        self.credentials_path = Path.home() / '.aws' / 'credentials'
        self.config = None
        
    def log(self, message):
        """Print log message to stdout."""
        print(message)
        
    def error(self, message):
        """Print error message to stderr and exit."""
        print(f"ERROR: {message}", file=sys.stderr)
        sys.exit(1)
        
    def verify_credentials_file(self):
        """Verify that the AWS credentials file exists."""
        if not self.credentials_path.exists():
            self.error(f"AWS credentials file not found at {self.credentials_path}")
            
    def load_credentials(self):
        """Load AWS credentials from the credentials file."""
        self.log("Verifying configuration")
        self.verify_credentials_file()
        
        self.config = configparser.ConfigParser()
        self.config.read(self.credentials_path)
        
        # Verify all profiles exist and have required keys
        credentials = {}
        for profile in self.profiles:
            if profile not in self.config:
                self.error(f"Profile '{profile}' not found in {self.credentials_path}")
                
            if 'aws_access_key_id' not in self.config[profile]:
                self.error(f"aws_access_key_id not found for profile '{profile}'")
                
            if 'aws_secret_access_key' not in self.config[profile]:
                self.error(f"aws_secret_access_key not found for profile '{profile}'")
                
            credentials[profile] = {
                'access_key_id': self.config[profile]['aws_access_key_id'],
                'secret_access_key': self.config[profile]['aws_secret_access_key'],
                'region': self.config[profile].get('region', 'us-east-1')
            }
            
        # If multiple profiles, verify they have the same key
        if len(self.profiles) > 1:
            first_key = credentials[self.profiles[0]]['access_key_id']
            for profile in self.profiles[1:]:
                if credentials[profile]['access_key_id'] != first_key:
                    if not self.force:
                        self.error(
                            f"Profiles have different access keys. "
                            f"Use --force to rotate them anyway or rotate separately."
                        )
                    else:
                        self.log(f"WARNING: Profiles have different keys, continuing with --force")
                        
        return credentials
        
    def get_iam_client(self, credentials):
        """
        Create and return an IAM client using the provided credentials.
        
        Args:
            credentials (dict): Dictionary containing AWS credentials
            
        Returns:
            boto3.client: Configured IAM client
        """
        return boto3.client(
            'iam',
            aws_access_key_id=credentials['access_key_id'],
            aws_secret_access_key=credentials['secret_access_key'],
            region_name=credentials['region']
        )
        
    def get_current_username(self, iam_client):
        """
        Get the current IAM username.
        
        Args:
            iam_client: Boto3 IAM client
            
        Returns:
            str: IAM username
        """
        try:
            user = iam_client.get_user()
            return user['User']['UserName']
        except ClientError as e:
            self.error(f"Failed to get current user: {e}")
            
    def check_key_count(self, iam_client, username, current_key_id):
        """
        Check the number of existing access keys and handle accordingly.
        
        Args:
            iam_client: Boto3 IAM client
            username (str): IAM username
            current_key_id (str): Current access key ID
            
        Returns:
            bool: True if safe to proceed, False otherwise
        """
        try:
            response = iam_client.list_access_keys(UserName=username)
            keys = response['AccessKeyMetadata']
            
            if len(keys) > 1:
                if not self.force:
                    self.error(
                        f"User has {len(keys)} access keys (maximum is 2). "
                        f"Delete one manually or use --force flag."
                    )
                else:
                    # Delete extra keys that are not the current one
                    self.log(f"WARNING: Found {len(keys)} keys, deleting extras with --force")
                    for key in keys:
                        if key['AccessKeyId'] != current_key_id:
                            self.log(f"Deleting extra key {key['AccessKeyId']}")
                            iam_client.delete_access_key(
                                UserName=username,
                                AccessKeyId=key['AccessKeyId']
                            )
                            
            return True
        except ClientError as e:
            self.error(f"Failed to list access keys: {e}")
            
    def create_new_key(self, iam_client, username):
        """
        Create a new access key.
        
        Args:
            iam_client: Boto3 IAM client
            username (str): IAM username
            
        Returns:
            dict: New access key credentials
        """
        try:
            self.log("Creating new access key")
            response = iam_client.create_access_key(UserName=username)
            key_data = response['AccessKey']
            
            new_credentials = {
                'access_key_id': key_data['AccessKeyId'],
                'secret_access_key': key_data['SecretAccessKey']
            }
            
            self.log(f"Created new key {new_credentials['access_key_id']}")
            return new_credentials
        except ClientError as e:
            self.error(f"Failed to create new access key: {e}")
            
    def verify_new_key(self, new_credentials, region):
        """
        Verify that the new access key works by testing it.
        Uses retry logic to handle AWS eventual consistency.
        
        Args:
            new_credentials (dict): New access key credentials
            region (str): AWS region
            
        Returns:
            bool: True if key works, False otherwise
        """
        self.log("Verifying new key works (may take up to 60 seconds)")
        
        for attempt in range(1, self.MAX_RETRY_ATTEMPTS + 1):
            try:
                # Try to use the new key to list access keys
                test_client = boto3.client(
                    'iam',
                    aws_access_key_id=new_credentials['access_key_id'],
                    aws_secret_access_key=new_credentials['secret_access_key'],
                    region_name=region
                )
                
                # Simple test to verify the key works
                test_client.list_access_keys()
                self.log(f"New key verified successfully on attempt {attempt}")
                return True
                
            except ClientError as e:
                if attempt < self.MAX_RETRY_ATTEMPTS:
                    self.log(f"Key not yet active (attempt {attempt}/{self.MAX_RETRY_ATTEMPTS}), retrying...")
                    time.sleep(self.RETRY_DELAY)
                else:
                    self.log(f"Failed to verify new key after {self.MAX_RETRY_ATTEMPTS} attempts")
                    return False
                    
        return False
        
    def update_credentials_file(self, new_credentials):
        """
        Update the credentials file with new access key.
        
        Args:
            new_credentials (dict): New access key credentials
        """
        try:
            self.log("Updating credentials file")
            
            for profile in self.profiles:
                self.config[profile]['aws_access_key_id'] = new_credentials['access_key_id']
                self.config[profile]['aws_secret_access_key'] = new_credentials['secret_access_key']
                self.log(f"Updated profile: {profile}")
                
            # Write back to file
            with open(self.credentials_path, 'w') as f:
                self.config.write(f)
                
        except Exception as e:
            self.error(f"Failed to update credentials file: {e}")
            
    def delete_old_key(self, iam_client, username, old_key_id):
        """
        Delete the old access key.
        
        Args:
            iam_client: Boto3 IAM client
            username (str): IAM username
            old_key_id (str): Old access key ID to delete
        """
        try:
            self.log("Deleting old access key")
            iam_client.delete_access_key(
                UserName=username,
                AccessKeyId=old_key_id
            )
            self.log(f"Deleted old key {old_key_id}")
        except ClientError as e:
            self.error(f"Failed to delete old access key: {e}")
            
    def cleanup_new_key(self, iam_client, username, new_key_id):
        """
        Cleanup: Delete a newly created key if verification failed.
        
        Args:
            iam_client: Boto3 IAM client
            username (str): IAM username
            new_key_id (str): New access key ID to delete
        """
        try:
            self.log(f"Cleaning up: Deleting new key {new_key_id}")
            iam_client.delete_access_key(
                UserName=username,
                AccessKeyId=new_key_id
            )
        except ClientError as e:
            self.log(f"WARNING: Failed to cleanup new key: {e}")
            
    def rotate(self):
        """
        Main rotation logic.
        Executes the complete key rotation workflow.
        """
        self.log(f"Rotating keys for profiles: {', '.join(self.profiles)}")
        
        # Step 1: Load and verify credentials
        credentials = self.load_credentials()
        
        # Use the first profile's credentials for rotation
        primary_profile = self.profiles[0]
        primary_creds = credentials[primary_profile]
        
        # Step 2: Create IAM client
        self.log("Verifying credentials")
        iam_client = self.get_iam_client(primary_creds)
        
        # Step 3: Get current username
        username = self.get_current_username(iam_client)
        
        # Step 4: Check current key count
        old_key_id = primary_creds['access_key_id']
        self.check_key_count(iam_client, username, old_key_id)
        
        # Step 5: Create new key
        new_credentials = self.create_new_key(iam_client, username)
        
        # Step 6: Verify new key works
        if not self.verify_new_key(new_credentials, primary_creds['region']):
            # Rollback: delete the new key
            self.cleanup_new_key(iam_client, username, new_credentials['access_key_id'])
            self.error("New key verification failed. Rolled back changes.")
            
        # Step 7: Update credentials file
        self.update_credentials_file(new_credentials)
        
        # Step 8: Delete old key
        self.delete_old_key(iam_client, username, old_key_id)
        
        # Success!
        self.log("Keys rotated successfully")
        

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Rotate AWS IAM access keys automatically',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              # Rotate default profile
  %(prog)s --profile myProfile          # Rotate specific profile
  %(prog)s --profiles dev,staging       # Rotate multiple profiles with same key
  %(prog)s --force                      # Force rotation even with 2 keys

For more information, visit: https://github.com/rhyeal/aws-rotate-iam-keys
        """
    )
    
    parser.add_argument(
        '--version', '-v',
        action='version',
        version=f'AWS Rotate IAM Keys (Python) v{AWSKeyRotator.VERSION}'
    )
    
    parser.add_argument(
        '--profile', '-p',
        dest='profile',
        help='AWS profile name to rotate'
    )
    
    parser.add_argument(
        '--profiles',
        dest='profiles',
        help='Comma-separated list of profiles to rotate with the same key'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force rotation even if user has 2 access keys'
    )
    
    args = parser.parse_args()
    
    # Determine which profiles to rotate
    if args.profiles:
        profiles = [p.strip() for p in args.profiles.split(',')]
    elif args.profile:
        profiles = [args.profile]
    else:
        profiles = ['default']
        
    # Create rotator and execute
    try:
        rotator = AWSKeyRotator(profiles, force=args.force)
        rotator.rotate()
    except KeyboardInterrupt:
        print("\nRotation interrupted by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
