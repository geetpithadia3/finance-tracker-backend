from datetime import date, datetime, timezone
import calendar

class DateService:
    @staticmethod
    def get_month_dates(year_month: str) -> tuple[datetime, datetime]:
        year, month = map(int, year_month.split('-'))
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
        end_date = datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59, tzinfo=timezone.utc)
        return start_date, end_date
