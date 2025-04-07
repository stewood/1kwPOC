import os
from datetime import datetime
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from .models import ReportData

class HTMLReportGenerator:
    def __init__(self, template_dir: str = None):
        if template_dir is None:
            template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.env.filters['format_money'] = self._format_money
        self.env.filters['format_percent'] = self._format_percent
        self.env.filters['format_date'] = self._format_date
    
    def generate(self, data: ReportData, output_path: str) -> None:
        """Generate HTML report and save to file."""
        template = self.env.get_template('report.html')
        
        # Prepare chart data
        strategy_chart_data = self._prepare_strategy_chart_data(data)
        distribution_chart_data = self._prepare_distribution_chart_data(data)
        
        # Prepare template context
        context = {
            'data': data,
            'strategy_chart_data': strategy_chart_data,
            'distribution_chart_data': distribution_chart_data,
            'warning_thresholds': {
                'days_left': 21,
                'high_profit_pct': 50,
                'high_loss_pct': -50
            }
        }
        
        # Render and save
        html_content = template.render(**context)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(html_content)
    
    def _prepare_strategy_chart_data(self, data: ReportData) -> Dict[str, Any]:
        """Prepare data for the strategy P&L chart."""
        return {
            'labels': [s.name for s in data.strategies.values()],
            'data': [s.total_pnl for s in data.strategies.values()],
            'colors': [
                'rgba(40, 167, 69, 0.5)',  # green
                'rgba(0, 123, 255, 0.5)',  # blue
                'rgba(23, 162, 184, 0.5)'  # cyan
            ]
        }
    
    def _prepare_distribution_chart_data(self, data: ReportData) -> Dict[str, Any]:
        """Prepare data for the P&L distribution chart."""
        # Create P&L buckets
        buckets = {
            '-100': 0, '-75': 0, '-50': 0, '-25': 0,
            '0': 0, '25': 0, '50': 0, '75': 0, '100': 0
        }
        
        # Count trades in each bucket
        for strategy in data.strategies.values():
            for trade in strategy.trades:
                if trade.pnl <= -100:
                    buckets['-100'] += 1
                elif trade.pnl <= -75:
                    buckets['-75'] += 1
                elif trade.pnl <= -50:
                    buckets['-50'] += 1
                elif trade.pnl <= -25:
                    buckets['-25'] += 1
                elif trade.pnl <= 0:
                    buckets['0'] += 1
                elif trade.pnl <= 25:
                    buckets['25'] += 1
                elif trade.pnl <= 50:
                    buckets['50'] += 1
                elif trade.pnl <= 75:
                    buckets['75'] += 1
                else:
                    buckets['100'] += 1
        
        return {
            'labels': list(buckets.keys()),
            'data': list(buckets.values())
        }
    
    @staticmethod
    def _format_money(value: Optional[float]) -> str:
        """Format a number as currency, handle None."""
        if value is None:
            return "N/A" # Or return empty string or $0.00?
        try:
            return f"${value:,.2f}"
        except (TypeError, ValueError):
            return "Error"
    
    @staticmethod
    def _format_percent(value: Optional[float]) -> str:
        """Format a number as percentage, handle None."""
        if value is None:
            return "N/A" # Or return empty string "" if preferred
        try:
            return f"{value:,.1f}%"
        except (TypeError, ValueError):
             # Handle cases where value might be non-numeric unexpectedly
            return "Error"
    
    @staticmethod
    def _format_date(value: datetime) -> str:
        """Format a datetime object."""
        return value.strftime('%Y-%m-%d') 