"""
Test script for Option Samurai scanning functionality.
Runs a single scan cycle and displays the results.
"""

import logging
import sys
from .config import Config
from .scanner import ScanManager

def setup_logging():
    """Set up logging with colored output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s',
        stream=sys.stdout
    )

def main():
    """Run a test scan cycle."""
    print("\n🔍 Option Samurai Scanner Test\n")
    
    try:
        # Set up logging
        setup_logging()
        
        # Initialize components
        print("⚙️  Initializing components...")
        config = Config()
        scanner = ScanManager(config)
        
        # Run a single scan cycle
        print("\n🚀 Running scan cycle...\n")
        scanner._run_scan_cycle()
        
        print("\n✅ Test completed successfully\n")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        raise

if __name__ == "__main__":
    main() 