import time
import itertools
import sys
import json
import os
from fastembed import TextEmbedding
from embeddings.text_extractors import extract_embedding_text

# 1. Define the testing grid aligned with codebase defaults (FE_THREADS = 4, EMBEDDING_BATCH_SIZE = 4)
TH_GRID = [1, 2, 4, 6, 8]
BATCH_GRID = [1, 2, 4, 8, 16]
NUM_TEST_CALLS = 50
OUTPUT_FILENAME = "fastembed_benchmark_results.md"

FIXTURE_PATH = os.path.join("tests", "fixtures", "sample_cards.json")

def load_sample_cards() -> list:
    if os.path.exists(FIXTURE_PATH):
        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

SAMPLE_CARDS = load_sample_cards()
SAMPLE_TEXTS = [extract_embedding_text(card) for card in SAMPLE_CARDS] * 4  # 36 items total, sufficient for max batch size 16

def write_report_to_disk(results):
    """Generates and writes a clean ranked markdown table report to disk."""
    report_lines = [
        "# FastEmbed Thread Tuning Grid Search",
        f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Configuration: {NUM_TEST_CALLS} calls per permutation, Model: nomic-ai/nomic-embed-text-v1.5",
        "",
        "### Leaderboard (Fastest to Slowest)",
        "| Rank | FE_THREADS | BATCH_SIZE | Total Time (s) | Throughput (Items/s) |",
        "| :---: | :---: | :---: | :---: | :---: |"
    ]
    
    # Sort results by throughput descending
    sorted_results = sorted(results, key=lambda x: x["throughput"], reverse=True)
    
    for rank, r in enumerate(sorted_results, start=1):
        report_lines.append(
            f"| {rank} | {r['threads']} | {r['batch_size']} | {r['total_time']:.3f}s | **{r['throughput']:.2f} items/s** |"
        )
        
    if sorted_results:
        best = sorted_results[0]
        report_lines.extend([
            "",
            "### Current Optimal Configuration",
            f"* **FE_THREADS**: {best['threads']}",
            f"* **BATCH_SIZE**: {best['batch_size']}",
            f"* **Peak Throughput**: {best['throughput']:.2f} items/s"
        ])
        
    with open(OUTPUT_FILENAME, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

def run_benchmark():
    results = []
    
    if not SAMPLE_TEXTS:
        print(f"Error: Sample cards fixture not found or empty at '{FIXTURE_PATH}'.")
        return

    print(f"Starting Automated FastEmbed Tuning Grid Search...")
    print(f"Running {NUM_TEST_CALLS} calls per permutation using nomic-ai/nomic-embed-text-v1.5.")
    print(f"Progressive updates will save live to: '{OUTPUT_FILENAME}'\n")
    
    # Generate all test permutations
    permutations = list(itertools.product(TH_GRID, BATCH_GRID))
    total_runs = len(permutations)
    
    for idx, (threads, batch_size) in enumerate(permutations, start=1):
        # Ensure sample slice fits batch size
        if batch_size > len(SAMPLE_TEXTS):
            continue
            
        print(f"[{idx}/{total_runs}] Testing: FE_THREADS={threads} | BATCH_SIZE={batch_size}... ", end="", flush=True)
        
        # Slice sample data to exact batch size
        batch_data = SAMPLE_TEXTS[:batch_size]
        
        try:
            # Initialize model with current thread constraint using nomic-ai/nomic-embed-text-v1.5
            model = TextEmbedding(model_name="nomic-ai/nomic-embed-text-v1.5", threads=threads)
            
            # Warmup call to ensure ONNX runtime is fully loaded/allocated in memory
            list(model.embed(batch_data))
            
            # Benchmark loop
            start_time = time.perf_counter()
            for _ in range(NUM_TEST_CALLS):
                # Force evaluation of the generator expression to compute the vectors
                list(model.embed(batch_data))
            end_time = time.perf_counter()
            
            total_fe_time = end_time - start_time
            total_items = NUM_TEST_CALLS * batch_size
            items_per_sec = total_items / total_fe_time
            
            # Append latest data
            results.append({
                "threads": threads,
                "batch_size": batch_size,
                "total_time": total_fe_time,
                "throughput": items_per_sec
            })
            
            print(f"Done! Speed: {items_per_sec:.2f} items/s")
            
            # Progressive Save: Re-write the updated rankings to disk instantly
            write_report_to_disk(results)
            
        except Exception as e:
            print(f"FAILED due to error: {e}")
            continue

    print(f"\nGrid search complete! Final leaderboard compiled inside '{OUTPUT_FILENAME}'")

if __name__ == "__main__":
    try:
        run_benchmark()
    except KeyboardInterrupt:
        print("\n[!] Exiting benchmark safely...")
        sys.exit(0)
