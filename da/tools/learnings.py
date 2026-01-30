"""Tools for searching and saving learnings."""

import json
from datetime import datetime, timezone

from agno.knowledge import Knowledge
from agno.knowledge.reader.text_reader import TextReader
from agno.tools import tool
from agno.utils.log import logger


def create_learnings_tools(knowledge: Knowledge) -> tuple:
    """Create search_learnings and save_learning tools."""

    @tool
    def search_learnings(query: str, limit: int = 5) -> str:
        """Search for relevant learnings from past interactions.

        Args:
            query: Keywords to search for (e.g., "date parsing", "position type")
            limit: Max results
        """
        try:
            results = knowledge.search(query=query, max_results=limit)
            if not results:
                return "No relevant learnings found."

            learnings = []
            for i, r in enumerate(results, 1):
                content = r.content if hasattr(r, "content") else str(r)
                try:
                    data = json.loads(content)
                    if data.get("type") == "learning":
                        learnings.append(f"{i}. **{data.get('title', 'Untitled')}**\n   {data.get('learning', '')}")
                except json.JSONDecodeError:
                    learnings.append(f"{i}. {content[:200]}")

            return (
                f"Found {len(learnings)} learning(s):\n\n" + "\n".join(learnings)
                if learnings
                else "No learnings found."
            )

        except (AttributeError, TypeError, ValueError) as e:
            logger.error(f"search_learnings failed: {e}")
            return f"Error: {e}"

    @tool
    def save_learning(
        title: str,
        learning: str,
        context: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        """Save a discovered pattern for future reference.

        Call search_learnings FIRST to check for duplicates.

        Args:
            title: Searchable title (e.g., "Date parsing in race_wins")
            learning: The actionable insight
            context: When this applies
            tags: Categories
        """
        if not title or not title.strip():
            return "Error: Title required."
        if not learning or not learning.strip():
            return "Error: Learning required."

        try:
            payload = {
                "type": "learning",
                "title": title.strip(),
                "learning": learning.strip(),
                "context": context.strip() if context else None,
                "tags": tags or [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            payload = {k: v for k, v in payload.items() if v is not None}

            knowledge.insert(
                name=f"learning_{title.strip().lower().replace(' ', '_')[:50]}",
                text_content=json.dumps(payload, ensure_ascii=False, indent=2),
                reader=TextReader(),
                skip_if_exists=True,
            )
            return f"Learning saved: {title}"

        except (AttributeError, TypeError, ValueError, OSError) as e:
            logger.error(f"save_learning failed: {e}")
            return f"Error: {e}"

    return search_learnings, save_learning
