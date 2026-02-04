#!/usr/bin/env python3
"""
Google OAuth Configuration Diagnostic Tool

This script helps diagnose Google OAuth configuration issues in Discussion Den.
Run this script to check if your Google OAuth is properly configured.

Usage: python check_oauth_config.py
"""

import os
import sys
from dotenv import load_dotenv

def check_oauth_config():
    """Check Google OAuth configuration and provide diagnostic information."""
    
    print("=" * 60)
    print("Discussion Den - Google OAuth Configuration Check")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    # Check environment variables
    print("\n1. ENVIRONMENT VARIABLES:")
    print("-" * 30)
    
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    
    print(f"GOOGLE_CLIENT_ID: {'✓ SET' if client_id else '✗ NOT SET'}")
    print(f"GOOGLE_CLIENT_SECRET: {'✓ SET' if client_secret else '✗ NOT SET'}")
    
    if client_id:
        print(f"  Value: {client_id[:20]}..." if len(client_id) > 20 else f"  Value: {client_id}")
    if client_secret:
        print(f"  Value: {client_secret[:10]}..." if len(client_secret) > 10 else f"  Value: {client_secret}")
    
    # Check for placeholder values
    print("\n2. CREDENTIAL VALIDATION:")
    print("-" * 30)
    
    def is_placeholder(value):
        """Check if value is a placeholder"""
        if not value:
            return True
        placeholder_patterns = [
            "your_google_client_id_here",
            "your_google_client_secret_here", 
            "your_client_id",
            "your_client_secret",
            "replace_with_your",
            "add_your_client_id",
            "add_your_client_secret"
        ]
        return value.lower() in placeholder_patterns
    
    client_id_valid = not is_placeholder(client_id)
    client_secret_valid = not is_placeholder(client_secret)
    
    print(f"Client ID Valid: {'✓ YES' if client_id_valid else '✗ NO (placeholder detected)'}")
    print(f"Client Secret Valid: {'✓ YES' if client_secret_valid else '✗ NO (placeholder detected)'}")
    
    # Overall status
    print("\n3. OVERALL STATUS:")
    print("-" * 30)
    
    if client_id_valid and client_secret_valid:
        print("✓ Google OAuth should work correctly")
        print("✓ Google login button will be visible")
        status = "CONFIGURED"
    elif client_id and client_secret:
        print("⚠ Google OAuth credentials are set but appear to be placeholders")
        print("⚠ Google login button will be hidden")
        print("⚠ Update .env file with real credentials from Google Cloud Console")
        status = "MISCONFIGURED"
    else:
        print("ℹ Google OAuth is not configured (optional feature)")
        print("ℹ Google login button will be hidden")
        print("ℹ Email/password authentication will work normally")
        status = "NOT_CONFIGURED"
    
    # Test OAuth registration
    print("\n4. OAUTH REGISTRATION TEST:")
    print("-" * 30)
    
    try:
        from extensions import oauth
        from app import create_app
        
        app = create_app()
        with app.app_context():
            if hasattr(oauth, 'google'):
                print("✓ Google OAuth client registered successfully")
            else:
                print("✗ Google OAuth client not registered")
                
    except Exception as e:
        print(f"✗ Error testing OAuth registration: {e}")
    
    # Recommendations
    print("\n5. RECOMMENDATIONS:")
    print("-" * 30)
    
    if status == "NOT_CONFIGURED":
        print("• Google OAuth is optional - your app will work fine without it")
        print("• To enable Google login:")
        print("  1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("  2. Create OAuth 2.0 credentials")
        print("  3. Update GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
        print("  4. Add redirect URI: http://localhost:5000/auth/google/callback")
        
    elif status == "MISCONFIGURED":
        print("• Replace placeholder values in .env with real Google OAuth credentials")
        print("• Get credentials from Google Cloud Console:")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. APIs & Services > Credentials")
        print("  3. Create OAuth 2.0 Client ID")
        print("  4. Copy Client ID and Client Secret to .env")
        
    elif status == "CONFIGURED":
        print("• Configuration looks good!")
        print("• Test Google login by starting the app and clicking 'Continue with Google'")
        print("• If issues persist, check Google Cloud Console configuration")
    
    print("\n6. NEXT STEPS:")
    print("-" * 30)
    print("• Start the app: python app.py")
    print("• Check console output for OAuth configuration messages")
    print("• Test email/password login (always works)")
    if status == "CONFIGURED":
        print("• Test Google login (should work)")
    
    print("\n" + "=" * 60)
    return status

if __name__ == "__main__":
    try:
        status = check_oauth_config()
        sys.exit(0 if status == "CONFIGURED" else 1)
    except Exception as e:
        print(f"Error running diagnostic: {e}")
        sys.exit(2)