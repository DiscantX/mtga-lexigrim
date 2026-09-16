from collections import Counter
from dataclasses import dataclass, field, fields
import json
import os
from typing import Any, Dict, List, Optional
from tqdm import tqdm

JSONL_PATH = "corpus/default-cards-20260915210531.jsonl"


def stream_objects_with_pos(file_path: str, chunk_size: int = 65536, skipped_items: Optional[List[Dict[str, Any]]] = None):
    """Streams JSON objects sequentially without loading the whole file into RAM, handling JSON decode errors gracefully."""
    decoder = json.JSONDecoder()
    buffer = ""
    bytes_read = 0
    if skipped_items is None:
        skipped_items = []

    with open(file_path, "r", encoding="utf-8") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                while buffer:
                    buffer = buffer.strip()
                    if not buffer:
                        break
                    try:
                        card_obj, index = decoder.raw_decode(buffer)
                        yield card_obj, bytes_read
                        buffer = buffer[index:]
                    except json.JSONDecodeError as e:
                        skipped_items.append({"buffer": buffer, "error": str(e)})
                        print(f"[WARNING] Skipping unparseable JSON at EOF: {e}. Buffer segment: {buffer[:100]}...")
                        newline_idx = buffer.find("\n")
                        if newline_idx != -1:
                            buffer = buffer[newline_idx + 1:]
                        else:
                            break
                break

            bytes_read = f.tell()
            buffer += chunk

            while buffer:
                buffer = buffer.strip()
                if not buffer:
                    break
                try:
                    card_obj, index = decoder.raw_decode(buffer)
                    yield card_obj, bytes_read
                    buffer = buffer[index:]
                except json.JSONDecodeError as e:
                    newline_idx = buffer.find("\n")
                    if newline_idx != -1:
                        bad_line = buffer[:newline_idx]
                        skipped_items.append({"line": bad_line, "error": str(e)})
                        print(f"[WARNING] Skipping malformed JSON line due to decode error: {e}. Content: {bad_line[:100]}...")
                        buffer = buffer[newline_idx + 1:]
                    else:
                        break


def generate_dataclass_code(file_path: str, output_py_path: str = "card_model.py"):
    """Analyzes all key occurrences and data types across the dataset,

    then generates a strongly-typed Python dataclass file.
    """
    key_counts = Counter()
    key_types: Dict[str, set] = {}
    total_cards = 0
    file_size = os.path.getsize(file_path)

    print("Analyzing dataset schema...")
    with tqdm(
        total=file_size,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc="Inspecting Keys",
    ) as pbar:
        last_pos = 0
        for card_obj, current_pos in stream_objects_with_pos(file_path):
            pbar.update(current_pos - last_pos)
            last_pos = current_pos

            total_cards += 1
            for k, v in card_obj.items():
                key_counts[k] += 1
                if k not in key_types:
                    key_types[k] = set()

                # Infer basic Python type
                if v is None:
                    key_types[k].add("None")
                elif isinstance(v, bool):
                    key_types[k].add("bool")
                elif isinstance(v, int):
                    key_types[k].add("int")
                elif isinstance(v, float):
                    key_types[k].add("float")
                elif isinstance(v, str):
                    key_types[k].add("str")
                elif isinstance(v, list):
                    key_types[k].add("List[Any]")
                elif isinstance(v, dict):
                    key_types[k].add("Dict[str, Any]")

    # Build dataclass field lines
    dataclass_lines = [
        "# Auto-generated MTG Card Dataclass",
        "from dataclasses import dataclass, field",
        "from typing import Optional, List, Dict, Any\n\n",
        "@dataclass",
        "class Card:",
        "    \"\"\"Represents a single Magic: The Gathering card object.\"\"\"",
    ]

    # Required fields (100% presence) must come before optional fields
    required_fields = []
    optional_fields = []

    for key in sorted(key_counts.keys()):
        count = key_counts[key]
        types = key_types[key] - {"None"}

        # Map inferred type
        if len(types) == 1:
            type_str = list(types)[0]
        elif len(types) > 1:
            type_str = "Any"
        else:
            type_str = "Any"

        # Sanitize variable names (e.g. key names that match python keywords)
        field_name = f"{key}_" if key in {"id", "type", "format", "import"} else key

        if count == total_cards and "None" not in key_types[key]:
            # Always present -> Required field
            required_fields.append(f"    {field_name}: {type_str}")
        else:
            # Missing in some entries -> Optional field with default None
            optional_fields.append(
                f"    {field_name}: Optional[{type_str}] = None"
            )

    dataclass_lines.extend(required_fields)
    dataclass_lines.extend(optional_fields)

    # Classmethod to parse dictionary into dataclass handling optional/extra keys
    mapper_code = """
    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        \"\"\"Safely instantiates a Card object from a dictionary, ignoring extra keys

        and assigning None to missing optional fields.
        \"\"\"
        valid_keys = {f.name for f in fields(cls)}
        filtered_data = {}

        for k, v in data.items():
            key_name = f"{k}_" if k in {"id", "type", "format", "import"} else k
            if key_name in valid_keys:
                filtered_data[key_name] = v

        return cls(**filtered_data)
"""
    dataclass_lines.append(mapper_code)

    with open(output_py_path, "w", encoding="utf-8") as f:
        f.write("\n".join(dataclass_lines))

    print(f"\nGenerated `{output_py_path}` successfully!")


if __name__ == "__main__":
    generate_dataclass_code(JSONL_PATH)