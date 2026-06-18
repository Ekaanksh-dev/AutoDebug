import yaml
from pathlib import Path

def load_agent_config(name: str) -> tuple[str, str]:
    config_path = Path(__file__).parent.parent / "agent_config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    agent = config[name]
    return agent["agent_id"], agent["api_key"]
