from datetime import datetime
from zoneinfo import ZoneInfo

def to_ist(utc_dt):
    """Converts a UTC datetime object to Indian Standard Time (IST)."""
    if utc_dt and isinstance(utc_dt, datetime):
        ist = ZoneInfo("Asia/Kolkata")
        return utc_dt.astimezone(ist)
    return utc_dt 