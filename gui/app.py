"""
Doom Downloader desktop interface.
"""

import os
import sys
import threading
import subprocess
import queue
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from core.config import config
from core.formats import FORMAT_NAMES, VIDEO_FORMAT_NAMES, DEFAULT_FORMAT, FILE_FORMAT, get_format_info
from core.downloader import AudioDownloader
from core.queue_manager import QueueManager, DownloadItem, QueueItemStatus
from core.url_parser import (
    extract_urls_from_text, is_playlist_url, fetch_playlist_entries, clean_video_url,
    is_spotify_url
)
from gui.theme import (
    BG_CANVAS, SURFACE_WHITE, SURFACE_MUTED, BORDER_COLOR,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BTN_PRIMARY_BG, BTN_PRIMARY_HOVER, BTN_PRIMARY_TEXT,
    BTN_SECONDARY_BG, BTN_SECONDARY_HOVER, BTN_SECONDARY_TEXT, BTN_SECONDARY_BORDER,
    FONT_TITLE, FONT_HEADING, FONT_BODY, FONT_BOLD, FONT_SMALL
)
from gui.queue_item_card import QueueItemCard

class DownloaderApp(ctk.CTk):
    def __init__(self, downloader: AudioDownloader, queue_manager: QueueManager):
        super().__init__()

        self.downloader = downloader
        self.queue_manager = queue_manager

        # Window Setup
        self.title("Doom Downloader")
        self.geometry("1160x860")
        self.minsize(960, 760)

        # Configure appearance to clean Light by default
        current_theme = config.get("theme", "Light")
        ctk.set_appearance_mode(current_theme)
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BG_CANVAS)

        # Internal state
        self.card_widgets = {}
        self.current_filter = "All"
        self.selected_format = config.get("default_format", DEFAULT_FORMAT)
        self.media_mode = "File" if self.selected_format == FILE_FORMAT else "Video" if self.selected_format in VIDEO_FORMAT_NAMES else "Audio"
        self.input_mode = "Single"
        self._adding = False
        self._library_visible = False
        self._library_generation = 0
        self._library_completed = set()
        self.library_dir = config.get("download_dir")
        self._events = queue.Queue()
        self.download_dir = config.get("download_dir")

        # Queue Manager Callbacks
        self.queue_manager.on_item_added = self._on_queue_item_added
        self.queue_manager.on_item_updated = self._on_queue_item_updated
        self.queue_manager.on_stats_updated = self._on_stats_updated

        self._create_header()
        self._create_footer()
        self.workspace = ctk.CTkFrame(self, fg_color="transparent")
        self.workspace.pack(fill="both", expand=True)
        self.main_frame = ctk.CTkFrame(self.workspace, fg_color="transparent")
        self.main_frame.pack(side="left", fill="both", expand=True)
        self._create_input_panel()
        self._create_queue_header()
        self._create_queue_area()
        self._create_library()
        self.after(80, self._drain_events)
        self.bind("<Control-Return>", self._download_shortcut)

        # Handle close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _button(self, parent, text, command, primary=False, **kwargs):
        return ctk.CTkButton(parent, text=text, command=command, height=36,
            corner_radius=8, font=FONT_BOLD, fg_color=BTN_PRIMARY_BG if primary else SURFACE_MUTED,
            text_color=BTN_PRIMARY_TEXT if primary else TEXT_PRIMARY,
            hover_color=BTN_PRIMARY_HOVER if primary else BTN_SECONDARY_HOVER, **kwargs)

    def _label(self, parent, text, font=FONT_BODY, color=TEXT_PRIMARY, **kwargs):
        return ctk.CTkLabel(parent, text=text, font=font, text_color=color, **kwargs)

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(24, 18))
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left")
        self._label(brand, "Doom Downloader", FONT_TITLE).pack(anchor="w")
        self._button(header, "Theme", self._toggle_theme, width=80).pack(side="right", padx=(8, 0))
        self._button(header, "Files", self._toggle_library, width=90).pack(side="right")

    def _create_input_panel(self):
        panel = ctk.CTkFrame(self.main_frame, fg_color=SURFACE_WHITE, border_width=1,
                             border_color=BORDER_COLOR, corner_radius=14)
        panel.pack(fill="x", padx=28)
        self.mode_switch = ctk.CTkSegmentedButton(panel, values=["Audio", "Video", "File"],
            command=self._on_mode_changed, font=FONT_BOLD, height=38,
            selected_color=BTN_PRIMARY_BG, selected_hover_color=BTN_PRIMARY_HOVER)
        self.mode_switch.set(self.media_mode)
        self.mode_switch.pack(pady=(22, 14))
        self.input_switch = ctk.CTkSegmentedButton(panel, values=["Single", "Bulk"],
            command=self._set_input_mode, font=FONT_SMALL, height=28,
            selected_color=BTN_PRIMARY_BG, selected_hover_color=BTN_PRIMARY_HOVER)
        self.input_switch.set("Single")
        self.input_switch.pack(pady=(0, 12))
        self.url_textbox = ctk.CTkTextbox(panel, height=46, corner_radius=12,
            fg_color=BG_CANVAS, border_color=BORDER_COLOR, border_width=1,
            text_color=TEXT_PRIMARY, font=FONT_BODY, wrap="none")
        self.url_textbox.pack(fill="x", padx=26, pady=(0, 8))
        self.url_textbox.bind("<KeyRelease>", self._input_changed)
        self.url_textbox.bind("<<Paste>>", lambda event: self.after(20, self._input_changed), add="+")
        self.url_textbox.bind("<Return>", self._input_return)
        self.url_textbox.bind("<Shift-Return>", self._bulk_newline)
        self.url_textbox.bind("<Control-Shift-Return>", self._bulk_newline)
        self.url_textbox.bind("<Control-Return>", self._download_shortcut)
        self.input_hint = self._label(panel, "Paste a link", FONT_SMALL, TEXT_MUTED)
        self.input_hint.pack()
        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.pack(pady=(8, 14))
        self._button(actions, "Paste", self._paste_clipboard, width=80).pack(side="left", padx=4)
        self._button(actions, "Clear", self._clear_input, width=70).pack(side="left", padx=4)
        self.download_btn = self._button(actions, "Download", self._start_download_action,
                                          primary=True, width=150)
        self.download_btn.pack(side="left", padx=4)
        controls = ctk.CTkFrame(panel, fg_color="transparent")
        controls.pack(pady=(0, 12))
        self._label(controls, "Output", FONT_SMALL, TEXT_SECONDARY).pack(side="left", padx=(0, 12))
        self.format_menu = ctk.CTkOptionMenu(controls, values=self._mode_formats(),
            command=self._on_format_changed, width=230, height=36, font=FONT_BODY,
            fg_color=SURFACE_MUTED, button_color=BTN_PRIMARY_BG, text_color=TEXT_PRIMARY,
            button_hover_color=BTN_PRIMARY_HOVER)
        self.format_menu.set(self.selected_format)
        self.format_menu.pack(side="left")
        self._button(controls, "Folder", self._browse_folder, width=80).pack(side="left", padx=(10, 0))
        options = ctk.CTkFrame(panel, fg_color="transparent")
        options.pack(pady=(0, 18))
        for index, (attr, label, key, default) in enumerate((
            ("cb_skip_existing", "Skip existing", "skip_existing", True),
            ("cb_auto_playlist", "Collections", "expand_playlists", True),
            ("cb_artwork", "Cover art", "embed_thumbnail", True),
            ("cb_metadata", "Metadata", "add_metadata", True))):
            cb = ctk.CTkCheckBox(options, text=label, font=FONT_SMALL,
                text_color=TEXT_SECONDARY, checkbox_width=18, checkbox_height=18,
                fg_color=BTN_PRIMARY_BG, hover_color=BTN_PRIMARY_HOVER, width=125)
            if config.get(key, default):
                cb.select()
            cb.grid(row=index // 2, column=index % 2, padx=18, pady=5, sticky="w")
            setattr(self, attr, cb)
        self._update_format_hint()

    def _mode_formats(self):
        return [FILE_FORMAT] if self.media_mode == "File" else VIDEO_FORMAT_NAMES if self.media_mode == "Video" else FORMAT_NAMES

    def _update_format_hint(self):
        self.cb_artwork.configure(state="normal" if self.media_mode == "Audio" else "disabled")
        for checkbox in (self.cb_metadata, self.cb_auto_playlist):
            checkbox.configure(state="disabled" if self.media_mode == "File" else "normal")
        self._input_changed()

    def _on_mode_changed(self, mode):
        self.media_mode = mode
        values = self._mode_formats()
        self.format_menu.configure(values=values)
        self.format_menu.set(values[0])
        self._on_format_changed(values[0])
        self._update_format_hint()

    def _set_input_mode(self, mode):
        if mode == "Single" and len(extract_urls_from_text(self.url_textbox.get("1.0", "end"))) > 1:
            mode = "Bulk"
        self.input_mode = mode
        self.input_switch.set(mode)
        self.url_textbox.configure(height=110 if mode == "Bulk" else 46)
        self._input_changed()

    def _input_changed(self, event=None):
        text = self.url_textbox.get("1.0", "end-1c")
        count = len(extract_urls_from_text(text))
        if count > 1 and self.input_mode != "Bulk":
            self.input_mode = "Bulk"
            self.input_switch.set("Bulk")
            self.url_textbox.configure(height=110)
        hint = f"{count} links" if count > 1 else "Direct file link" if self.media_mode == "File" else "Paste a link"
        self.input_hint.configure(text=hint)

    def _bulk_newline(self, event=None):
        self._set_input_mode("Bulk")
        self.url_textbox.insert("insert", "\n")
        return "break"

    def _input_return(self, event=None):
        if self.input_mode == "Single":
            self._start_download_action()
            return "break"
        return self._bulk_newline()

    def _download_shortcut(self, event=None):
        self._start_download_action()
        return "break"

    def _create_queue_header(self):
        bar = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        bar.pack(fill="x", padx=32, pady=(22, 8))
        self._label(bar, "Downloads", FONT_HEADING).pack(side="left")
        self.summary_label = self._label(bar, "0 items", FONT_SMALL, TEXT_SECONDARY)
        self.summary_label.pack(side="left", padx=16)
        self.pause_btn = self._button(bar, "Pause queue", self._toggle_queue, width=115)
        self.pause_btn.pack(side="right")
        self._button(bar, "Clear finished", self._clear_completed, width=115).pack(side="right", padx=8)
        self._button(bar, "Retry failed", self._retry_failed, width=105).pack(side="right")
        filters = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        filters.pack(fill="x", padx=32, pady=(0, 8))
        self.filter_seg = ctk.CTkSegmentedButton(filters,
            values=["All", "Downloading", "Completed", "Queued", "Failed"],
            command=self._on_filter_changed, font=FONT_SMALL, height=30,
            selected_color=BTN_PRIMARY_BG, selected_hover_color=BTN_PRIMARY_HOVER)
        self.filter_seg.set("All")
        self.filter_seg.pack(side="left")

    def _toggle_queue(self):
        if self.queue_manager.is_paused:
            self.queue_manager.resume()
        else:
            self.queue_manager.pause()
        self.pause_btn.configure(text="Resume queue" if self.queue_manager.is_paused else "Pause queue")

    def _retry_failed(self):
        with self.queue_manager.lock:
            ids = [item.id for item in self.queue_manager.items if item.status == QueueItemStatus.FAILED]
        for item_id in ids:
            self.queue_manager.retry_item(item_id)

    def _create_queue_area(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent", corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True, padx=26, pady=4)
        self.empty_label = self._label(self.scroll_frame,
            "No downloads", color=TEXT_MUTED,
            justify="center")
        self.empty_label.pack(pady=65)

    def _create_footer(self):
        footer = ctk.CTkFrame(self, fg_color=SURFACE_WHITE, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        status = "Ready" if self.downloader.is_ffmpeg_available() else "FFmpeg missing — add it to bin/"
        self.footer_label = self._label(footer, f"{status}  ·  {self.download_dir}", FONT_SMALL, TEXT_SECONDARY)
        self.footer_label.pack(side="left", padx=32, pady=8)

    def _create_library(self):
        self.library_panel = ctk.CTkFrame(self.workspace, width=280, fg_color=SURFACE_WHITE,
            corner_radius=0, border_width=1, border_color=BORDER_COLOR)
        self.library_panel.pack_propagate(False)
        top = ctk.CTkFrame(self.library_panel, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(18, 10))
        self._label(top, "Files", FONT_HEADING).pack(side="left")
        self._button(top, "Close", self._toggle_library, width=60).pack(side="right")
        self.library_path = self._label(self.library_panel, "", FONT_SMALL, TEXT_SECONDARY,
                                        wraplength=240, justify="left")
        self.library_path.pack(fill="x", padx=16, pady=(0, 8))
        self.library_search = ctk.CTkEntry(self.library_panel, placeholder_text="Filter files", height=34,
            fg_color=BG_CANVAS, text_color=TEXT_PRIMARY, border_color=BORDER_COLOR)
        self.library_search.pack(fill="x", padx=16, pady=(0, 10))
        self.library_search.bind("<KeyRelease>", self._filter_library)
        nav = ctk.CTkFrame(self.library_panel, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=(0, 8))
        self._button(nav, "Up", self._library_up, width=55).pack(side="left", padx=3)
        self._button(nav, "Home", self._library_home, width=65).pack(side="left", padx=3)
        self._button(nav, "Refresh", self._refresh_library, width=80).pack(side="left", padx=3)
        self.library_list = ctk.CTkScrollableFrame(self.library_panel, fg_color="transparent")
        self.library_list.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._button(self.library_panel, "Open in Explorer", self._open_library_folder, width=240).pack(padx=16, pady=(0, 16))
        self._library_entries = []

    def _toggle_library(self):
        self._library_visible = not self._library_visible
        width = self.winfo_width()
        if self._library_visible:
            self.library_panel.pack(side="right", fill="y", before=self.main_frame)
            self.minsize(1240, 760)
            self.geometry(f"{max(1240, width + 280)}x{self.winfo_height()}")
            self._refresh_library()
        else:
            self.library_panel.pack_forget()
            self.minsize(960, 760)
            self.geometry(f"{max(960, width - 280)}x{self.winfo_height()}")

    def _library_home(self):
        self._navigate_library(self.download_dir)

    def _library_up(self):
        self._navigate_library(os.path.dirname(os.path.abspath(self.library_dir)))

    def _navigate_library(self, path):
        self.library_dir = path
        self.library_search.delete(0, "end")
        self._refresh_library()

    def _open_library_folder(self):
        self._open_path(self.library_dir)

    def _open_path(self, path):
        try:
            os.startfile(path)
        except OSError as error:
            messagebox.showerror("Open file", str(error))

    def _refresh_library(self):
        if not hasattr(self, "library_list"):
            return
        self._library_generation += 1
        generation = self._library_generation
        directory = self.library_dir
        self.library_path.configure(text=directory)

        def scan():
            try:
                with os.scandir(directory) as entries:
                    files = [(entry.name, entry.path, entry.is_dir(), entry.stat().st_size)
                             for entry in entries if not entry.name.startswith(".doom-")
                             and not entry.name.endswith((".part", ".ytdl"))]
                files.sort(key=lambda entry: (not entry[2], entry[0].casefold()))
                self._safe_after(0, self._library_loaded, generation, files, "")
            except OSError as error:
                self._safe_after(0, self._library_loaded, generation, [], str(error))
        threading.Thread(target=scan, daemon=True).start()

    def _library_loaded(self, generation, entries, error):
        if generation != self._library_generation:
            return
        self._library_entries = entries
        self._filter_library()
        if error:
            self._label(self.library_list, error, FONT_SMALL, TEXT_SECONDARY,
                        wraplength=220).pack(pady=12)

    def _filter_library(self, event=None):
        for widget in self.library_list.winfo_children():
            widget.destroy()
        query = self.library_search.get().casefold()
        entries = [entry for entry in self._library_entries if query in entry[0].casefold()]
        if not entries:
            self._label(self.library_list, "No files", color=TEXT_MUTED).pack(pady=30)
        for name, path, directory, size in entries[:200]:
            row = ctk.CTkFrame(self.library_list, fg_color=SURFACE_MUTED, corner_radius=8)
            row.pack(fill="x", pady=3)
            label = ("▸ " if directory else "") + name
            button = ctk.CTkButton(row, text=label, anchor="w", height=34, font=FONT_SMALL,
                fg_color="transparent", hover_color=BTN_SECONDARY_HOVER, text_color=TEXT_PRIMARY,
                command=lambda p=path, d=directory: self._navigate_library(p) if d else self._open_path(p))
            button.pack(fill="x", padx=5, pady=(3, 0))
            self._label(row, "Folder" if directory else f"{size / 1024 / 1024:.1f} MB", FONT_SMALL,
                        TEXT_MUTED).pack(anchor="w", padx=12, pady=(0, 5))
        if len(entries) > 200:
            self._label(self.library_list, "Filter to see more files", FONT_SMALL, TEXT_MUTED).pack(pady=8)

    # ---------------- Actions & Handlers ----------------

    def _on_format_changed(self, new_format: str):
        self.selected_format = new_format
        config.set("default_format", new_format)

    def _toggle_theme(self):
        current = config.get("theme", "Light")
        new_theme = "Dark" if current == "Light" else "Light"
        config.set("theme", new_theme)
        ctk.set_appearance_mode(new_theme)

    def _paste_clipboard(self):
        try:
            content = self.clipboard_get()
            if content:
                existing = self.url_textbox.get("1.0", "end-1c").strip()
                self.url_textbox.insert("end", ("\n" if existing else "") + content.strip())
                self._input_changed()
        except Exception:
            pass

    def _clear_input(self):
        self.url_textbox.delete("1.0", "end")
        self._set_input_mode("Single")

    def _browse_folder(self):
        chosen = filedialog.askdirectory(
            initialdir=self.download_dir,
            title="Select Download Folder"
        )
        if chosen:
            self.download_dir = chosen
            config.set("download_dir", chosen)
            self.footer_label.configure(text=f"Ready  ·  {chosen}")
            self.library_dir = chosen
            self._refresh_library()

    def _open_current_folder(self):
        if os.path.isdir(self.download_dir):
            try:
                os.startfile(self.download_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open directory: {e}")

    def _start_download_action(self):
        if self._adding:
            return
        raw_text = self.url_textbox.get("1.0", "end").strip()
        if not raw_text:
            return

        urls = extract_urls_from_text(raw_text)
        if not urls:
            messagebox.showwarning("Notice", "Enter an HTTP or HTTPS link.")
            return

        self.download_btn.configure(state="disabled", text="Adding...")
        if self.media_mode != "Audio" and any(is_spotify_url(url) for url in urls):
            self.download_btn.configure(state="normal", text="Download")
            messagebox.showinfo("Audio links", "Use Audio mode for Spotify links.")
            return
        self._adding = True
        self.url_textbox.configure(state="disabled")
        options = dict(detect_playlist=bool(self.cb_auto_playlist.get()) and self.media_mode != "File",
            skip_existing=bool(self.cb_skip_existing.get()), current_fmt=self.selected_format,
            target_dir=self.download_dir, artwork=bool(self.cb_artwork.get()) and self.media_mode == "Audio",
            metadata=bool(self.cb_metadata.get()))
        for key, value in (("skip_existing", options["skip_existing"]),
                           ("embed_thumbnail", bool(self.cb_artwork.get())),
                           ("add_metadata", options["metadata"]), ("expand_playlists", options["detect_playlist"])):
            config.set(key, value)
        threading.Thread(target=self._enqueue_worker, args=(urls, options), daemon=True).start()

    def _enqueue_worker(self, urls, options):
        try:
            self._process_input_urls(urls, options)
        except Exception as error:
            self._safe_after(0, self._enqueue_failed, str(error))

    def _enqueue_failed(self, error):
        self._adding = False
        self.url_textbox.configure(state="normal")
        self.download_btn.configure(state="normal", text="Download")
        messagebox.showerror("Could not add links", error)

    def _process_input_urls(self, urls: list, options: dict):
        detect_playlist = options["detect_playlist"]
        skip_existing = options["skip_existing"]
        current_fmt = options["current_fmt"]
        target_dir = options["target_dir"]
        total_enqueued = 0

        for url in urls:
            # Condition 1: User-created playlist or Spotify collection
            from urllib.parse import urlsplit
            host = (urlsplit(url).hostname or "").lower()
            known_single_host = host in ("youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be") or is_spotify_url(url)
            if detect_playlist and (is_playlist_url(url) or not known_single_host):
                try:
                    playlist_title, entries = fetch_playlist_entries(
                        url, self.downloader.ffmpeg_dir
                    )
                    if entries:
                        for entry in entries:
                            self.queue_manager.add_item(
                                url=entry["url"],
                                format_label=current_fmt,
                                download_dir=target_dir,
                                title=entry["title"],
                                artist=entry["uploader"],
                                duration=entry["duration"],
                                thumbnail_url=entry.get("thumbnail_url", ""),
                                embed_thumbnail=options["artwork"],
                                skip_existing=skip_existing,
                                crop_square=True,
                                add_metadata=options["metadata"],
                                playlist_name=playlist_title
                            )
                            total_enqueued += 1
                        continue
                except Exception as e:
                    print(f"[Doom Downloader] Error expanding playlist: {e}")

            # Condition 2: Single video / track link -> download ONLY that particular track
            clean_url = clean_video_url(url)
            is_spot = is_spotify_url(clean_url)
            self.queue_manager.add_item(
                url=clean_url,
                format_label=current_fmt,
                download_dir=target_dir,
                artist="Spotify" if is_spot else urlsplit(clean_url).hostname or "Web",
                embed_thumbnail=options["artwork"],
                skip_existing=skip_existing,
                crop_square=True,
                add_metadata=options["metadata"]
            )
            total_enqueued += 1

        self._safe_after(0, self._on_enqueued_finished, total_enqueued)

    def _on_enqueued_finished(self, count: int):
        self._adding = False
        self.url_textbox.configure(state="normal")
        self.download_btn.configure(state="normal", text="Download")
        self._clear_input()
        if count > 0:
            self.empty_label.pack_forget()

    def _on_filter_changed(self, selected_filter: str):
        self.current_filter = selected_filter
        self._apply_filter()

    def _apply_filter(self):
        with self.queue_manager.lock:
            for item in self.queue_manager.items:
                card = self.card_widgets.get(item.id)
                if not card:
                    continue

                visible = True
                if self.current_filter == "Downloading":
                    visible = (item.status in [QueueItemStatus.FETCHING, QueueItemStatus.DOWNLOADING, QueueItemStatus.CONVERTING])
                elif self.current_filter == "Completed":
                    visible = (item.status in [QueueItemStatus.COMPLETED, QueueItemStatus.EXISTS])
                elif self.current_filter == "Failed":
                    visible = item.status == QueueItemStatus.FAILED
                elif self.current_filter == "Queued":
                    visible = (item.status == QueueItemStatus.QUEUED)

                if visible:
                    card.pack(fill="x", pady=3)
                else:
                    card.pack_forget()

    def _clear_completed(self):
        removed_ids = self.queue_manager.clear_completed()
        for rid in removed_ids:
            card = self.card_widgets.pop(rid, None)
            if card:
                card.destroy()
        if not self.card_widgets:
            self.empty_label.pack(pady=70)

    def _safe_after(self, ms: int, func, *args):
        self._events.put((func, args))

    def _drain_events(self):
        for _ in range(200):
            try:
                func, args = self._events.get_nowait()
            except queue.Empty:
                break
            func(*args)
        self.after(80, self._drain_events)

    # ---------------- Queue Callbacks ----------------

    def _on_queue_item_added(self, item: DownloadItem):
        self._safe_after(0, self._ui_add_item_card, item)

    def _ui_add_item_card(self, item: DownloadItem):
        self.empty_label.pack_forget()
        card = QueueItemCard(
            self.scroll_frame,
            item=item,
            on_cancel=self.queue_manager.cancel_item,
            on_retry=self.queue_manager.retry_item,
            on_remove=self._handle_remove_item
        )
        self.card_widgets[item.id] = card
        self._apply_filter()

    def _handle_remove_item(self, item_id: str):
        if self.queue_manager.remove_item(item_id):
            card = self.card_widgets.pop(item_id, None)
            if card:
                card.destroy()
            if not self.card_widgets:
                self.empty_label.pack(pady=70)

    def _on_queue_item_updated(self, item: DownloadItem):
        self._safe_after(0, self._ui_update_item_card, item.id)

    def _ui_update_item_card(self, item_id: str):
        card = self.card_widgets.get(item_id)
        if card:
            card.update_data()
            self._apply_filter()
            item = self.queue_manager.get_item(item_id)
            if item and item.status in (QueueItemStatus.COMPLETED, QueueItemStatus.EXISTS) and item_id not in self._library_completed:
                self._library_completed.add(item_id)
                if self._library_visible:
                    self._refresh_library()

    def _on_stats_updated(self, stats: dict):
        self._safe_after(0, self._ui_update_stats, stats)

    def _ui_update_stats(self, stats: dict):
        total = stats.get("total", 0)
        active = stats.get("downloading", 0)
        speed = stats.get("total_speed_str", "0 KB/s")
        if active > 0:
            self.summary_label.configure(text=f"{total} items  •  {active} active  •  {speed}")
        else:
            self.summary_label.configure(text=f"{total} items  •  {speed}")

    def _on_closing(self):
        try:
            self.queue_manager.stop()
        except Exception:
            pass
        self.destroy()
