import yaml
import os

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.example.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    for key, value in config.items():
        env_var = f"MCP_{key.upper()}"
        if env_var in os.environ:
            config[key] = os.environ[env_var]

    return config

def deterministic_id(seed: str, prefix: str) -> str:
    import hashlib
    import json

    if not isinstance(seed, str):
        seed = json.dumps(seed, sort_keys=True)

    hex = hashlib.sha1(seed.encode()).hexdigest()[:6]
    return f"{prefix}-{hex}"
