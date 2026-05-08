import asyncio
import os
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

from packages.scrapers.ncs_scraper import scrape_ncs
from packages.scrapers.apna_scraper import scrape_apna
from packages.shared.schemas import JobDTO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://urbanshift:urbanshift_dev@db:5432/urbanshift")

try:
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logger.warning(f"Failed to load SentenceTransformer: {e}. Embeddings will be mocked if not available.")
    embedder = None

async def upsert_jobs(jobs: list[JobDTO]):
    if not jobs:
        return
        
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        for job in jobs:
            # Compute embedding
            desc = job.description_md or ""
            skills = " ".join(job.required_skills) if job.required_skills else ""
            embed_text = f"{job.title}. {job.sector or ''}. {skills}. {desc[:500]}"
            
            embedding = None
            if embedder:
                try:
                    embedding_list = embedder.encode(embed_text).tolist()
                    embedding = f"[{','.join(map(str, embedding_list))}]"
                except Exception as e:
                    logger.error(f"Embedding failed: {e}")
            
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
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    employer = EXCLUDED.employer,
                    area = EXCLUDED.area,
                    pay_min = EXCLUDED.pay_min,
                    pay_max = EXCLUDED.pay_max,
                    sector = EXCLUDED.sector,
                    required_skills = EXCLUDED.required_skills,
                    worker_band = EXCLUDED.worker_band,
                    description_md = EXCLUDED.description_md,
                    scraped_at = EXCLUDED.scraped_at,
                    embedding = EXCLUDED.embedding
            """)
            
            try:
                await conn.execute(query, {
                    "id": job.id,
                    "source": job.source,
                    "source_url": job.source_url,
                    "source_listing_id": job.source_listing_id,
                    "title": job.title,
                    "employer": job.employer,
                    "area": job.area,
                    "lat": job.lat,
                    "lng": job.lng,
                    "pay_min": job.pay_min,
                    "pay_max": job.pay_max,
                    "sector": job.sector,
                    "required_skills": job.required_skills,
                    "worker_band": job.worker_band,
                    "scheme_link_id": job.scheme_link_id,
                    "description_md": job.description_md,
                    "scraped_at": job.scraped_at,
                    "embedding": embedding
                })
            except Exception as e:
                logger.error(f"Error upserting job {job.id}: {e}")
                
    await engine.dispose()
    logger.info(f"Upserted {len(jobs)} jobs to db.")

async def run_scrapers():
    logger.info("Starting scrapers run...")
    all_jobs = []
    
    try:
        ncs_jobs = await scrape_ncs()
        logger.info(f"NCS Scraper finished with {len(ncs_jobs)} jobs.")
        all_jobs.extend(ncs_jobs)
    except Exception as e:
        logger.error(f"NCS Scraper failed: {e}")
        
    try:
        apna_jobs = await scrape_apna()
        logger.info(f"Apna Scraper finished with {len(apna_jobs)} jobs.")
        all_jobs.extend(apna_jobs)
    except Exception as e:
        logger.error(f"Apna Scraper failed: {e}")
        
    if all_jobs:
        await upsert_jobs(all_jobs)
    else:
        logger.warning("No jobs scraped across all scrapers.")

def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_scrapers, 'interval', minutes=30)
    scheduler.start()
    logger.info("APScheduler started.")
    
    # Run once at startup
    asyncio.get_event_loop().create_task(run_scrapers())
    
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == "__main__":
    start_scheduler()
