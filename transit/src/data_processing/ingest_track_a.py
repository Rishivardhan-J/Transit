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
    if 'KAGGLE_API_TOKEN' in os.environ or 'KAGGLE_USERNAME' in os.environ:
        logger.info("Found Kaggle credentials in environment variables.")
        return True
        
    token_file = Path.home() / '.kaggle' / 'access_token'
    json_file = Path.home() / '.kaggle' / 'kaggle.json'
    if token_file.exists() or json_file.exists():
        logger.info("Found Kaggle credentials file.")
        return True
        
    logger.warning("Kaggle credentials not explicitly found, but we will attempt to run anyway.")
    return True

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
        if name == "amazon_last_mile":
            # Handled separately via AWS Open Data
            continue
            
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
            
    # Download Amazon Last Mile via AWS Open Data
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    
    almrrc_dir = RAW_DATA_DIR / "amazon_last_mile"
    if not (almrrc_dir.exists() and any(almrrc_dir.iterdir())):
        logger.info("Downloading amazon_last_mile from AWS Open Data...")
        almrrc_dir.mkdir(parents=True, exist_ok=True)
        s3 = boto3.client("s3", config=Config(signature_version=UNSIGNED))
        bucket = "amazon-last-mile-challenges"
        prefix = "almrrc2021/almrrc2021-data-training/model_build_inputs/"
        files_to_download = ["package_data.json", "route_data.json", "travel_times.json", "actual_sequences.json"]
        
        for f in files_to_download:
            logger.info(f"Downloading {f}...")
            s3.download_file(bucket, prefix + f, str(almrrc_dir / f))
        logger.info("Successfully downloaded amazon_last_mile")
    else:
        logger.info("Dataset amazon_last_mile already exists. Skipping.")
            
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
