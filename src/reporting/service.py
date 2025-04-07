import os
from datetime import datetime
from typing import Optional

from ..database.db_manager import DatabaseManager
from ..services.price_service import PriceService
from .collector import ReportDataCollector
from .generator import HTMLReportGenerator

class ReportingService:
    def __init__(self, db_manager: DatabaseManager, price_service: PriceService, config: Optional[dict] = None):
        self.collector = ReportDataCollector(db_manager, price_service)
        self.generator = HTMLReportGenerator()
        self.config = config or {}
    
    def generate_end_of_run_report(self, output_dir: str = "reports") -> str:
        """Generate an HTML report at the end of an app run."""
        # Collect data
        report_data = self.collector.collect_data()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"trading_report_{timestamp}.html"
        output_path = os.path.join(output_dir, filename)
        
        # Generate report
        self.generator.generate(report_data, output_path)
        
        return output_path 