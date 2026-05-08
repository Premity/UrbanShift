import asyncio
import logging
from packages.scrapers.runner import run_scrapers

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    asyncio.run(run_scrapers())
