import time
from typing import Dict, Tuple

class RateLimiter:
    """In-memory rate limiter using the Token Bucket algorithm."""
    def __init__(self, rate: float, capacity: int):
        self.rate = rate  # tokens added per second
        self.capacity = capacity  # max tokens in bucket
        self.buckets: Dict[str, Tuple[float, float]] = {}  # ip -> (tokens, last_update_time)

    def check_rate_limit(self, ip: str) -> bool:
        now = time.time()
        if ip not in self.buckets:
            self.buckets[ip] = (self.capacity, now)
            return True

        tokens, last_update = self.buckets[ip]
        # replenish tokens based on elapsed time
        elapsed = now - last_update
        tokens = min(self.capacity, tokens + elapsed * self.rate)
        
        if tokens >= 1.0:
            self.buckets[ip] = (tokens - 1.0, now)
            return True
        else:
            self.buckets[ip] = (tokens, now)
            return False

# Limiters configuration
# 60 requests per minute capacity
api_limiter = RateLimiter(rate=60.0 / 60.0, capacity=60)
# 10 requests per minute capacity for auth/upload
auth_limiter = RateLimiter(rate=10.0 / 60.0, capacity=10)

