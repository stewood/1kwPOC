#!/usr/bin/env python3
"""
Debug the token expiration issue
"""

import os
import sys
import json
import base64
from datetime import datetime, timezone
from dotenv import load_dotenv

def decode_token_payload(token):
    """Decode the payload part of a JWT token without validation."""
    # Remove 'Bearer ' prefix if present
    if token.startswith('Bearer '):
        token = token[7:]
    
    # Split the token parts
    parts = token.split('.')
    if len(parts) != 3:
        return None
    
    # Decode the payload (second part)
    payload_b64 = parts[1]
    # Add padding if needed
    payload_b64 += '=' * (-len(payload_b64) % 4)
    
    try:
        payload_json = base64.b64decode(payload_b64.replace('-', '+').replace('_', '/'))
        return json.loads(payload_json)
    except Exception as e:
        print(f"Error decoding payload: {e}")
        return None

def main():
    # Load token from .env
    load_dotenv()
    token = os.getenv("OPTIONSAMURAI_BEARER_TOKEN")
    
    if not token:
        print("Token not found in environment variables!")
        return
    
    # Print token prefix
    print(f"Token prefix: {token[:20]}...")
    
    # Decode the payload
    payload = decode_token_payload(token)
    if not payload:
        print("Failed to decode token payload!")
        return
    
    # Check token claims
    iss = payload.get('iss')
    sub = payload.get('sub')
    iat = payload.get('iat')
    exp = payload.get('exp')
    
    print(f"Issuer (iss): {iss}")
    print(f"Subject (sub): {sub}")
    
    # Detailed expiration information
    if iat:
        issued_at = datetime.fromtimestamp(iat, timezone.utc)
        print(f"Issued at (iat): {iat} ({issued_at.isoformat()})")
    else:
        print("Issued at (iat): Not found in token!")
    
    if exp:
        expires_at = datetime.fromtimestamp(exp, timezone.utc)
        print(f"Expires at (exp): {exp} ({expires_at.isoformat()})")
        
        # Check if token is expired
        current_time = datetime.now(timezone.utc)
        print(f"Current UTC time: {int(current_time.timestamp())} ({current_time.isoformat()})")
        
        if current_time > expires_at:
            print("❌ TOKEN IS EXPIRED!")
        else:
            print("✅ TOKEN IS VALID (not expired)")
            print(f"Time until expiration: {expires_at - current_time}")
    else:
        print("Expires at (exp): Not found in token!")

if __name__ == "__main__":
    main() 