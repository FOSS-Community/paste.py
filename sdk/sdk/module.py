import requests
from typing import Optional, Union
from pathlib import Path

class PasteBinSDK:
    def __init__(self, base_url: str = "http://paste.fosscu.org"):
        self.base_url = base_url
    