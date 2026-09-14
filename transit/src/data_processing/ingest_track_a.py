import os
import sys
import logging
from pathlib import Path
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Track A Datasets
KAGGLE_DATASETS = {
    "food_delivery": "denkuznetz/food-delivery-time-prediction",
    "mini_ecommerce": "revatiborkhade03/mini-e-commerce-logistics-dataset-delivery-times",
    "amazon_last_mile": "amazon-science/amazon-last-mile-routing-research-challenge", # Expected Kaggle path
}
KAGGLE_COMPETITIONS = {
    "nyc_taxi": "nyc-taxi-trip-duration"
}

RAW_DATA_DIR = Path("transit/data/raw")

def verify_kaggle_credentials():
    """
    Verifies that the new single-token Kaggle auth is present.
    Requires either KAGGLE_API_TOKEN environment variable or ~/.kaggle/access_token.
    """
    if 'KAGGLE_API_TOKEN' in os.environ:
        logger.info("Found KAGGLE_API_TOKEN in environment variables.")
        return True
        
    token_file = Path.home() / '.kaggle' / 'access_token'
    if token_file.exists():
        logger.info("Found Kaggle access_token file.")
        return True
        
    logger.error("Kaggle credentials not found.")
    logger.error("Please set KAGGLE_API_TOKEN environment variable or create ~/.kaggle/access_token.")
    return False

def run_kaggle_command(command: list):
    """Runs a Kaggle CLI command."""
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(command)}")
        logger.error(f"Error output: {e.stderr}")
        raise

def ingest_track_a():
    """Ingests all Track A datasets."""
    if not verify_kaggle_credentials():
        sys.exit(1)
        
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Download Kaggle Datasets
    for name, dataset in KAGGLE_DATASETS.items():
        out_dir = RAW_DATA_DIR / name
        if out_dir.exists() and any(out_dir.iterdir()):
            logger.info(f"Dataset {name} already exists. Skipping.")
            continue
            
        logger.info(f"Downloading dataset: {name} ({dataset})")
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            # We use the CLI to rely on its auth resolution
            run_kaggle_command(["kaggle", "datasets", "download", "-d", dataset, "-p", str(out_dir), "--unzip"])
            logger.info(f"Successfully downloaded {name}")
        except Exception as e:
            logger.error(f"Failed to download {name}. Error: {e}")
            
    # Download Kaggle Competitions
    for name, comp in KAGGLE_COMPETITIONS.items():
        out_dir = RAW_DATA_DIR / name
        if out_dir.exists() and any(out_dir.iterdir()):
            logger.info(f"Competition {name} already exists. Skipping.")
            continue
            
        logger.info(f"Downloading competition: {name} ({comp})")
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            run_kaggle_command(["kaggle", "competitions", "download", "-c", comp, "-p", str(out_dir)])
            # Unzip manually since competition download doesn't always support --unzip reliably in all versions
            zip_file = out_dir / f"{comp}.zip"
            if zip_file.exists():
                subprocess.run(["unzip", "-q", "-o", str(zip_file), "-d", str(out_dir)], check=True)
                zip_file.unlink()
            logger.info(f"Successfully downloaded {name}")
        except Exception as e:
            logger.error(f"Failed to download {name}. Error: {e}")

if __name__ == "__main__":
    ingest_track_a()
