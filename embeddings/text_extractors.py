from typing import Any, Dict, List

def extract_clean_payload(card_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Extract clean, essential metadata payload fields from raw Scryfall card dict."""
    return {
        "id": card_obj.get("id"),
        "name": card_obj.get("name"),
        "mana_cost": card_obj.get("mana_cost"),
        "type_line": card_obj.get("type_line"),
        "oracle_text": card_obj.get("oracle_text"),
        "colors": card_obj.get("colors", []),
        "color_identity": card_obj.get("color_identity", []),
        "rarity": card_obj.get("rarity"),
        "set": card_obj.get("set"),
        "set_name": card_obj.get("set_name"),
        "image_uris": card_obj.get("image_uris", {}),
        "card_faces": card_obj.get("card_faces", []),
    }

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
