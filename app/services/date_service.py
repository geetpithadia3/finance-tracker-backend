from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class DateService:
    """Service for handling date calculations and recurring date logic"""
    
    @staticmethod
    def calculate_next_due_date(start_date: datetime, frequency: str) -> datetime:
        """Calculate next due date based on frequency (legacy function)"""
        if frequency == "DAILY":
            return start_date + timedelta(days=1)
        elif frequency == "WEEKLY":
            return start_date + timedelta(weeks=1)
        elif frequency == "MONTHLY":
            return start_date + relativedelta(months=1)
        elif frequency == "YEARLY":
            return start_date + relativedelta(years=1)
        else:
            return start_date + timedelta(days=30)  # Default to monthly

    @staticmethod
    def calculate_next_due_date_enhanced(
        start_date: datetime, 
        frequency: str, 
        date_flexibility: str = "EXACT"
    ) -> datetime:
        """Enhanced calculation with date flexibility options"""
        # Base calculation
        if frequency == "DAILY":
            next_date = start_date + timedelta(days=1)
        elif frequency == "WEEKLY":
            next_date = start_date + timedelta(weeks=1)
        elif frequency == "BIWEEKLY":
            next_date = start_date + timedelta(weeks=2)
        elif frequency == "FOUR_WEEKLY":
            next_date = start_date + timedelta(weeks=4)
        elif frequency == "MONTHLY":
            next_date = start_date + relativedelta(months=1)
        elif frequency == "YEARLY":
            next_date = start_date + relativedelta(years=1)
        else:
            next_date = start_date + relativedelta(months=1)  # Default to monthly
        
        # Apply date flexibility
        if date_flexibility == "EARLY_MONTH":
            next_date = next_date.replace(day=1)
        elif date_flexibility == "MID_MONTH":
            next_date = next_date.replace(day=15)
        elif date_flexibility == "LATE_MONTH":
            # Last day of month
            next_date = next_date.replace(day=28)
        elif date_flexibility == "WEEKDAY":
            # Adjust to next weekday if falls on weekend
            while next_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                next_date += timedelta(days=1)
        elif date_flexibility == "WEEKEND":
            # Adjust to next weekend if falls on weekday
            while next_date.weekday() < 5:
                next_date += timedelta(days=1)
        
        return next_date