# Auto-generated MTG Card Dataclass
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class Card:
    """Represents a single Magic: The Gathering card object."""
    artist: str
    booster: bool
    border_color: str
    collector_number: str
    color_identity: List[Any]
    digital: bool
    finishes: List[Any]
    foil: bool
    frame: str
    full_art: bool
    game_changer: bool
    games: List[Any]
    highres_image: bool
    id_: str
    image_status: str
    image_updated_at: str
    keywords: List[Any]
    lang: str
    layout: str
    legalities: Dict[str, Any]
    multiverse_ids: List[Any]
    name: str
    nonfoil: bool
    object: str
    oversized: bool
    prices: Dict[str, Any]
    prints_search_uri: str
    promo: bool
    rarity: str
    related_uris: Dict[str, Any]
    released_at: str
    reprint: bool
    reserved: bool
    rulings_uri: str
    scryfall_set_uri: str
    scryfall_uri: str
    set: str
    set_id: str
    set_name: str
    set_search_uri: str
    set_type: str
    set_uri: str
    story_spotlight: bool
    textless: bool
    uri: str
    variation: bool
    all_parts: Optional[List[Any]] = None
    arena_id: Optional[int] = None
    artist_ids: Optional[List[Any]] = None
    attraction_lights: Optional[List[Any]] = None
    card_back_id: Optional[str] = None
    card_faces: Optional[List[Any]] = None
    cardmarket_id: Optional[int] = None
    cmc: Optional[float] = None
    color_indicator: Optional[List[Any]] = None
    colors: Optional[List[Any]] = None
    content_warning: Optional[bool] = None
    defense: Optional[str] = None
    edhrec_rank: Optional[int] = None
    flavor_name: Optional[str] = None
    flavor_text: Optional[str] = None
    frame_effects: Optional[List[Any]] = None
    hand_modifier: Optional[str] = None
    illustration_id: Optional[str] = None
    image_uris: Optional[Dict[str, Any]] = None
    life_modifier: Optional[str] = None
    loyalty: Optional[str] = None
    mana_cost: Optional[str] = None
    mtgo_foil_id: Optional[int] = None
    mtgo_id: Optional[int] = None
    oracle_id: Optional[str] = None
    oracle_text: Optional[str] = None
    penny_rank: Optional[int] = None
    power: Optional[str] = None
    preview: Optional[Dict[str, Any]] = None
    printed_name: Optional[str] = None
    printed_text: Optional[str] = None
    printed_type_line: Optional[str] = None
    produced_mana: Optional[List[Any]] = None
    promo_types: Optional[List[Any]] = None
    purchase_uris: Optional[Dict[str, Any]] = None
    resource_id: Optional[str] = None
    security_stamp: Optional[str] = None
    tcgplayer_etched_id: Optional[int] = None
    tcgplayer_id: Optional[int] = None
    toughness: Optional[str] = None
    type_line: Optional[str] = None
    variation_of: Optional[str] = None
    watermark: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        """Safely instantiates a Card object from a dictionary, ignoring extra keys

        and assigning None to missing optional fields.
        """
        valid_keys = {f.name for f in fields(cls)}
        filtered_data = {}

        for k, v in data.items():
            key_name = f"{k}_" if k in {"id", "type", "format", "import"} else k
            if key_name in valid_keys:
                filtered_data[key_name] = v

        return cls(**filtered_data)
