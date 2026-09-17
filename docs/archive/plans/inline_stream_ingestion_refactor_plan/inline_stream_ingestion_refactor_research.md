### SYSTEM ARCHITECTURE REFACTOR TASK: INGESTION PIPELINE OPTIMIZATION

We need to refactor our data ingestion pipeline (`ingest.py`) to maximize throughput. Currently, the script runs in a strict sequential loop (`Fetch -> Embed Batch -> Wait for Qdrant Upsert -> Repeat`). This couples our local embedding generation batch size directly to our remote database upsert batch size, creating a massive performance bottleneck.

Please analyze the codebase, locate the core ingestion loop, and implement the decoupled architecture detailed below.

---

#### 1. EMPIRICAL DATA & FINDINGS (The "Why")
Our performance profiling data across multiple test runs reveals two conflicting component behaviors:
* **Qdrant Upsert Behavior:** The network, disk commit, and HTTP/gRPC handshake overhead creates a fixed penalty of ~2.08 seconds per call. Standalone Qdrant throughput scales beautifully with larger batches (0.48 items/s at batch size 1 vs. 14.49 items/s at batch size 32). It requires large batch sizes to be efficient.
* **FastEmbed Generation Behavior:** Local CPU matrix math peaks in efficiency at a batch size of 2 to 4 (~4.5 to 5.0 items/s). If forced into a batch size of 32, local generation performance collapses to 3.33 items/s due to CPU cache misses and thread contention (`FE_THREADS = 4`). It requires small batch sizes to be efficient.

---

#### 2. TARGET ARCHITECTURE: DECOUPLED PRODUCER-CONSUMER
To maximize performance, we must completely decouple local vector generation from remote database upserts using a thread-safe Queue pattern.

**A. Threading Configuration & Safety Constraints:**
* Keep `FE_THREADS = 4` passed to `TextEmbedding`.
* **CRITICAL CONSTRAINT:** The script currently features a Windows file-lock retry block because local/embedded Qdrant utilizes RocksDB/SQLite storage engines. To prevent concurrent write contention and database file-locking errors on Windows, **DO NOT use a multi-worker ThreadPoolExecutor for upserts**. 
* **The Solution:** Implement exactly **one (1) dedicated background worker thread** to handle all Qdrant interactions sequentially out of a queue.

**B. Component 1: The Producer (Main Thread)**
* Continues streaming cards, parsing payloads, and cleaning data.
* Executes `FastEmbed` generation utilizing an **Embedding Batch Size of 4** (the empirical sweet spot for local CPU efficiency).
* As soon as a batch of 4 points is generated, immediately push those payload objects into a thread-safe `queue.Queue(maxsize=1000)` to keep memory usage bounded.

**C. Component 2: The Consumer (Dedicated Background Thread)**
* Spawns at script initialization, running a continuous loop pulling points from the queue.
* **Aggressive Batching Logic:** The worker thread should pull items from the queue and accumulate them in an internal memory buffer. It must execute a bulk `qclient.upsert()` call ONLY when:
  1. The internal buffer reaches an **Upsert Batch Size of 128 points** (minimizing the ~2.08s network penalty).
  2. Or, a short timeout expires (e.g., 2 to 3 seconds of the queue being empty) to flush remaining trailing points at the end of the file.

---

#### 3. AUXILIARY OPTIMIZATIONS TO VERIFY
While refactoring the main loop, please check and implement the following minor optimizations if not already optimized:
* **Fixed Overhead Optimization:** Our telemetry shows that `Fetch Existing Card IDs` takes a flat ~14.4 seconds at the start of every run. Check if this query can be optimized via a lean streaming scroll query or restricted fields to cut down initialization time.
* **Indexing Threshold:** Ensure `indexing_threshold=1000000` remains active during the bulk insert block to prevent Qdrant from rebuilding segments mid-ingestion.
* **Payload Trimming:** Verify that `ESSENTIAL_PAYLOAD_FIELDS` is strictly filtering out heavy, unneeded metadata fields before data serialization to keep point preparation times fast.

---

#### 4. IMPLEMENTATION EXPECTATIONS
Please rewrite or refactor the ingestion block in `ingest.py`. Ensure clean exception handling, graceful shutdown of the background worker thread when the main stream ends, and a clean mechanism to flush any remaining items in the queue before exit. 

Show me the structural changes or the updated file when ready.
