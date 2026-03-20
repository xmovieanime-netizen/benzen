import re
from typing import Tuple

def validate_twitter_link(link: str) -> Tuple[bool, str]:
    """
    Validate if link is a valid Twitter/X link
    Returns (is_valid, error_message)
    """
    if not link:
        return False, "Link is empty"
    
    # Check if it's a valid URL
    url_pattern = r'^https?://'
    if not re.match(url_pattern, link):
        return False, "Link must start with http:// or https://"
    
    # Check if it's a Twitter/X domain
    twitter_patterns = [
        r'twitter\.com',
        r'x\.com',
        r't\.co'
    ]
    
    is_twitter = any(re.search(pattern, link) for pattern in twitter_patterns)
    if not is_twitter:
        return False, "Link must be from twitter.com, x.com, or t.co"
    
    return True, ""

def validate_duration_format(duration_str: str) -> Tuple[bool, str]:
    """
    Validate duration format
    Returns (is_valid, error_message)
    """
    if not duration_str:
        return True, ""  # Empty is valid (uses default)
    
    pattern = r'^(\d+[dhm]\s*)+$'
    if not re.match(pattern, duration_str.lower()):
        return False, "Invalid duration format. Use: 2d 5h 30m"
    
    return True, ""
