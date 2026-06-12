# pyrefly: ignore [missing-import]
from slowapi import Limiter

# pyrefly: ignore [missing-import]
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
