from collections import Counter
import os
from tqdm import tqdm
from core.streaming import JsonlStreamReader

JSONL_PATH = 'corpus/default-cards-20260915210531.jsonl'


def analyze_key_frequency(file_path: str):
    """Reads the JSON dataset streamingly, tracks key occurrence frequencies,
    and displays a real-time byte progress bar.
    """
    key_counts = Counter()
    total_cards = 0
    file_size = os.path.getsize(file_path)

    stream_reader = JsonlStreamReader(file_path)
    skipped_items = []

    # Setup progress bar tracking total file size in bytes
    with tqdm(
        total=file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc="Analyzing Cards",
    ) as pbar:
        last_pos = 0

        # Stream objects line-by-line / chunk-by-chunk using JsonlStreamReader
        for card_obj, current_pos in stream_reader.stream(skipped_items):
            # Advance progress bar based on disk bytes read
            if current_pos > last_pos:
                pbar.update(current_pos - last_pos)
                last_pos = current_pos

            # 'card_obj' is now a fully usable native Python dict
            total_cards += 1
            key_counts.update(card_obj.keys())

    # Output key statistics
    print(f"\nAnalyzed {total_cards:,} total cards.\n")
    if skipped_items:
        print(f"Skipped {len(skipped_items):,} malformed items.")
    print(f"{'Key Name':<35} | {'Count':<10} | {'Presence (%)':<10}")
    print("-" * 62)

    for key, count in key_counts.most_common():
        percentage = (count / total_cards) * 100 if total_cards > 0 else 0
        print(f"{key:<35} | {count:<10,} | {percentage:.1f}%")


if __name__ == "__main__":
    analyze_key_frequency(JSONL_PATH)
