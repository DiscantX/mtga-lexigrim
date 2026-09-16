### SYSTEM ARCHITECTURE REFACTOR TASK: INLINE STREAM PIPELINING FOR INGEST.PY

We need to optimize the producer phase of our ingestion pipeline inside `ingest.py`. Currently, the script features a severe architectural flaw: it pre-scans and loads thousands of parsed Scryfall JSON objects into a monolithic in-memory array (`pending_cards`) before spinning up the background consumer thread. This halts our processing pipeline at initialization, triggers excessive garbage collection, and starves our asynchronous architecture.

Please execute a structural refactor of `ingest_cards_to_qdrant` to achieve **True Inline Stream Pipelining**. The background thread must start immediately, and items must be streamed, filtered, embedded, and queued on-the-fly, holding a maximum of 2 card objects in memory at any given microsecond.

---

#### 1. CRITICAL BLOCK DELETIONS
Locate and **completely delete** the following sequential pre-loading and filtering block (found roughly between lines 174 and 185):

```python
# DELETE THIS ENTIRE BLOCK COMPLETELY
print("Filtering dataset for pending cards...")
with timer.measure("Streaming & Filtering"):
    pending_cards = []
    skipped_existing = 0

    for card_obj, _ in stream_objects_with_pos(file_path):
        if card_obj["id"] in existing_ids:
            skipped_existing += 1
            continue
        pending_cards.append(card_obj)

total_pending = len(pending_cards)
print(f"Dataset stats: {total_cards:,} total cards | {skipped_existing:,} already in DB | {total_pending:,} to process.")
```

---

#### 2. BACKGROUND WORKER ACCELERATION
Move the Queue initialization and the background consumer worker thread initialization **upwards** so that it spawns *immediately* after the `Pre-scan Line Count` metric finishes. The thread must be active and waiting for data *before* the file stream begins.

```python
# INITIALIZE QUEUE AND THREAD IMMEDIATELY AFTER PRE-SCAN LINE COUNT
card_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
error_holder = []
consumer_thread = threading.Thread(
    target=qdrant_consumer_worker,
    args=(card_queue, timer, error_holder),
    daemon=True
)
consumer_thread.start()
```

---

#### 3. PIPELINE REFACTOR SPECIFICATION (THE CORE LOOP)
Replace the old `for card_obj in pending_cards:` loop with a direct iteration over the memory-safe generator `stream_objects_with_pos(file_path)`. 

Implement the following exact logical structure to process cards on-the-fly:

```python
try:
    processed_this_run = 0
    current_embedding_batch = []
    
    # Calculate an estimated maximum remaining count for tqdm display bounds
    estimated_pending = total_cards - len(existing_ids)
    
    print("Streaming cards directly to FastEmbed...")
    with tqdm(total=estimated_pending, unit="cards", desc="Ingesting MTG Cards", dynamic_ncols=True) as pbar:
        # Stream raw items straight from disk one-by-one
        for card_obj, _ in stream_objects_with_pos(file_path):
            
            # Step A: Inline Dedup Filtering (No storage overhead)
            if card_obj["id"] in existing_ids:
                continue
            
            # Step B: Populate our tiny generation batch tracking window
            current_embedding_batch.append(card_obj)

            # Step C: When batch size hit (EMBEDDING_BATCH_SIZE=2), process and enqueue
            if len(current_embedding_batch) >= EMBEDDING_BATCH_SIZE:
                points = process_batch(current_embedding_batch, timer)
                
                # Blocks if queue is full (handles backpressure safely)
                card_queue.put(points) 
                
                processed_this_run += len(current_embedding_batch)
                pbar.update(len(current_embedding_batch))
                current_embedding_batch = []

            # Step D: Background consumer health monitoring
            if error_holder:
                raise error_holder[0]

            # Step E: Throttled telemetry dashboard update
            if processed_this_run % REPORT_INTERVAL == 0:
                pbar.set_postfix({
                    "Total DB": len(existing_ids) + processed_this_run,
                    "Cache Size": len(embedding_cache),
                    "Embed/b": f"{timer.get_avg('FastEmbed Generation'):.2f}s",
                    "Upsert/b": f"{timer.get_avg('Qdrant Upsert'):.2f}s"
                })

        # Step F: Flush residual trailing cards at EOF
        if current_embedding_batch:
            points = process_batch(current_embedding_batch, timer)
            card_queue.put(points)
            processed_this_run += len(current_embedding_batch)
            pbar.update(len(current_embedding_batch))

    # Step G: Graceful pipeline worker tear down
    card_queue.put(None)
    consumer_thread.join()

    if error_holder:
        raise error_holder[0]
```

---

#### 4. ARCHITECTURAL SANITY CHECK
* **No List Appends:** Ensure no global list accumulators (like `pending_cards`) are left in the main thread scope to ensure objects are garbage collected immediately after being batched.
* **Variable Scope Protection:** Ensure variables like `total_cards` and `existing_ids` are mapped cleanly to the `tqdm` visualization arguments.
* **Error Bubbling:** Verify that the `error_holder` checking mechanics remain inside the stream iterator loops to halt the producer instantly if the background thread drops its database socket connection.

Please implement these modifications within `ingest.py` and output the clean, fully-pipelined refactored script.


def ingest_cards_to_qdrant(file_path: str):
    timer = IngestionTimer()
    
    # ... [Keep Fetch Existing Card IDs & Threshold updates exactly as they are] ...

    # 1. Initialize Queue and Background Worker immediately
    card_queue = queue.Queue(maxsize=QUEUE_MAXSIZE)
    error_holder = []
    consumer_thread = threading.Thread(
        target=qdrant_consumer_worker,
        args=(card_queue, timer, error_holder),
        daemon=True
    )
    consumer_thread.start()

    try:
        processed_this_run = 0
        current_embedding_batch = []
        
        # 2. Pipeline processing directly from the disk stream
        print("Streaming cards directly to FastEmbed...")
        with tqdm(unit="cards", desc="Ingesting MTG Cards", dynamic_ncols=True) as pbar:
            
            # STREAM ONE CARD AT A TIME INSTEAD OF PRE-PARSING THE LIST
            for card_obj, _ in stream_objects_with_pos(file_path):
                
                # Inline filtering keeps RAM flat and bypasses object retention
                if card_obj["id"] in existing_ids:
                    continue
                
                current_embedding_batch.append(card_obj)

                # Process local embedding generation as soon as batch hits 2
                if len(current_embedding_batch) >= EMBEDDING_BATCH_SIZE:
                    points = process_batch(current_embedding_batch, timer)
                    card_queue.put(points) # Backpressure handle
                    
                    processed_this_run += len(current_embedding_batch)
                    pbar.update(len(current_embedding_batch))
                    current_embedding_batch = []

                if error_holder:
                    raise error_holder[0]

                # Update performance stats on the fly
                if processed_this_run % REPORT_INTERVAL == 0:
                    pbar.set_postfix({
                        "Cache Size": len(embedding_cache),
                        "Embed/b": f"{timer.get_avg('FastEmbed Generation'):.2f}s",
                        "Upsert/b": f"{timer.get_avg('Qdrant Upsert'):.2f}s"
                    })

            # Catch remaining stray cards
            if current_embedding_batch:
                points = process_batch(current_embedding_batch, timer)
                card_queue.put(points)
                processed_this_run += len(current_embedding_batch)
                pbar.update(len(current_embedding_batch))

        # 3. Clean shutdown sequence
        card_queue.put(None)
        consumer_thread.join()

        if error_holder:
            raise error_holder[0]

    finally:
        # ... [Keep recovery logic as it is] ...
