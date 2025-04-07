#!/usr/bin/env python3
"""
Compare the token in .env with the one we were provided
"""

import json
import base64
from dotenv import load_dotenv
import os

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

# Token from .env
load_dotenv()
env_token = os.getenv("OPTIONSAMURAI_BEARER_TOKEN")

# Token we were provided
provided_token = """eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InpWZjVSVUp6alVtTjdaMURhWUk1ZiJ9.eyJnaXZlbl9uYW1lIjoiU3RlcGhlbiIsImZhbWlseV9uYW1lIjoiV29vZGFyZCIsIm5pY2tuYW1lIjoid29vZGFyZC5zdGVwaGVuIiwibmFtZSI6IlN0ZXBoZW4gV29vZGFyZCIsInBpY3R1cmUiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NMUVZpaThzWk9wSk5DcWxkOUZ4X01QNWc1SkxYRkhhUTFmbl9pbjRoQVFNVzYtUXRIOD1zOTYtYyIsInVwZGF0ZWRfYXQiOiIyMDI1LTA0LTA2VDE4OjE5OjIxLjU1OVoiLCJlbWFpbCI6Indvb2RhcmQuc3RlcGhlbkBnbWFpbC5jb20iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiaXNzIjoiaHR0cHM6Ly9hdXRoLm9wdGlvbnNhbXVyYWkuY29tLyIsImF1ZCI6InVHS25ualFLQ21OMGw2bEowNjBMVjFIWHhhMnpDTkVCIiwic3ViIjoiZ29vZ2xlLW9hdXRoMnwxMTQ0NDUzMDAwMTk2MDIyMzU5MDkiLCJpYXQiOjE3NDQwMzI1OTMsImV4cCI6MTc0NDA2ODU5Mywic2lkIjoiMk56QUlHT1dYZHNoc0pyazdHSXdXSndwVjNJeVBicFEiLCJub25jZSI6IjlSTWt1RWk0In0.XJbU1fIu3ZbZEU7XVDk4GGMdrchOMFpqccsMWHnr_fYAO86_ryOKJ2iFW9bFiBuLZYHSdKSb3_2oCdxIQKCaYKTg5W343PtoZTZVX-jC8-FNmB2_HONm39yymJ8iO173KBwcVdbWVJgRP716-g3mzc3UpEmPS7P_IiJvtF8HBFHCmTDfUocrSE-oRnadWy-Gf7dk4udoPQWv42X_wgbdls5Z9aSNK5iuFEiPjdqXOXZk7RKMctxsSzShjXTHHRw-PYNcwGvwwzL3aB8MS3P34EQma1Osk70q-4-KjGTkAq-NhNslzExHYrlf2Jk899doJjr0kY5ZtHMMlFhWcXdGFA"""

# Decode both tokens
env_payload = decode_token_payload(env_token)
provided_payload = decode_token_payload(provided_token)

print("Comparing tokens:")
print("-" * 50)

if env_token == provided_token:
    print("The tokens are identical")
else:
    print("The tokens are different")

print("\nEnvironment token:")
print(f"IAT: {env_payload.get('iat')}")
print(f"EXP: {env_payload.get('exp')}")

print("\nProvided token:")
print(f"IAT: {provided_payload.get('iat')}")
print(f"EXP: {provided_payload.get('exp')}") 