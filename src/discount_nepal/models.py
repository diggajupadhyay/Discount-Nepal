"""Product data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Product:
    """A single discounted product observed on a store."""

    website: str
    name: str
    regular_price: str
    sale_price: str
    url: str
    image_url: str = "N/A"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "website": self.website,
            "name": self.name,
            "regular_price": self.regular_price,
            "sale_price": self.sale_price,
            "url": self.url,
            "image_url": self.image_url,
            "timestamp": self.timestamp,
        }

    @property
    def is_on_sale(self) -> bool:
        """True when a distinct sale price is present and lower than regular."""
        try:
            reg = float(
                "".join(c for c in self.regular_price if c.isdigit() or c == ".")
            )
            sale = float(
                "".join(c for c in self.sale_price if c.isdigit() or c == ".")
            )
            return sale > 0 and reg > 0 and sale < reg
        except ValueError:
            return False

    @property
    def discount_percent(self) -> Optional[int]:
        """Rounded discount percentage, or None when not on sale."""
        if not self.is_on_sale:
            return None
        try:
            reg = float(
                "".join(c for c in self.regular_price if c.isdigit() or c == ".")
            )
            sale = float(
                "".join(c for c in self.sale_price if c.isdigit() or c == ".")
            )
            return round((reg - sale) / reg * 100)
        except ValueError:
            return None

    def __post_init__(self) -> None:
        # Normalise empty / missing fields.
        for name in ("website", "name", "regular_price", "sale_price", "url"):
            value = getattr(self, name)
            if not value or str(value).strip().lower() in {"n/a", "none", ""}:
                setattr(self, name, "N/A")
