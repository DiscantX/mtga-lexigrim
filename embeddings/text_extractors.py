from typing import Any, Dict, List, Optional

def extract_clean_payload(card_obj: Dict[str, Any], rulings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Extract clean, essential metadata payload fields from raw Scryfall card dict in parity with docs/payload_schema.md."""
    payload = {
        # Core Identity & Rules
        "id": card_obj.get("id"),
        "oracle_id": card_obj.get("oracle_id"),
        "name": card_obj.get("name"),
        "lang": card_obj.get("lang"),
        "mana_cost": card_obj.get("mana_cost"),
        "cmc": card_obj.get("cmc"),
        "type_line": card_obj.get("type_line"),
        "oracle_text": card_obj.get("oracle_text"),
        "colors": card_obj.get("colors", []),
        "color_identity": card_obj.get("color_identity", []),
        "keywords": card_obj.get("keywords", []),
        "power": card_obj.get("power"),
        "toughness": card_obj.get("toughness"),
        "loyalty": card_obj.get("loyalty"),
        "defense": card_obj.get("defense"),
        "card_faces": card_obj.get("card_faces", []),
        
        # Set & Edition Metadata
        "set": card_obj.get("set"),
        "set_id": card_obj.get("set_id"),
        "set_name": card_obj.get("set_name"),
        "set_type": card_obj.get("set_type"),
        "collector_number": card_obj.get("collector_number"),
        "rarity": card_obj.get("rarity"),
        "released_at": card_obj.get("released_at"),
        
        # Media & Rendering
        "image_uris": card_obj.get("image_uris", {}),
        
        # Legalities
        "legalities": card_obj.get("legalities", {}),
    }
    payload["rulings"] = rulings or []
    return payload

def extract_embedding_text(card_obj: Dict[str, Any]) -> str:
    """Format rich descriptive text for embedding generation, handling single and double-faced cards."""
    name = card_obj.get("name", "")
    type_line = card_obj.get("type_line", "")
    mana_cost = card_obj.get("mana_cost", "")
    oracle_text = card_obj.get("oracle_text", "")

    if "card_faces" in card_obj and isinstance(card_obj["card_faces"], list) and card_obj["card_faces"]:
        face_texts = []
        for face in card_obj["card_faces"]:
            f_name = face.get("name", "")
            f_type = face.get("type_line", "")
            f_mana = face.get("mana_cost", "")
            f_oracle = face.get("oracle_text", "")
            face_texts.append(f"{f_name} | {f_type} | {f_mana} | {f_oracle}")
        oracle_text = " // ".join(face_texts)

    parts = [
        f"Card Name: {name}",
        f"Type: {type_line}",
        f"Mana Cost: {mana_cost}",
        f"Oracle Text: {oracle_text}"
    ]
    return "\n".join(parts)
