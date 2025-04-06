"""
Market Hours Utilities

Functions for checking market hours and calculating market open/close times.
Uses the Tradier API to get accurate market status information.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Optional
import pytz

logger = logging.getLogger(__name__)

# US Eastern Time zone for market hours
EASTERN = pytz.timezone('America/New_York')

# Regular market hours (9:30 AM - 4:00 PM Eastern)
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)

def is_market_open() -> bool:
    """Check if the market is currently open.
    
    This is a simplified check that only looks at regular market hours.
    For production use, this should be replaced with an actual API call
    to Tradier to get the current market status.
    
    Returns:
        bool: True if market is open, False otherwise
    """
    now = datetime.now(EASTERN)
    
    # Check if it's a weekday
    if now.weekday() > 4:  # Saturday = 5, Sunday = 6
        return False
    
    # Check if within market hours
    current_time = now.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE

def get_next_market_close() -> Optional[datetime]:
    """Get the next market close time.
    
    Returns:
        datetime: Next market close time in Eastern time,
                 or None if market is closed for the day
    """
    now = datetime.now(EASTERN)
    
    # If weekend or past close, no close time today
    if now.weekday() > 4 or now.time() > MARKET_CLOSE:
        return None
    
    # Combine today's date with close time
    close_time = datetime.combine(now.date(), MARKET_CLOSE)
    return EASTERN.localize(close_time)

def get_next_market_open() -> datetime:
    """Get the next market open time.
    
    Returns:
        datetime: Next market open time in Eastern time
    """
    now = datetime.now(EASTERN)
    
    # If before today's open, use today
    if now.weekday() <= 4 and now.time() < MARKET_OPEN:
        open_date = now.date()
    else:
        # Find next weekday
        days_ahead = 1
        if now.weekday() == 4:  # Friday
            days_ahead = 3
        elif now.weekday() == 5:  # Saturday
            days_ahead = 2
        
        open_date = now.date() + timedelta(days=days_ahead)
    
    # Combine with open time
    open_time = datetime.combine(open_date, MARKET_OPEN)
    return EASTERN.localize(open_time) 