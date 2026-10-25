"""
Download queue item card widget.
Minimalist, high-contrast monochrome design with a three-dots context menu (⋮).
"""

import os
import subprocess
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from typing import Callable, Optional
from core.queue_manager import DownloadItem, QueueItemStatus
from core.formats import get_format_info
from gui.theme import (
    SURFACE_WHITE, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    STATUS_COLORS, FONT_BOLD, FONT_BODY, FONT_SMALL, FONT_BADGE
)

def format_duration(seconds: int) -> str:
    if not seconds:
        return ""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

class QueueItemCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        item: DownloadItem,
        on_cancel: Optional[Callable[[str], None]] = None,
        on_retry: Optional[Callable[[str], None]] = None,
        on_remove: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=SURFACE_WHITE,
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=8,
            **kwargs
        )
        self.item = item
        self.on_cancel = on_cancel
        self.on_retry = on_retry
        self.on_remove = on_remove
        self._ctk_thumb = None

        self.fmt_info = get_format_info(item.format_label)
        self._build_ui()
        self.update_data()

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)

        # 1. Left Thumbnail
        self.thumb_frame = ctk.CTkFrame(
            self,
            width=50,
            height=50,
            fg_color="#f1f5f9",
            border_color=BORDER_COLOR,
            border_width=1,
            corner_radius=6
        )
        self.thumb_frame.grid(row=0, column=0, rowspan=3, padx=(12, 10), pady=10, sticky="nsw")
        self.thumb_frame.pack_propagate(False)

        self.thumb_label = ctk.CTkLabel(
            self.thumb_frame,
            text="🎵",
            font=("Segoe UI", 16),
            text_color=TEXT_MUTED
        )
        self.thumb_label.pack(expand=True, fill="both")

        # 2. Middle Content Area
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, rowspan=3, sticky="nsew", padx=0, pady=(8, 8))
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Title Row
        title_box = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="ew")
        title_box.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            title_box,
            text=self.item.title,
            font=FONT_BOLD,
            text_color=TEXT_PRIMARY,
            anchor="w",
            wraplength=520
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        # Subtitle Row (Artist & Duration & Format)
        self.subtitle_label = ctk.CTkLabel(
            self.content_frame,
            text="",
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(1, 4))

        # Minimal Progress Bar
        self.progress_bar = ctk.CTkProgressBar(
            self.content_frame,
            height=4,
            corner_radius=2,
            progress_color="#0f172a",
            fg_color="#e2e8f0"
        )
        self.progress_bar.set(0.0)
        self.progress_bar.grid(row=2, column=0, sticky="ew", pady=(0, 3))

        # Status Line
        self.status_msg_label = ctk.CTkLabel(
            self.content_frame,
            text=self.item.status_message,
            font=FONT_SMALL,
            text_color=TEXT_SECONDARY,
            anchor="w"
        )
        self.status_msg_label.grid(row=3, column=0, sticky="w")

        # 3. Right Actions Area (Badge + Quick Action + Three-Dots Button)
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=2, rowspan=3, padx=(6, 12), pady=8, sticky="e")

        # Status Badge Pill
        self.status_badge = ctk.CTkLabel(
            self.right_frame,
            text=" QUEUED ",
            font=FONT_BADGE,
            text_color="#475569",
            fg_color="#f1f5f9",
            corner_radius=4,
            height=22
        )
        self.status_badge.grid(row=0, column=0, padx=(0, 6))

        # Quick Action Button (Play when completed, or cancel when active)
        self.quick_btn = ctk.CTkButton(
            self.right_frame,
            text="▶ Play",
            width=54,
            height=26,
            font=FONT_SMALL,
            fg_color="#f1f5f9",
            text_color=TEXT_PRIMARY,
            hover_color="#e2e8f0",
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._on_quick_btn_clicked
        )
        self.quick_btn.grid(row=0, column=1, padx=(0, 4))

        # Three-Dots Menu Button (⋮)
        self.menu_btn = ctk.CTkButton(
            self.right_frame,
            text="⋮",
            width=28,
            height=26,
            font=("Segoe UI", 13, "bold"),
            fg_color="#ffffff",
            text_color=TEXT_PRIMARY,
            hover_color="#f1f5f9",
            border_width=1,
            border_color=BORDER_COLOR,
            command=self._show_context_menu
        )
        self.menu_btn.grid(row=0, column=2)

    def update_data(self):
        """Refreshes the card visual state from its DownloadItem."""
        self.title_label.configure(text=self.item.title)

        # Subtitle info: Artist • Duration • Format
        meta_parts = []
        if self.item.artist and self.item.artist != "YouTube":
            meta_parts.append(self.item.artist)
        if self.item.duration:
            meta_parts.append(format_duration(self.item.duration))
        meta_parts.append(self.fmt_info.get("badge", "MP3"))
        self.subtitle_label.configure(text="  •  ".join(meta_parts))

        self.status_msg_label.configure(text=self.item.status_message)

        # Thumbnail Image
        if self.item.thumbnail_image and self._ctk_thumb is None:
            try:
                self._ctk_thumb = ctk.CTkImage(
                    light_image=self.item.thumbnail_image,
                    dark_image=self.item.thumbnail_image,
                    size=(50, 50)
                )
                self.thumb_label.configure(image=self._ctk_thumb, text="")
            except Exception:
                pass

        # Progress Bar
        progress_val = max(0.0, min(1.0, self.item.percent / 100.0))
        self.progress_bar.set(progress_val)

        # Status Badge Pill
        status = self.item.status
        badge_text = status
        if status == QueueItemStatus.EXISTS:
            badge_text = "IN FOLDER"
        elif status == QueueItemStatus.COMPLETED:
            badge_text = "DONE"
        elif status == QueueItemStatus.DOWNLOADING:
            badge_text = f"{int(self.item.percent)}%"

        bg_col, fg_col = STATUS_COLORS.get(status, ("#f1f5f9", "#475569"))
        self.status_badge.configure(
            text=f" {badge_text} ",
            fg_color=bg_col,
            text_color=fg_col
        )

        # Quick Button state
        if status in [QueueItemStatus.COMPLETED, QueueItemStatus.EXISTS]:
            self.quick_btn.configure(text="▶ Play", state="normal")
            self.quick_btn.grid(row=0, column=1, padx=(0, 4))
        elif status in [QueueItemStatus.DOWNLOADING, QueueItemStatus.FETCHING]:
            self.quick_btn.configure(text="✕", state="normal")
            self.quick_btn.grid(row=0, column=1, padx=(0, 4))
        elif status in [QueueItemStatus.FAILED, QueueItemStatus.CANCELLED]:
            self.quick_btn.configure(text="↻", state="normal")
            self.quick_btn.grid(row=0, column=1, padx=(0, 4))
        else:
            self.quick_btn.grid_forget()

    def _on_quick_btn_clicked(self):
        status = self.item.status
        if status in [QueueItemStatus.COMPLETED, QueueItemStatus.EXISTS]:
            self._play_file()
        elif status in [QueueItemStatus.DOWNLOADING, QueueItemStatus.FETCHING]:
            if self.on_cancel:
                self.on_cancel(self.item.id)
        elif status in [QueueItemStatus.FAILED, QueueItemStatus.CANCELLED]:
            if self.on_retry:
                self.on_retry(self.item.id)

    def _show_context_menu(self):
        """Displays the clean three-dots (⋮) popup context menu."""
        menu = tk.Menu(
            self,
            tearoff=0,
            bg="#ffffff",
            fg="#0f172a",
            activebackground="#f1f5f9",
            activeforeground="#0f172a",
            bd=1,
            relief="solid",
            font=("Segoe UI", 9)
        )

        status = self.item.status

        # Action: Resume / Retry (Stuck, cancelled, or failed)
        if status in [QueueItemStatus.FAILED, QueueItemStatus.CANCELLED, QueueItemStatus.EXISTS]:
            action_label = "Resume / Retry Download" if status != QueueItemStatus.EXISTS else "Redownload / Overwrite"
            menu.add_command(
                label=f"↻  {action_label}",
                command=lambda: self.on_retry(self.item.id) if self.on_retry else None
            )

        # Action: Play (if file exists)
        if self.item.filepath and os.path.isfile(self.item.filepath):
            menu.add_command(label="▶  Play media", command=self._play_file)
            menu.add_command(label="📁  Show in File Explorer", command=self._open_in_folder)

        # Action: Cancel (if active)
        if status in [QueueItemStatus.DOWNLOADING, QueueItemStatus.FETCHING, QueueItemStatus.QUEUED]:
            menu.add_command(
                label="✕  Cancel Download",
                command=lambda: self.on_cancel(self.item.id) if self.on_cancel else None
            )

        menu.add_separator()

        # Action: Copy Link
        menu.add_command(label="📋  Copy Link", command=self._copy_link)

        # Action: Remove
        menu.add_command(
            label="🗑  Remove from Queue",
            command=lambda: self.on_remove(self.item.id) if self.on_remove else None
        )

        # Calculate position under the button
        try:
            x = self.menu_btn.winfo_rootx()
            y = self.menu_btn.winfo_rooty() + self.menu_btn.winfo_height() + 2
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def _play_file(self):
        if self.item.filepath and os.path.isfile(self.item.filepath):
            try:
                os.startfile(self.item.filepath)
            except Exception as e:
                print(f"Error opening audio: {e}")

    def _open_in_folder(self):
        filepath = self.item.filepath
        if filepath and os.path.isfile(filepath):
            try:
                subprocess.Popen(f'explorer /select,"{os.path.normpath(filepath)}"')
                return
            except Exception:
                pass
        if os.path.isdir(self.item.download_dir):
            try:
                os.startfile(self.item.download_dir)
            except Exception:
                pass

    def _copy_link(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.item.url)
        except Exception:
            pass
