# Milestone 3 Implementation Plan: Pluggable Widgets, Colors, and AI Support

## 1. Overview & Objectives
Milestone 3 introduces rich ANSI styling, pluggable project-specific widgets (such as card details and deck lists), and asynchronous AI chatbot integration. It completes the unified interactive CLI by preparing middleware for Phase 2 LLM interactions.

---

## 2. Directory & File Structure
```
ui/
├── widget.py                    # Pluggable widget abstract base interface
├── cli/
    └── widgets/
        ├── card_view.py         # Card layout rendering plug-in
        └── deck_view.py         # Deck list composition viewer
```

---

## 3. Step-by-Step Implementation Instructions

### Step 1: Define Pluggable Widget Interface ([`ui/widget.py`](ui/widget.py:1))
- **File Path**: [`ui/widget.py`](ui/widget.py:1)
- **Class**: [`PluggableWidget`](ui/widget.py:1) (ABC)
- **Methods**:
  - `update(self, data: Dict[str, Any]) -> None`
  - `render(self, width: int, height: int) -> Any`

### Step 2: Implement MTG-Specific Widgets
- **File Path**: [`ui/cli/widgets/card_view.py`](ui/cli/widgets/card_view.py:1) and [`ui/cli/widgets/deck_view.py`](ui/cli/widgets/deck_view.py:1)
- **Action**: Create `CardDetailWidget` and `DeckListWidget` inheriting from [`PluggableWidget`](ui/widget.py:1) to format card printings, mana curves, rules payloads, and archetype compositions cleanly with ANSI color codes.

### Step 3: Add ANSI Styling and Theme Support
- **File Path**: [`ui/cli/app.py`](ui/cli/app.py:1)
- **Action**: Configure `prompt_toolkit.styles.Style` dictionaries to establish distinct color classes for headers, search scores, rarity highlights, and user prompts.

### Step 4: Integrate AI Chat Middleware Hook
- **File Path**: [`ui/controller.py`](ui/controller.py:1)
- **Action**: Add an asynchronous method `stream_ai_chat_response(self, user_prompt: str)` in [`LexiGrimSession`](ui/controller.py:1) prepared for Phase 2 Google Gemini integration, routing incoming tokens to the interactive CLI output area in real time.

---

## 4. Acceptance Criteria
- Search results and card details render with vibrant ANSI color highlights (mana symbols, rarities, scores).
- Pluggable widgets can be registered and rendered inside the split viewport.
- The session controller successfully supports chat history hooks and streaming response hooks for upcoming AI integration.
