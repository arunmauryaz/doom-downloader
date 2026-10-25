"""
Theme and styling definitions for Doom Downloader.
Minimalist, high-contrast monochrome design (Black & White).
Clean, quiet, and professional — avoiding AI-style gradients or neon colors.
"""

# Neutral Monochrome Color Palette
BG_CANVAS = ("#f5f6f8", "#111318")           # Soft off-white main background
SURFACE_WHITE = ("#ffffff", "#1b1e25")       # Pure white cards / panels
SURFACE_MUTED = ("#eef1f5", "#252a34")       # Subtle neutral grey surface
BORDER_COLOR = ("#dfe3eb", "#323846")        # Crisp 1px border
BORDER_FOCUS = ("#202939", "#edf0f7")        # Focused border

TEXT_PRIMARY = ("#202939", "#edf0f7")        # Deep charcoal/black
TEXT_SECONDARY = ("#5c687c", "#aab4c6")      # Clean neutral grey
TEXT_MUTED = ("#788397", "#8994a8")          # Dim grey placeholder
TEXT_WHITE = ("#ffffff", "#1b1e25")          # White on black buttons

# Action Buttons
BTN_PRIMARY_BG = "#4263eb"      # Solid black
BTN_PRIMARY_HOVER = "#3451ce"
BTN_PRIMARY_TEXT = "#ffffff"

BTN_SECONDARY_BG = ("#ffffff", "#1b1e25")    # Clean white button
BTN_SECONDARY_HOVER = ("#eef1f5", "#252a34")
BTN_SECONDARY_TEXT = ("#202939", "#edf0f7")
BTN_SECONDARY_BORDER = ("#dfe3eb", "#323846")

# Progress bar
PROGRESS_TRACK = ("#dfe3eb", "#323846")
PROGRESS_FILL = ("#202939", "#edf0f7")

# Subtle Status Badges
STATUS_COLORS = {
    "QUEUED": ("#f1f5f9", "#475569"),
    "FETCHING": ("#f8fafc", "#334155"),
    "DOWNLOADING": ("#0f172a", "#ffffff"),
    "CONVERTING": ("#334155", "#ffffff"),
    "COMPLETED": ("#f0fdf4", "#166534"),
    "EXISTS": ("#f1f5f9", "#334155"),
    "FAILED": ("#fef2f2", "#991b1b"),
    "CANCELLED": ("#f4f4f5", "#71717a")
}

# Typography
FONT_FAMILY = "Segoe UI"
FONT_TITLE = (FONT_FAMILY, 28, "bold")
FONT_HEADING = (FONT_FAMILY, 17, "bold")
FONT_BODY = (FONT_FAMILY, 13)
FONT_BOLD = (FONT_FAMILY, 13, "bold")
FONT_SMALL = (FONT_FAMILY, 12)
FONT_BADGE = (FONT_FAMILY, 9, "bold")
