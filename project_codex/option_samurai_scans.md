# Option Samurai Scan Strategy

## Setup and Authentication

```python
import os
from optionsamurai_api import APIClient, TokenError, APIError

def initialize_client():
    token = os.getenv("OPTIONSAMURAI_BEARER_TOKEN")
    if not token:
        raise RuntimeError("OPTIONSAMURAI_BEARER_TOKEN environment variable not set.")
    
    try:
        client = APIClient(bearer_token=token)
        print("APIClient initialized successfully.")
        return client
    except TokenError as e:
        print(f"Failed to initialize client due to token error: {e}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during client initialization: {e}")
        raise
```

## Selected Scans

We've identified three key scans that align with our trading strategy:

1. **High Probability Iron Condors - Index/ETF** (ID: 35269)
   - Primary strategy for regular income generation
   - Focuses on high-liquidity index and ETF options
   - Typically seeks high probability trades (>80%)
   - Example Results:
     ```
     SPY (S&P 500 ETF):
     - Probability: 82.1% profit / 14.7% loss
     - P/L: $0.62 max profit / $1.38 max loss (0.45 risk/reward)
     - Structure: 4-leg [478, 480, 530, 532]
     - Liquidity: 6,906 option volume, 57.9M avg stock volume
     ```

2. **Bull Call Spreads** (ID: 35867)
   - Directional strategy for bullish market conditions
   - Looks for favorable risk/reward ratios
   - Example Results:
     ```
     MSFT:
     - Probability: 55.2% profit / 42.4% loss
     - P/L: $2.30 max profit / $0.20 max loss (11.50 risk/reward)
     - Structure: 2-leg [282.5, 285]
     - Liquidity: 1,605 option volume
     ```

3. **Bear Put Spreads** (ID: 35797)
   - Directional strategy for bearish market conditions
   - Focuses on high probability setups
   - Example Results:
     ```
     NFLX:
     - Probability: 86.3% profit / 10.1% loss
     - P/L: $13.79 max profit / $1.21 max loss (11.37 risk/reward)
     - Structure: 2-leg [955, 940]
     - Liquidity: 83 option volume, 4.6M avg stock volume
     ```

## Implementation

### Running Scans
```python
def run_selected_scans():
    try:
        client = initialize_client()
        scans_to_run = [
            (35269, "High Probability Iron Condors Index ETF"),
            (35867, "Bull Call Spreads"),
            (35797, "Bear Put Spreads")
        ]
        
        results = {}
        for scan_id, scan_name in scans_to_run:
            try:
                scan_results = client.execute_scan(scan_id=scan_id, page=0)
                results[scan_name] = format_scan_results(scan_results)
                print(f"Successfully executed {scan_name}")
            except APIError as e:
                print(f"API Error running scan {scan_id}: {e} (Status: {e.status_code})")
            except TokenError as e:
                print(f"Token Error running scan {scan_id}: {e}")
                raise  # Token errors should stop all scans
            except Exception as e:
                print(f"Unexpected error running scan {scan_id}: {e}")
        
        return results
    
    except TokenError as e:
        print(f"Token validation failed: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error in scan execution: {e}")
        raise
```

### API Response Structure
The Option Samurai API returns results in the following format:
```json
{
    "items": [
        {
            "id": "string",
            "name": "string",
            "symbol": "string",
            "expiration": "string",
            "strike": "number",
            "type": "string",
            "bid": "number",
            "ask": "number",
            "volume": "number",
            "openInterest": "number",
            "impliedVolatility": "number",
            "delta": "number",
            "gamma": "number",
            "theta": "number",
            "vega": "number"
        }
    ],
    "totalCount": "number",
    "pageSize": "number"
}
```

### Scan IDs and Strategies

1. **High Probability Iron Condors Index ETF** (ID: 35269)
   - Non-directional strategy for sideways markets
   - Focuses on high probability setups
   - Example Results:
     ```
     SPY:
     - Probability: 85.2% profit / 14.8% loss
     - P/L: $12.50 max profit / $2.50 max loss (5.0 risk/reward)
     - Structure: 4-leg [420, 425, 435, 440]
     - Liquidity: 125 option volume, 85M avg stock volume
     ```

