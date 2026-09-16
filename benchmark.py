import time
import itertools
from fastembed import TextEmbedding

# 1. Define the testing grid aligned with codebase defaults (FE_THREADS = 4, EMBEDDING_BATCH_SIZE = 4)
TH_GRID = [1, 2, 4, 6, 8]
BATCH_GRID = [1, 2, 4, 8, 16]
NUM_TEST_CALLS = 10
OUTPUT_FILENAME = "fastembed_benchmark_results.md"

from ingest import extract_embedding_text

# 1. Define the testing grid aligned with codebase defaults (FE_THREADS = 4, EMBEDDING_BATCH_SIZE = 4)
TH_GRID = [1, 2, 4, 6, 8]
BATCH_GRID = [1, 2, 4, 8, 16]
NUM_TEST_CALLS = 50
OUTPUT_FILENAME = "fastembed_benchmark_results.md"

# Realistic Magic card sample dataset reflecting real-world card payload structures containing retained fields as detailed in docs/payload_schema.md
SAMPLE_CARDS = [
    {
        "id": "1d2e3f4a-5b6c-7d8e-9f0a-1b2c3d4e5f6a",
        "oracle_id": "00000000-0000-0000-0000-000000000001",
        "name": "Lightning Bolt",
        "lang": "en",
        "mana_cost": "{R}",
        "cmc": 1.0,
        "type_line": "Instant",
        "oracle_text": "Lightning Bolt deals 3 damage to any target.",
        "colors": ["R"],
        "color_identity": ["R"],
        "keywords": [],
        "power": None,
        "toughness": None,
        "loyalty": None,
        "defense": None,
        "card_faces": None,
        "set": "lea",
        "set_id": "11111111-1111-1111-1111-111111111111",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "collector_number": "161",
        "rarity": "common",
        "released_at": "1993-08-05",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/1/d/1d2e3f4a.jpg",
            "normal": "https://cards.scryfall.io/normal/front/1/d/1d2e3f4a.jpg",
            "art_crop": "https://cards.scryfall.io/art_crop/front/1/d/1d2e3f4a.jpg"
        },
        "legalities": {"standard": "not_legal", "modern": "legal", "commander": "legal"}
    },
    {
        "id": "2d3e4f5a-6b7c-8d9e-0f1a-2b3c4d5e6f7a",
        "oracle_id": "00000000-0000-0000-0000-000000000002",
        "name": "Counterspell",
        "lang": "en",
        "mana_cost": "{U}{U}",
        "cmc": 2.0,
        "type_line": "Instant",
        "oracle_text": "Counter target spell.",
        "colors": ["U"],
        "color_identity": ["U"],
        "keywords": [],
        "power": None,
        "toughness": None,
        "loyalty": None,
        "defense": None,
        "card_faces": None,
        "set": "lea",
        "set_id": "11111111-1111-1111-1111-111111111111",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "collector_number": "55",
        "rarity": "uncommon",
        "released_at": "1993-08-05",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/2/d/2d3e4f5a.jpg",
            "normal": "https://cards.scryfall.io/normal/front/2/d/2d3e4f5a.jpg",
            "art_crop": "https://cards.scryfall.io/art_crop/front/2/d/2d3e4f5a.jpg"
        },
        "legalities": {"standard": "not_legal", "modern": "legal", "commander": "legal"}
    },
    {
        "id": "3d4e5f6a-7b8c-9d0e-1f2a-3b4c5d6e7f8a",
        "oracle_id": "00000000-0000-0000-0000-000000000003",
        "name": "Llanowar Elves",
        "lang": "en",
        "mana_cost": "{G}",
        "cmc": 1.0,
        "type_line": "Creature — Elf Druid",
        "oracle_text": "{T}: Add {G}.",
        "colors": ["G"],
        "color_identity": ["G"],
        "keywords": [],
        "power": "1",
        "toughness": "1",
        "loyalty": None,
        "defense": None,
        "card_faces": None,
        "set": "lea",
        "set_id": "11111111-1111-1111-1111-111111111111",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "collector_number": "214",
        "rarity": "common",
        "released_at": "1993-08-05",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/3/d/3d4e5f6a.jpg",
            "normal": "https://cards.scryfall.io/normal/front/3/d/3d4e5f6a.jpg",
            "art_crop": "https://cards.scryfall.io/art_crop/front/3/d/3d4e5f6a.jpg"
        },
        "legalities": {"standard": "legal", "modern": "legal", "commander": "legal"}
    },
    {
        "id": "4d5e6f7a-8b9c-0d1e-2f3a-4b5c6d7e8f9a",
        "oracle_id": "00000000-0000-0000-0000-000000000004",
        "name": "Giant Growth",
        "lang": "en",
        "mana_cost": "{G}",
        "cmc": 1.0,
        "type_line": "Instant",
        "oracle_text": "Target creature gets +3/+3 until end of turn.",
        "colors": ["G"],
        "color_identity": ["G"],
        "keywords": [],
        "power": None,
        "toughness": None,
        "loyalty": None,
        "defense": None,
        "card_faces": None,
        "set": "lea",
        "set_id": "11111111-1111-1111-1111-111111111111",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "collector_number": "197",
        "rarity": "common",
        "released_at": "1993-08-05",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/4/d/4d5e6f7a.jpg",
            "normal": "https://cards.scryfall.io/normal/front/4/d/4d5e6f7a.jpg",
            "art_crop": "https://cards.scryfall.io/art_crop/front/4/d/4d5e6f7a.jpg"
        },
        "legalities": {"standard": "not_legal", "modern": "legal", "commander": "legal"}
    },
    {
        "id": "5d6e7f8a-9b0c-1d2e-3f4a-5b6c7d8e9f0a",
        "oracle_id": "00000000-0000-0000-0000-000000000005",
        "name": "Serra Angel",
        "lang": "en",
        "mana_cost": "{3}{W}{W}",
        "cmc": 5.0,
        "type_line": "Creature — Angel",
        "oracle_text": "Flying, vigilance",
        "colors": ["W"],
        "color_identity": ["W"],
        "keywords": ["Flying", "Vigilance"],
        "power": "4",
        "toughness": "4",
        "loyalty": None,
        "defense": None,
        "card_faces": None,
        "set": "lea",
        "set_id": "11111111-1111-1111-1111-111111111111",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "collector_number": "39",
        "rarity": "uncommon",
        "released_at": "1993-08-05",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/5/d/5d6e7f8a.jpg",
            "normal": "https://cards.scryfall.io/normal/front/5/d/5d6e7f8a.jpg",
            "art_crop": "https://cards.scryfall.io/art_crop/front/5/d/5d6e7f8a.jpg"
        },
        "legalities": {"standard": "not_legal", "modern": "legal", "commander": "legal"}
    },
    {
        "id": "6d7e8f9a-0b1c-2d3e-4f5a-6b7c8d9e0f1a",
        "oracle_id": "00000000-0000-0000-0000-000000000006",
        "name": "Wrath of God",
        "lang": "en",
        "mana_cost": "{2}{W}{W}",
        "cmc": 4.0,
        "type_line": "Sorcery",
        "oracle_text": "Destroy all creatures. They can't be regenerated.",
        "colors": ["W"],
        "color_identity": ["W"],
        "keywords": [],
        "power": None,
        "toughness": None,
        "loyalty": None,
        "defense": None,
        "card_faces": None,
        "set": "lea",
        "set_id": "11111111-1111-1111-1111-111111111111",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "collector_number": "43",
        "rarity": "rare",
        "released_at": "1993-08-05",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/6/d/6d7e8f9a.jpg",
            "normal": "https://cards.scryfall.io/normal/front/6/d/6d7e8f9a.jpg",
            "art_crop": "https://cards.scryfall.io/art_crop/front/6/d/6d7e8f9a.jpg"
        },
        "legalities": {"standard": "not_legal", "modern": "legal", "commander": "legal"}
    },
    {
        "id": "7d8e9f0a-1b2c-3d4e-5f6a-7b8c9d0e1f2a",
        "oracle_id": "00000000-0000-0000-0000-000000000007",
        "name": "Dark Ritual",
        "lang": "en",
        "mana_cost": "{B}",
        "cmc": 1.0,
        "type_line": "Instant",
        "oracle_text": "Add {B}{B}{B}.",
        "colors": ["B"],
        "color_identity": ["B"],
        "keywords": [],
        "power": None,
        "toughness": None,
        "loyalty": None,
        "defense": None,
        "card_faces": None,
        "set": "lea",
        "set_id": "11111111-1111-1111-1111-111111111111",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "collector_number": "100",
        "rarity": "common",
        "released_at": "1993-08-05",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/7/d/7d8e9f0a.jpg",
            "normal": "https://cards.scryfall.io/normal/front/7/d/7d8e9f0a.jpg",
            "art_crop": "https://cards.scryfall.io/art_crop/front/7/d/7d8e9f0a.jpg"
        },
        "legalities": {"standard": "not_legal", "modern": "legal", "commander": "legal"}
    },
    {
        "id": "8d9e0f1a-2b3c-4d5e-6f7a-8b9c0d1e2f3a",
        "oracle_id": "00000000-0000-0000-0000-000000000008",
        "name": "Birds of Paradise",
        "lang": "en",
        "mana_cost": "{G}",
        "cmc": 1.0,
        "type_line": "Creature — Bird",
        "oracle_text": "Flying. {T}: Add one mana of any color.",
        "colors": ["G"],
        "color_identity": ["G"],
        "keywords": ["Flying"],
        "power": "0",
        "toughness": "1",
        "loyalty": None,
        "defense": None,
        "card_faces": None,
        "set": "lea",
        "set_id": "11111111-1111-1111-1111-111111111111",
        "set_name": "Limited Edition Alpha",
        "set_type": "core",
        "collector_number": "193",
        "rarity": "rare",
        "released_at": "1993-08-05",
        "image_uris": {
            "small": "https://cards.scryfall.io/small/front/8/d/8d9e0f1a.jpg",
            "normal": "https://cards.scryfall.io/normal/front/8/d/8d9e0f1a.jpg",
            "art_crop": "https://cards.scryfall.io/art_crop/front/8/d/8d9e0f1a.jpg"
        },
        "legalities": {"standard": "not_legal", "modern": "legal", "commander": "legal"}
    },
    {
        "id": "9d0e1f2a-3b4c-5d6e-7f8a-9b0c1d2e3f4a",
        "oracle_id": "00000000-0000-0000-0000-000000000009",
        "name": "Delver of Secrets // Insectile Aberration",
        "lang": "en",
        "mana_cost": "",
        "cmc": 1.0,
        "type_line": "Creature — Human Wizard // Creature — Human Insect",
        "oracle_text": "",
        "colors": ["U"],
        "color_identity": ["U"],
        "keywords": ["Transform"],
        "power": None,
        "toughness": None,
        "loyalty": None,
        "defense": None,
        "card_faces": [
            {
                "name": "Delver of Secrets",
                "mana_cost": "{U}",
                "type_line": "Creature — Human Wizard",
                "oracle_text": "At the beginning of your upkeep, look at the top card of your library. You may reveal that card. If it's an instant or sorcery card, transform Delver of Secrets.",
                "power": "1",
                "toughness": "1"
            },
            {
                "name": "Insectile Aberration",
                "mana_cost": "",
                "type_line": "Creature — Human Insect",
                "oracle_text": "Flying",
                "power": "3",
                "toughness": "2"
            }
        ],
        "set": "isd",
        "set_id": "22222222-2222-2222-2222-222222222222",
        "set_name": "Innistrad",
        "set_type": "expansion",
        "collector_number": "51a",
        "rarity": "common",
        "released_at": "2011-09-30",
        "image_uris": None,
        "legalities": {"standard": "not_legal", "modern": "legal", "commander": "legal"}
    }
]

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
    run_benchmark()
