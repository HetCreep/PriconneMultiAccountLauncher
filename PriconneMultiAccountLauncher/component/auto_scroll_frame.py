"""Drop-in replacement for CTkScrollableFrame that auto-hides its scrollbar
when the inner content fits the visible area.

Behavior:
- After initial layout (and on every <Configure>), measure content vs canvas height.
- If content fits → `grid_remove()` the scrollbar (preserves position metadata).
- If content overflows → restore the scrollbar via `grid()`.

Safe across CTk versions because failures are silently swallowed (UI cosmetic,
not functional). Worst case: scrollbar always visible (same as plain
CTkScrollableFrame).
"""

import logging

from customtkinter import CTkScrollableFrame

logger = logging.getLogger(__name__)

# Fudge factor for height comparison (rounding + 1px borders).
_HEIGHT_TOLERANCE = 2


class CTkAutoScrollFrame(CTkScrollableFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._auto_scroll_grid_info: dict | None = None
        try:
            self._auto_scroll_grid_info = dict(self._scrollbar.grid_info())
        except Exception as exc:  # noqa: BLE001
            logger.debug("AutoScroll: cannot read scrollbar grid_info: %s", exc)

        self.bind("<Configure>", self._auto_scroll_reeval, add="+")
        # Delay first check until widgets are sized.
        self.after(50, self._auto_scroll_reeval)

    def _auto_scroll_reeval(self, event=None) -> None:
        try:
            self.update_idletasks()
            canvas_h = self._parent_canvas.winfo_height()
            bbox = self._parent_canvas.bbox("all")
            content_h = (bbox[3] - bbox[1]) if bbox else 0
            if content_h <= canvas_h + _HEIGHT_TOLERANCE:
                self._scrollbar.grid_remove()
            else:
                info = self._auto_scroll_grid_info or {}
                # Filter to keys grid() accepts; ignore '-in'/'-id' etc.
                keys = ("row", "column", "rowspan", "columnspan", "sticky", "padx", "pady")
                kw = {k: info[k] for k in keys if k in info}
                if kw:
                    self._scrollbar.grid(**kw)
                else:
                    self._scrollbar.grid()
        except Exception as exc:  # noqa: BLE001
            logger.debug("AutoScroll: reeval failed (cosmetic): %s", exc)