2. **Bull Call Spreads** (ID: 35867)
   - Directional strategy for bullish market conditions
   - Focuses on high probability setups
   - Example Results:
     ```
     AAPL:
     - Probability: 82.1% profit / 17.9% loss
     - P/L: $15.25 max profit / $4.75 max loss (3.21 risk/reward)
     - Structure: 2-leg [175, 180]
     - Liquidity: 95 option volume, 52M avg stock volume
     ```

3. **Bear Put Spreads** (ID: 35797)
   - Directional strategy for bearish market conditions
   - Focuses on high probability setups
   - Example Results:
     ```
     NFLX:
     - Probability: 86.3% profit / 10.1% loss
     - P/L: $13.79 max profit / $1.21 max loss (11.37 risk/reward)
     - Structure: 2-leg [955, 940]
     - Liquidity: 83 option volume, 4.6M avg stock volume
     ```

### Key Data Fields

#### Core Trade Metrics
- `max_profit`: Maximum potential profit
- `max_loss`: Maximum potential loss
- `max_return_margin`: Return on margin
- `max_return_margin_annualized`: Annualized return on margin
- `prob_max_profit`: Probability of achieving max profit
- `prob_max_loss`: Probability of hitting max loss
- `profit_range_percent`: Profit range as percentage
- `spread_profit_ratio`: Ratio of max profit to max loss
- `spread_expected_value`: Expected value of the trade

#### Market Data
- `name`: Symbol/ETF name
- `industry`: Industry classification
- `average_volume`: Average stock trading volume
- `beta`: Beta value relative to market
- `dividend_yield`: Current dividend yield
- `market_cap`: Market capitalization

#### Stock Price Data
- `stock_last`: Current stock price
- `stock_open`: Opening price
- `stock_high`: Day's high
- `stock_low`: Day's low
- `stock_close`: Previous close
- `stock_volume`: Current trading volume

#### Volatility Metrics
- `stock_iv`: Implied volatility
- `stock_rv`: Realized volatility
- `skew`: Volatility skew
- `atr_dollar`: Average True Range in dollars
- `atr_percent`: Average True Range as percentage

#### Option Data
- `expiration_date`: Array of expiration dates for each leg
- `days_to_expiration`: Array of days until expiration
- `strike`: Array of strike prices
- `volume`: Option volume
- `open_interest`: Array of open interest for each leg
- `bid`: Current bid price
- `mid`: Mid price between bid and ask
- `ask`: Current ask price

#### Greeks
- `delta`: Rate of change vs underlying
- `gamma`: Rate of change in delta
- `theta`: Time decay
- `vega`: Sensitivity to volatility

#### Performance
- `performance_month`: 1-month performance
- `performance_quarter`: 3-month performance
- `performance_half_year`: 6-month performance
- `performance_year`: 1-year performance
- `performance_ytd`: Year-to-date performance
- `week_52_high`: Distance from 52-week high
- `week_52_low`: Distance from 52-week low

### Results Storage
```python
def save_scan_results(results: dict, scan_name: str):
    import json
    from datetime import datetime
    from pathlib import Path
    
    # Create results directory if it doesn't exist
    results_dir = Path("scan_results")
    results_dir.mkdir(exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = scan_name.lower().replace(" ", "_")
    filename = results_dir / f"{timestamp}_{safe_name}.json"
    
    # Save results
    try:
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"Results saved to {filename}")
    except Exception as e:
        print(f"Error saving results: {e}")
```

## Usage Strategy

1. **Primary Income Generation**
   - Use Iron Condor scan for regular income opportunities
   - Focus on highly liquid ETFs (SPY, QQQ)
   - Look for >80% probability of profit
   - Monitor option volume for liquidity

2. **Directional Trades**
   - Use Bull Call spreads in bullish markets
   - Use Bear Put spreads in bearish markets
   - Prioritize trades with risk/reward > 3.0
   - Consider market conditions and trend

3. **Risk Management**
   - Check both probability of profit AND loss
   - Verify option liquidity (volume)
   - Consider position sizing based on risk/reward
   - Monitor days to expiration for time decay management

4. **Error Handling**
   - Handle token expiration gracefully
   - Implement retries for rate limits
   - Log all API errors for monitoring
   - Cache results to minimize API calls

## Next Steps

1. Implement automated scan scheduling
2. Add trade tracking and performance metrics
3. Create alerts for high-probability setups
4. Develop position sizing rules based on scan results
5. Add retry logic for transient API errors
6. Implement results caching to respect rate limits 