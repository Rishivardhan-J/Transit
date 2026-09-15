import os
import pickle
from datetime import datetime

def save_model(model, name: str, metadata: dict, output_dir: str = "transit/results/models") -> str:
    """
    Saves a trained model artifact with versioning metadata.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    git_hash = "unset"  # Placeholder
    version = f"{timestamp}_{git_hash}"
    
    model_dir = os.path.join(output_dir, name, version)
    os.makedirs(model_dir, exist_ok=True)
    
    model_filepath = os.path.join(model_dir, "model.pkl")
    metadata_filepath = os.path.join(model_dir, "metadata.pkl")
    
    with open(model_filepath, 'wb') as f:
        pickle.dump(model, f)
        
    with open(metadata_filepath, 'wb') as f:
        pickle.dump(metadata, f)
        
    return model_dir

def load_model(name: str, version: str = "latest", input_dir: str = "transit/results/models") -> tuple:
    """
    Loads a model and its metadata.
    If version is 'latest', loads the most recently saved version based on timestamp.
    """
    base_dir = os.path.join(input_dir, name)
    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"No models found for {name} in {input_dir}")
        
    if version == "latest":
        versions = sorted(os.listdir(base_dir))
        if not versions:
            raise FileNotFoundError(f"No versions found for {name}")
        version = versions[-1]
        
    model_dir = os.path.join(base_dir, version)
    
    with open(os.path.join(model_dir, "model.pkl"), 'rb') as f:
        model = pickle.load(f)
        
    with open(os.path.join(model_dir, "metadata.pkl"), 'rb') as f:
        metadata = pickle.load(f)
        
    return model, metadata
