import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import os
import json

# Command Navy Palette
NAVY_DARK = "#0B132B"
NAVY_LIGHT = "#1C2541"
NAVY_ACCENT = "#3A506B"
CYAN = "#5BC0BE"

def set_style():
    plt.style.use('dark_background')
    plt.rcParams.update({
        'axes.facecolor': NAVY_DARK,
        'figure.facecolor': NAVY_DARK,
        'axes.edgecolor': NAVY_ACCENT,
        'axes.labelcolor': 'white',
        'xtick.color': 'white',
        'ytick.color': 'white',
        'grid.color': NAVY_LIGHT,
        'text.color': 'white'
    })

def generate_figures():
    set_style()
    
    # Ensure dir exists
    out_dir = Path("transit/results/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    data_path = Path("transit/data/processed/demo_city.parquet")
    if not data_path.exists():
        print("demo_city.parquet not found. Skipping figure generation.")
        return
        
    df = pd.read_parquet(data_path)
    
    # 1. Demand Distribution
    plt.figure(figsize=(8, 5))
    sns.histplot(df['demand_weight'], color=CYAN, kde=True)
    plt.title("Order Demand Weight Distribution")
    plt.xlabel("Weight/Volume")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(out_dir / "demand_distribution.png", dpi=300)
    plt.close()
    
    # 2. Priority Distribution
    plt.figure(figsize=(8, 5))
    df['priority'].value_counts().plot(kind='bar', color=CYAN)
    plt.title("Order Priority Levels")
    plt.xlabel("Priority")
    plt.ylabel("Count")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.savefig(out_dir / "priority_distribution.png", dpi=300)
    plt.close()
    
    # 3. Traffic Score vs Time of Day
    if 'traffic_score' in df.columns and 'time_window_start' in df.columns:
        df['hour'] = pd.to_datetime(df['time_window_start']).dt.hour
        plt.figure(figsize=(10, 5))
        sns.boxplot(x='hour', y='traffic_score', data=df, color=CYAN)
        plt.title("Traffic Score by Hour of Day")
        plt.xlabel("Hour of Day")
        plt.ylabel("Traffic Multiplier")
        plt.tight_layout()
        plt.savefig(out_dir / "traffic_by_hour.png", dpi=300)
        plt.close()
        
    # 4. Weather Severity
    if 'weather_severity' in df.columns:
        plt.figure(figsize=(8, 5))
        sns.histplot(df['weather_severity'], color=CYAN, bins=10)
        plt.title("Weather Severity Distribution")
        plt.xlabel("Severity Score")
        plt.ylabel("Count")
        plt.tight_layout()
        plt.savefig(out_dir / "weather_severity.png", dpi=300)
        plt.close()
        
    print("EDA figures generated successfully.")

def create_notebooks():
    nb1_content = {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# 01. Data Analysis\n", "Exploratory Data Analysis using the `DataProcessor` module."]},
            {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None, "source": [
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "from src.data_processing.processor import DataProcessor\n",
                "\n",
                "df = pd.read_parquet('../data/processed/demo_city.parquet')\n",
                "df.head()"
            ]}
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4, "nbformat_minor": 4
    }
    
    nb2_content = {
        "cells": [
            {"cell_type": "markdown", "metadata": {}, "source": ["# 02. Feature Engineering\n", "Analyzing engineered features and the pipeline."]},
            {"cell_type": "code", "metadata": {}, "outputs": [], "execution_count": None, "source": [
                "import pandas as pd\n",
                "from src.feature_engineering.feature_pipeline import build_feature_pipeline\n",
                "\n",
                "df = pd.read_parquet('../data/processed/demo_city.parquet')\n",
                "pipeline = build_feature_pipeline()\n",
                "df_transformed = pipeline.fit_transform(df)\n",
                "df_transformed[['direct_distance_km', 'is_peak_hour']].head()"
            ]}
        ],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4, "nbformat_minor": 4
    }
    
    Path("transit/notebooks").mkdir(parents=True, exist_ok=True)
    with open("transit/notebooks/01_data_analysis.ipynb", "w") as f:
        json.dump(nb1_content, f)
    with open("transit/notebooks/02_feature_engineering.ipynb", "w") as f:
        json.dump(nb2_content, f)

if __name__ == "__main__":
    create_notebooks()
    generate_figures()
