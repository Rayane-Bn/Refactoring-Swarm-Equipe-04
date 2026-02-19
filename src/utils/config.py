"""
Configuration management for the Refactoring Swarm project.
Loads environment variables and defines critical paths.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ===== API Configuration =====
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError(
        "❌ GROQ_API_KEY not found in .env file. "
        "Please copy .env.example to .env and add your API key."
    )

# ===== Model Configuration =====
DEFAULT_MODEL = "llama-3.3-70b-versatile"  # Fast and cost-effective for most tasks
# Alternative: "gemini-1.5-pro" for more complex reasoning (if needed)

# ===== Project Paths =====
PROJECT_ROOT = Path(__file__).parent.parent.parent  # Go up to project root
SANDBOX_DIR = PROJECT_ROOT / "sandbox"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure critical directories exist
SANDBOX_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ===== Agent Configuration =====
MAX_ITERATIONS = 10  # Maximum self-healing loop iterations (prevent infinite loops)
TIMEOUT_SECONDS = 300  # 5 minutes timeout per agent action

# ===== Logging Configuration =====
LOG_FILE = LOGS_DIR / "experiment_data.json"

# ===== Validation =====
def validate_config():
    """Validate that all required configuration is present."""
    errors = []
    
    if not GROQ_API_KEY:
        errors.append("GOOGLE_API_KEY is missing")
    
    if not SANDBOX_DIR.exists():
        errors.append(f"Sandbox directory does not exist: {SANDBOX_DIR}")
    
    if errors:
        raise ValueError(f"Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))
    
    return True

# Validate on import
validate_config()