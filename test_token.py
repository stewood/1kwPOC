#!/usr/bin/env python3
"""
Simple script to test Option Samurai API token directly.
"""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv
import requests # Add requests import

# Add the project path to import the Option Samurai API
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Import necessary classes from the library
    from optionsamurai_api import APIClient
    from optionsamurai_api.exceptions import TokenExpiredError, AuthenticationError, TokenError
    
    # Load environment variables
    load_dotenv(verbose=True)
    
    # Get token
    token = os.getenv("OPTIONSAMURAI_BEARER_TOKEN")
    
    if not token:
        print("❌ ERROR: OPTIONSAMURAI_BEARER_TOKEN environment variable not found in .env file")
        sys.exit(1)
    
    # Print token info
    print(f"🔑 Token: {token[:20]}...{token[-20:]}")
    print(f"🔄 Token loaded from: {os.path.abspath('.env')}")
    
    # Try to initialize API client and get scans using the library
    print("\n--- Attempting API call via optionsamurai_api library ---")
    try:
        print("🔌 Initializing APIClient...")
        client = APIClient(bearer_token=token)
        print("✅ API client initialized successfully via library")

        print("📊 Fetching saved scans via library...")
        scans_data = client.get_scans() # Use a different variable name

        if hasattr(scans_data, 'saved') and scans_data.saved:
            print(f"✅ LIBRARY CALL SUCCEEDED: Retrieved {len(scans_data.saved)} saved scans.")
            # Optionally print some scan info
            # for scan in scans_data.saved[:2]:
            #     print(f"   - {scan['id']}: {scan['label']}")
        else:
            print("⚠️ LIBRARY CALL SUCCEEDED but no saved scans found or unable to retrieve scans.")

        print("\n✅ Library test passed without TokenExpiredError.")

    except TokenExpiredError as e:
        print(f"❌ LIBRARY CALL FAILED as expected with TokenExpiredError: {e}")
        print("\n--- Now attempting direct API call with the SAME token using 'requests' ---")

        api_url = "https://api.optionsamurai.com/v1/scans"
        headers = {
            "Authorization": f"Bearer {token}", # Use the raw token directly
            "User-Agent": "test_token_direct_requests/1.0" # Simple user agent
        }

        try:
            print(f"📡 Making direct GET request to {api_url}...")
            response = requests.get(api_url, headers=headers, timeout=30)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # If successful:
            print(f"✅ DIRECT CALL SUCCEEDED (Status: {response.status_code})")
            try:
                direct_scans_data = response.json()
                if 'saved' in direct_scans_data and direct_scans_data['saved']:
                     print(f"   Retrieved {len(direct_scans_data['saved'])} scans directly.")
                else:
                     print("   Direct call successful, but no 'saved' scans in response.")
                print("\nCONCLUSION: The token WORKS directly, proving the library's error is incorrect.")
            except json.JSONDecodeError:
                 print("   Direct call successful, but response was not valid JSON.")
                 print(f"   Response text (first 500 chars): {response.text[:500]}")


        except requests.exceptions.HTTPError as http_err:
            print(f"❌ DIRECT CALL FAILED with HTTP Error: {http_err}")
            print(f"   Response status: {http_err.response.status_code}")
            print(f"   Response text: {http_err.response.text}")
            print("\nCONCLUSION: Direct call also failed, token might actually be invalid OR another issue exists.")
        except requests.exceptions.RequestException as req_err:
            print(f"❌ DIRECT CALL FAILED with Request Exception: {req_err}")
            print("\nCONCLUSION: Network or other request issue occurred during direct call.")

    # Catch other potential library errors
    except AuthenticationError as e:
         print(f"❌ LIBRARY CALL FAILED with AuthenticationError (not Expired): {e}")
         # Optionally, still try the direct call here too?
         # ... (add direct call logic if needed) ...
    except TokenError as e:
         print(f"❌ LIBRARY CALL FAILED with general TokenError: {e}")
    except Exception as e: # Catch any other unexpected errors from the library call
        print(f"❌ LIBRARY CALL FAILED with unexpected Exception: {e}")
        # Optionally, still try the direct call
        # ... (add direct call logic if needed) ...


except ImportError:
    print("❌ ERROR: Failed to import optionsamurai_api. Make sure it's installed and accessible.")
    print("   Current sys.path:", sys.path)
    sys.exit(1)
except Exception as e: # Catch errors during initial setup/import
    print(f"❌ An unexpected error occurred during script setup: {e}")
    sys.exit(1)

# Remove the original generic exception block as we have more specific handling now
# except Exception as e:
#     print(f"❌ ERROR: {e}")
#     print("\nCheck if:")
#     print("1. The token is valid and not expired")
#     print("2. You have network connectivity to the Option Samurai API")
#     print("3. The Option Samurai API is currently available")
#     sys.exit(1) 