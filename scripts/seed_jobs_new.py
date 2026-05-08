import asyncio
import csv
import json
import os
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback to localhost if run from host, or db if run via docker
default_db_url = "postgresql+asyncpg://urbanshift:urbanshift_dev@localhost:5432/urbanshift"
if os.environ.get("DATABASE_URL") and "db:5432" in os.environ.get("DATABASE_URL"):
    # If we are somehow reading from the env file but running locally without docker
    pass

DATABASE_URL = os.getenv("DATABASE_URL", default_db_url)
# Force localhost for local run unless overridden explicitly
if "db:5432" in DATABASE_URL and not os.path.exists("/.dockerenv"):
    DATABASE_URL = DATABASE_URL.replace("db:5432", "localhost:5432")

async def seed_jobs():
    engine = create_async_engine(DATABASE_URL)
    
    # Path to the CSV file
    csv_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'seed', 'jobs_with_scheme_links.csv')
    
    jobs = []
    with open(csv_file_path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            job = {
                "id": row["id"],
                "source": row["source"],
                "source_url": row["source_url"],
                "source_listing_id": row["source_listing_id"] if row["source_listing_id"] else None,
                "title": row["title"],
                "employer": row["employer"] if row["employer"] else None,
                "area": row["area"] if row["area"] else None,
                "lat": float(row["lat"]) if row["lat"] else None,
                "lng": float(row["lng"]) if row["lng"] else None,
                "pay_min": int(row["pay_min"]) if row["pay_min"] else None,
                "pay_max": int(row["pay_max"]) if row["pay_max"] else None,
                "sector": row["sector"] if row["sector"] else None,
                "required_skills": json.loads(row["required_skills"]) if row["required_skills"] else None,
                "worker_band": int(row["worker_band"]) if row["worker_band"] else None,
                "scheme_link_id": row["scheme_link_id"] if row["scheme_link_id"] else None,
                "description_md": row["description_md"] if row["description_md"] else None,
                "scraped_at": datetime.fromisoformat(row["scraped_at"]),
                "embedding": row["embedding"] if row["embedding"] else None
            }
            jobs.append(job)

    async with engine.begin() as conn:
        logger.info("Clearing existing jobs from jobs_cache...")
        await conn.execute(text("TRUNCATE TABLE jobs_cache;"))
        
        logger.info(f"Inserting {len(jobs)} jobs into jobs_cache...")
        
        query = text("""
            INSERT INTO jobs_cache (
                id, source, source_url, source_listing_id, title, employer, 
                area, lat, lng, pay_min, pay_max, sector, required_skills, 
                worker_band, scheme_link_id, description_md, scraped_at, embedding
            ) VALUES (
                :id, :source, :source_url, :source_listing_id, :title, :employer,
                :area, :lat, :lng, :pay_min, :pay_max, :sector, :required_skills,
                :worker_band, :scheme_link_id, :description_md, :scraped_at, :embedding
            )
        """)
        
        for job in jobs:
            try:
                await conn.execute(query, job)
            except Exception as e:
                logger.error(f"Error inserting job {job['id']}: {e}")
                
    await engine.dispose()
    logger.info("Database seed completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed_jobs())
