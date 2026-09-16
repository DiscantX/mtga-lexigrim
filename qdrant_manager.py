# qdrant_manager.py
import os
import socket
import subprocess
import time
from qdrant_client import QdrantClient, models

# Update this path to where your qdrant binary lives outside the project space
QDRANT_EXE_PATH = r"C:\Users\Admin\qdrant\qdrant.exe"  
PORT = 6333

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "dbs")
SNAPSHOTS_DIR = os.path.join(PROJECT_ROOT, "data", "snapshots")


def is_qdrant_running(port: int = PORT) -> bool:
    """Checks if Qdrant is active by testing the REST API port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


# Inside qdrant_manager.py -> update auto_initialize_collections:

def auto_initialize_collections(client: QdrantClient):
    collection_name = "mtg_cards"
    
    if client.collection_exists(collection_name):
        return

    print(f"\n⚠️ Database collection '{collection_name}' not found. Initializing architecture...")
    
    # 🛠️ IMPROVEMENT: Add an optimized indexing threshold to lower disk conflicts on Windows
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=768,
            distance=models.Distance.COSINE,
            on_disk=True # Keeps RAM usage optimized
        ),
        # This tells Qdrant to load points in memory first, avoiding massive disk open/close collisions
        optimizers_config=models.OptimizersConfigDiff(
            indexing_threshold=20000 
        )
    )
    
    print("Building fast inverted lookup paths...")
    client.create_payload_index(collection_name, "colors", models.PayloadSchemaType.KEYWORD)
    client.create_payload_index(collection_name, "cmc", models.PayloadSchemaType.INTEGER)
    client.create_payload_index(collection_name, "legalities.commander", models.PayloadSchemaType.KEYWORD)
    print("✓ Collection structure initialized completely.\n")


def ensure_qdrant_running():
    """Checks for Qdrant, launches the process if down, and verifies structural schemas."""
    server_was_down = False

    if not is_qdrant_running():
        server_was_down = True
        print("⚠️ Qdrant server is down. Attempting background launch...")

        if not os.path.exists(QDRANT_EXE_PATH):
            raise FileNotFoundError(
                f"Could not find qdrant.exe at: {QDRANT_EXE_PATH}. "
                f"Please update the path variable inside qdrant_manager.py."
            )

        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(SNAPSHOTS_DIR, exist_ok=True)

        custom_env = os.environ.copy()
        custom_env["QDRANT__STORAGE__STORAGE_PATH"] = DATA_DIR
        custom_env["QDRANT__STORAGE__SNAPSHOTS_PATH"] = SNAPSHOTS_DIR

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE

        subprocess.Popen(
            [QDRANT_EXE_PATH],
            env=custom_env,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Poll the port for initialization
        print("Waiting for Qdrant to initialize", end="", flush=True)
        initialized = False
        for _ in range(20):
            time.sleep(0.5)
            print(".", end="", flush=True)
            if is_qdrant_running():
                print(f"\n✓ Qdrant successfully launched. Data isolated to: {DATA_DIR}")
                initialized = True
                break
        
        if not initialized:
            raise RuntimeError("\n❌ Qdrant was started but failed to open port 6333 in time.")
    else:
        if __name__ == "__main__":
            print("✓ Qdrant server is already running.")

    # Core logic: Establish a client and run our database structural safety check
    client = QdrantClient(host="localhost", port=6333)
    auto_initialize_collections(client)
    return True


if __name__ == "__main__":
    ensure_qdrant_running()
