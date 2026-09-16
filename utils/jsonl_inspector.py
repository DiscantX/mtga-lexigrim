from collections import Counter
import json
import os
from tqdm import tqdm

JSONL_PATH = 'corpus/default-cards-20260915210531.jsonl'


def stream_objects_with_pos(file_path: str, chunk_size: int = 65536):
    """Streams and decodes JSON objects sequentially into Python dictionaries

    without relying on strict newline characters (\n) or reading the whole file
    into RAM. Yields tuples of (python_dict, current_byte_position).
    """
    decoder = json.JSONDecoder()
    buffer = ""
    bytes_read = 0

    with open(file_path, "r", encoding="utf-8") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break

            bytes_read = f.tell()
            buffer += chunk

            while buffer:
                buffer = buffer.strip()
                try:
                    # Decodes raw JSON string segment into a native Python dict
                    card_obj, index = decoder.raw_decode(buffer)
                    yield card_obj, bytes_read
                    buffer = buffer[index:]  # Advance past parsed object
                except json.JSONDecodeError:
                    # Incomplete JSON object at end of buffer; read next chunk
                    break


def analyze_key_frequency(file_path: str):
    """Reads the JSON dataset streamingly, tracks key occurrence frequencies,

    and displays a real-time byte progress bar.
    """
    key_counts = Counter()
    total_cards = 0
    file_size = os.path.getsize(file_path)

    # Setup progress bar tracking total file size in bytes
    with tqdm(
        total=file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc="Analyzing Cards",
    ) as pbar:
        last_pos = 0

        # Stream objects line-by-line / chunk-by-chunk
        for card_obj, current_pos in stream_objects_with_pos(file_path):
            # Advance progress bar based on disk bytes read
            pbar.update(current_pos - last_pos)
            last_pos = current_pos

            # 'card_obj' is now a fully usable native Python dict
            total_cards += 1
            key_counts.update(card_obj.keys())

    # Output key statistics
    print(f"\nAnalyzed {total_cards:,} total cards.\n")
    print(f"{'Key Name':<35} | {'Count':<10} | {'Presence (%)':<10}")
    print("-" * 62)

    for key, count in key_counts.most_common():
        percentage = (count / total_cards) * 100 if total_cards > 0 else 0
        print(f"{key:<35} | {count:<10,} | {percentage:.1f}%")


if __name__ == "__main__":
    analyze_key_frequency(JSONL_PATH)