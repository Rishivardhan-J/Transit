import os
import urllib.request
import zipfile
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BENCHMARK_DIR = Path("transit/data/benchmark")

# Solomon benchmark source (usually hosted at sintef or various academic mirrors)
SOLOMON_URL = "http://web.cba.neu.edu/~msolomon/solomon_100.zip" 

def download_and_extract(url: str, extract_path: Path):
    """Downloads a zip file from a URL and extracts it."""
    try:
        zip_path = extract_path / "temp.zip"
        logger.info(f"Downloading from {url}...")
        
        # Add a basic User-Agent to avoid simple blocks
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
            data = response.read()
            out_file.write(data)
            
        logger.info("Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        zip_path.unlink()
        logger.info(f"Successfully processed {url}")
    except Exception as e:
        logger.error(f"Failed to download/extract {url}: {e}")
        logger.error("<<BENCHMARK_DOWNLOAD_CONFIRMATION>> Please download this benchmark manually and place it in transit/data/benchmark/")

def ingest_track_b():
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    
    solomon_dir = BENCHMARK_DIR / "solomon"
    if not solomon_dir.exists() or not any(solomon_dir.iterdir()):
        solomon_dir.mkdir(parents=True, exist_ok=True)
        download_and_extract(SOLOMON_URL, solomon_dir)
    else:
        logger.info("Solomon benchmark already exists. Skipping.")

    # Note: Homberger instances are numerous and often require manual approval/email links on academic sites.
    # We stub the directory and request manual drop-in if a direct public link isn't stably available.
    homberger_dir = BENCHMARK_DIR / "homberger"
    if not homberger_dir.exists() or not any(homberger_dir.iterdir()):
        homberger_dir.mkdir(parents=True, exist_ok=True)
        logger.warning("<<BENCHMARK_DOWNLOAD_CONFIRMATION>> Homberger instances require manual download.")
        logger.warning("Please place Homberger instances in transit/data/benchmark/homberger/")
    else:
        logger.info("Homberger benchmark already exists. Skipping.")

if __name__ == "__main__":
    ingest_track_b()
