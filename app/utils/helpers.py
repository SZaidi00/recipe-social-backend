from datetime import datetime, timedelta
from typing import Tuple

def can_change_username(user, months: int = 3) -> Tuple[bool, int]:
    """
    Check if user can change username.
    
    Args:
        user: User object
        months: Number of months to wait between changes
        
    Returns:
        Tuple of (can_change: bool, days_until_eligible: int)
    """
    if not user.username_last_changed:
        # Never changed username before, allow change
        return True, 0
    
    time_since_change = datetime.utcnow() - user.username_last_changed
    required_wait = timedelta(days=months * 30)  # Approximate months to days
    
    if time_since_change >= required_wait:
        return True, 0
    else:
        remaining_time = required_wait - time_since_change
        days_remaining = remaining_time.days + 1  # Round up
        return False, days_remaining

def get_next_username_change_date(user, months: int = 3) -> datetime:
    """Get the next date when user can change username."""
    if not user.username_last_changed:
        return datetime.utcnow()  # Can change now
    
    return user.username_last_changed + timedelta(days=months * 30)