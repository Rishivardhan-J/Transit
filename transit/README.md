# Transit

Phase 1: Foundation, Data Pipeline & EDA.

## Setup Instructions

### Environment Setup
Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Kaggle Credentials (Track A Datasets)
To download the Track A datasets, you need Kaggle API credentials.
Set the `KAGGLE_API_TOKEN` environment variable, or place your token in `~/.kaggle/access_token`. 

```bash
export KAGGLE_API_TOKEN=your_token_here
```
The ingestion scripts will look for this token.

### Benchmark Datasets (Track B)
The Track B benchmark datasets (Solomon, Homberger) are downloaded directly.
If any scripted downloads fail, please download the files manually and place them in the `data/benchmark/` directory.

### Docker Services
Start the stubbed database services (Postgres, Redis) for future phases:
```bash
docker-compose up -d
```
