import os
import sys
import logging

# Ensure the app directory is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.api.deps import ingest_service_dep
from app.core.config import get_settings

# Configure logging to see the crawler in action
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Stripe Docs Ingestion Script...")
    
    # Temporarily override settings to allow a deep crawl
    settings = get_settings()
    settings.crawler_max_pages = 500  # Adjust this number to crawl more/less pages
    settings.crawler_delay_ms = 100   # Be polite, but fast enough
    
    # Get the orchestrator from our dependency graph
    orchestrator = ingest_service_dep()
    
    logger.info("Crawling starting. This may take a few minutes...")
    # 'all' scope triggers the default seed (https://docs.stripe.com) 
    # and crawls across /payments, /billing, /webhooks, /api, /testing
    result = orchestrator.run(scope='all')
    
    logger.info("Ingestion Complete!")
    logger.info(f"Pages Seen: {result.get('pages_seen')}")
    logger.info(f"Documents Upserted: {result.get('documents_upserted')}")
    logger.info(f"Chunks Embedded & Upserted: {result.get('chunks_upserted')}")

if __name__ == "__main__":
    main()
