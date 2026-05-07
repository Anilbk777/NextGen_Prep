import os
import sys
import logging
from dotenv import load_dotenv

# Add the 'app' directory to sys.path
sys.path.append(os.path.join(os.getcwd(), "app"))

logging.basicConfig(level=logging.INFO)
load_dotenv()

try:
    from app.infrastructure.self_rag.self_rag_main import build_pipeline
    print("Attempting to build pipeline...")
    pipeline = build_pipeline()
    print("Pipeline built successfully!")
except Exception as e:
    print(f"Error building pipeline: {e}")
    import traceback
    traceback.print_exc()
