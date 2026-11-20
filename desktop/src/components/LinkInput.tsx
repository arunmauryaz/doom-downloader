import React, { useState, useEffect, useRef } from "react";
import {
  Download,
  ChevronDown,
  SlidersHorizontal,
  Loader2,
  Video,
  Music,
  FolderOpen,
  RotateCcw,
  X,
  CheckSquare,
  Square,
  Layers,
} from "lucide-react";
import { FormatsResponse, MediaResolutionInfo } from "@/lib/types";
import { formatDuration } from "@/lib/utils";
import { engineClient } from "@/lib/engineClient";

interface LinkInputProps {
  formats: FormatsResponse | null;
  defaultFormat: string;
  defaultDownloadDir: string;
  skipExisting: boolean;
  expandCollections: boolean;
  embedThumbnail: boolean;
  addMetadata: boolean;
  onDownload: (params: {
    url?: string;
    items?: Array<{ url: string; title?: string; thumbnail_url?: string; artist?: string; format?: string }>;
    format: string;
    download_dir?: string;
    skip_existing: boolean;
    expand: boolean;
    embed_thumbnail: boolean;
    add_metadata: boolean;
  }) => Promise<void>;
  onInspectUrl: (url: string) => Promise<MediaResolutionInfo | null>;
  onFolderChange?: (dir: string) => void;
}

export const LinkInput: React.FC<LinkInputProps> = ({
  formats,
  defaultFormat,
  defaultDownloadDir,
  skipExisting: initialSkip,
  expandCollections: initialExpand,
  embedThumbnail: initialEmbed,
  addMetadata: initialMeta,
  onDownload,
  onInspectUrl,
  onFolderChange,
}) => {
  const [urlText, setUrlText] = useState("");
  const [mediaMode, setMediaMode] = useState<"video" | "audio">("video");
  const [selectedFormat, setSelectedFormat] = useState(defaultFormat);
  const [customDir, setCustomDir] = useState<string>("");
  const [skipExisting, setSkipExisting] = useState(initialSkip);
  const [expandCollections, setExpandCollections] = useState(initialExpand);
  const [embedThumbnail, setEmbedThumbnail] = useState(initialEmbed);
  const [addMetadata, setAddMetadata] = useState(initialMeta);
  const [showOptions, setShowOptions] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const [detectedMedia, setDetectedMedia] = useState<MediaResolutionInfo | null>(null);
  const [selectedEntryIds, setSelectedEntryIds] = useState<Set<string>>(new Set());
  const [isSubmitting, setIsSubmitting] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const inspectTimerRef = useRef<number | null>(null);

  const toggleEntrySelection = (entryId: string) => {
    setSelectedEntryIds((prev) => {
      const next = new Set(prev);
      if (next.has(entryId)) {
        next.delete(entryId);
      } else {
        next.add(entryId);
      }
      return next;
    });
  };

  const toggleSelectAllEntries = () => {
    if (!detectedMedia?.entries) return;
    const allIds = detectedMedia.entries.map((e, idx) => e.id || e.stream_url || e.url || String(idx));
    if (selectedEntryIds.size === allIds.length) {
      setSelectedEntryIds(new Set());
    } else {
      setSelectedEntryIds(new Set(allIds));
    }
  };

  // Available formats grouped cleanly
  const videoFormats = formats?.video_formats?.map((f) => f.label) || [
    "MP4 · 1080p",
    "MP4 · 720p",
    "MP4 · 480p",
    "MP4 · 360p",
    "MP4 · Best available",
  ];

  const audioFormats = formats?.audio_formats?.map((f) => f.label) || [
    "MP3 (320 kbps)",
    "MP3 (256 kbps)",
    "MP3 (128 kbps)",
    "FLAC (Lossless)",
    "WAV (Lossless PCM)",
    "M4A (AAC)",
    "OPUS",
  ];

  // Initialize format and mode based on defaultFormat
  useEffect(() => {
    if (defaultFormat) {
      const isAudio = audioFormats.includes(defaultFormat) || defaultFormat.toLowerCase().includes("mp3");
      if (isAudio) {
        setMediaMode("audio");
      } else {
        setMediaMode("video");
      }
      setSelectedFormat(defaultFormat);
    }
  }, [defaultFormat]);

  // Count URLs in input
  const urls = urlText
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0 && (l.startsWith("http://") || l.startsWith("https://")));
  const urlCount = urls.length;

  // Auto-resize textarea to fit content cleanly
  const adjustTextareaHeight = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineCount = urlText.split(/\r?\n/).length;
    if (lineCount <= 1 && !urlText.includes("\n")) {
      el.style.height = "44px";
    } else {
      el.style.height = `${Math.min(160, Math.max(54, el.scrollHeight))}px`;
    }
  };

  const handleTextChange = (text: string) => {
    setUrlText(text);

    if (inspectTimerRef.current) {
      window.clearTimeout(inspectTimerRef.current);
    }

    const firstUrl = text.trim().split(/\s+/)[0];
    if (firstUrl && (firstUrl.startsWith("http://") || firstUrl.startsWith("https://"))) {
      inspectTimerRef.current = window.setTimeout(async () => {
        setInspecting(true);
        try {
          const info = await onInspectUrl(firstUrl);
          if (info) {
            setDetectedMedia(info);
            if (info.is_collection && info.entries && info.entries.length > 0) {
              const allIds = new Set(info.entries.map((e, idx) => e.id || e.stream_url || e.url || String(idx)));
              setSelectedEntryIds(allIds);
            } else {
              setSelectedEntryIds(new Set());
            }
            // Auto adapt mode and format based on detected media
            if (info.suggested_mode === "Audio" || info.media_type === "spotify_audio") {
              setMediaMode("audio");
              setSelectedFormat(info.default_format || "MP3 (320 kbps)");
            } else if (info.suggested_mode === "Video" || info.media_type === "video") {
              setMediaMode("video");
              setSelectedFormat(info.default_format || "MP4 · 1080p");
            }
          }
        } catch {
          // ignore
        } finally {
          setInspecting(false);
        }
      }, 350);
    } else {
      setDetectedMedia(null);
      setSelectedEntryIds(new Set());
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [urlText]);

  // Handle Mode Toggle (Video vs Audio)
  const handleModeSwitch = (mode: "video" | "audio") => {
    setMediaMode(mode);
    if (mode === "video") {
      const best = videoFormats.find((f) => f.includes("1080p")) || videoFormats[0];
      setSelectedFormat(best);
    } else {
      const best = audioFormats.find((f) => f.includes("320")) || audioFormats[0];
      setSelectedFormat(best);
    }
  };

  // Keyboard navigation: Enter triggers download, Shift+Enter adds new line
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      triggerDownload();
    }
  };

  const handleBrowseFolder = async () => {
    try {
      let chosen: string | null = null;
      if (window.electronAPI?.selectFolder) {
        chosen = await window.electronAPI.selectFolder(customDir || defaultDownloadDir);
      } else {
        chosen = await engineClient.browseDirectory();
      }
      if (chosen) {
        setCustomDir(chosen);
        if (onFolderChange) onFolderChange(chosen);
      }
    } catch {
      // ignore
    }
  };

  const triggerDownload = async () => {
    const trimmed = urlText.trim();
    if (!trimmed || isSubmitting) return;

    setIsSubmitting(true);
    try {
      if (detectedMedia?.is_collection && detectedMedia.entries && detectedMedia.entries.length > 0) {
        const chosenItems = detectedMedia.entries
          .filter((e, idx) => selectedEntryIds.has(e.id || e.stream_url || e.url || String(idx)))
          .map((e) => ({
            url: e.stream_url || e.url || "",
            title: e.title,
            thumbnail_url: e.thumbnail_url,
            artist: e.artist || detectedMedia.artist,
            format: selectedFormat || (mediaMode === "video" ? videoFormats[0] : audioFormats[0]),
          }));

        if (chosenItems.length === 0) {
          setIsSubmitting(false);
          return;
        }

        await onDownload({
          items: chosenItems,
          format: selectedFormat || (mediaMode === "video" ? videoFormats[0] : audioFormats[0]),
          download_dir: customDir || undefined,
          skip_existing: skipExisting,
          expand: expandCollections,
          embed_thumbnail: embedThumbnail,
          add_metadata: addMetadata,
        });
      } else {
        await onDownload({
          url: trimmed,
          format: selectedFormat || (mediaMode === "video" ? videoFormats[0] : audioFormats[0]),
          download_dir: customDir || undefined,
          skip_existing: skipExisting,
          expand: expandCollections,
          embed_thumbnail: embedThumbnail,
          add_metadata: addMetadata,
        });
      }
      setUrlText("");
      setDetectedMedia(null);
      setSelectedEntryIds(new Set());
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeDownloadFolder = customDir || defaultDownloadDir;

  return (
    <div className="w-full max-w-3xl mx-auto py-5 px-5 select-none">
      <div className="bg-card/75 backdrop-blur-2xl border border-border/70 rounded-2xl shadow-sm hover:shadow-md transition-all duration-300 p-4">
        {/* Input Bar */}
        <div className="relative flex items-center">
          <textarea
            ref={textareaRef}
            value={urlText}
            onChange={(e) => handleTextChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Paste link here (Shift+Enter for multiple links)..."
            rows={1}
            className="w-full resize-none bg-background/90 border border-border/70 rounded-xl px-4 py-2.5 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all duration-200 pr-16 leading-relaxed"
          />

          {urlText && (
            <button
              onClick={() => {
                setUrlText("");
                setDetectedMedia(null);
              }}
              className="absolute right-2.5 px-2 py-1 text-[11px] rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
              title="Clear input"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Live Detected Media Preview Card with Real Thumbnail */}
        {inspecting && (
          <div className="mt-2.5 px-3 py-2 rounded-xl bg-secondary/30 border border-border/40 flex items-center gap-2 text-xs text-muted-foreground animate-in fade-in duration-150">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
            <span className="font-mono text-[11px]">Resolving media details...</span>
          </div>
        )}

        {detectedMedia && !inspecting && (
          detectedMedia.is_collection && detectedMedia.entries && detectedMedia.entries.length > 0 ? (
            /* Multi-Video / Collection Selection View */
            <div className="mt-3 p-3 rounded-2xl bg-secondary/35 border border-border/60 space-y-2.5 animate-in fade-in duration-200">
              {/* Collection Header */}
              <div className="flex items-center justify-between gap-2 border-b border-border/30 pb-2">
                <div className="flex items-center gap-2 min-w-0">
                  <Layers className="w-4 h-4 text-primary shrink-0" />
                  <span className="font-semibold text-xs text-foreground truncate">
                    {detectedMedia.title}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-card border border-border text-muted-foreground font-mono shrink-0">
                    {detectedMedia.platform}
                  </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    type="button"
                    onClick={toggleSelectAllEntries}
                    className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-secondary/60 hover:bg-secondary text-foreground border border-border/40 transition-colors flex items-center gap-1.5"
                  >
                    {selectedEntryIds.size === detectedMedia.entries.length ? (
                      <>
                        <CheckSquare className="w-3.5 h-3.5 text-primary" />
                        <span>Deselect All</span>
                      </>
                    ) : (
                      <>
                        <Square className="w-3.5 h-3.5 text-muted-foreground" />
                        <span>Select All</span>
                      </>
                    )}
                    <span className="font-mono text-[10px] text-muted-foreground ml-0.5">
                      ({selectedEntryIds.size}/{detectedMedia.entries.length})
                    </span>
                  </button>

                  <button
                    onClick={() => {
                      setDetectedMedia(null);
                      setSelectedEntryIds(new Set());
                    }}
                    className="w-6 h-6 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/70"
                    title="Dismiss preview"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Video Cards Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 max-h-56 overflow-y-auto pr-1">
                {detectedMedia.entries.map((entry, idx) => {
                  const entryId = entry.id || entry.stream_url || entry.url || String(idx);
                  const isSelected = selectedEntryIds.has(entryId);

                  return (
                    <div
                      key={entryId}
                      onClick={() => toggleEntrySelection(entryId)}
                      className={`group relative flex items-center gap-2.5 p-2 rounded-xl border cursor-pointer transition-all duration-150 select-none ${
                        isSelected
                          ? "bg-card/90 border-primary/50 shadow-sm"
                          : "bg-card/40 border-border/40 opacity-60 hover:opacity-100 hover:border-border"
                      }`}
                    >
                      {/* Checkbox indicator */}
                      <div className="shrink-0 text-primary">
                        {isSelected ? (
                          <CheckSquare className="w-4 h-4 fill-primary/10" />
                        ) : (
                          <Square className="w-4 h-4 text-muted-foreground/60" />
                        )}
                      </div>

                      {/* Thumbnail */}
                      {entry.thumbnail_url ? (
                        <img
                          src={entry.thumbnail_url}
                          alt={entry.title}
                          referrerPolicy="no-referrer"
                          className="w-12 h-9 object-cover rounded-lg border border-border/50 shrink-0 bg-secondary"
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = "none";
                          }}
                        />
                      ) : (
                        <div className="w-12 h-9 rounded-lg bg-secondary/80 border border-border/40 flex items-center justify-center shrink-0 text-muted-foreground">
                          <Video className="w-4 h-4" />
                        </div>
                      )}

                      {/* Meta */}
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-medium text-foreground truncate leading-tight" title={entry.title}>
                          {entry.title}
                        </p>
                        {entry.duration ? (
                          <p className="text-[10px] text-muted-foreground font-mono mt-0.5">
                            {formatDuration(entry.duration)}
                          </p>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ) : (
            /* Single Media Preview */
            <div className="mt-3 p-2.5 rounded-2xl bg-secondary/40 border border-border/60 flex items-center gap-3.5 animate-in fade-in duration-200">
              {detectedMedia.thumbnail_url ? (
                <img
                  src={detectedMedia.thumbnail_url}
                  alt={detectedMedia.title}
                  referrerPolicy="no-referrer"
                  className="w-24 h-16 sm:w-28 sm:h-18 object-cover rounded-xl border border-border/60 shrink-0 shadow-sm bg-secondary"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = "none";
                  }}
                />
              ) : (
                <div className="w-20 h-14 rounded-xl bg-secondary/80 border border-border/50 flex items-center justify-center shrink-0 text-muted-foreground">
                  {mediaMode === "video" ? <Video className="w-6 h-6" /> : <Music className="w-6 h-6" />}
                </div>
              )}

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-xs text-foreground truncate max-w-[280px] sm:max-w-[420px]">
                    {detectedMedia.title || "Detected media"}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-card border border-border text-muted-foreground font-mono shrink-0">
                    {detectedMedia.platform}
                  </span>
                </div>

                <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-1">
                  {detectedMedia.artist && <span className="truncate max-w-[200px]">{detectedMedia.artist}</span>}
                  {detectedMedia.is_collection && (
                    <span className="text-primary font-medium">
                      Collection ({detectedMedia.collection_count || "multiple"} tracks)
                    </span>
                  )}
                  <span className="text-muted-foreground/60">• Suggested: {detectedMedia.suggested_mode}</span>
                </div>
              </div>

              <button
                onClick={() => setDetectedMedia(null)}
                className="w-6 h-6 rounded-lg flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/70 shrink-0"
                title="Dismiss preview"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )
        )}

        {/* Controls Bar: Video/Audio Switch, Resolution Dropdown, Options, Download */}
        <div className="mt-3.5 pt-3 border-t border-border/40 flex flex-wrap items-center justify-between gap-3">
          {/* Left: Mode Toggle & Format Dropdown */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Video vs Audio Segmented Switch */}
            <div className="flex items-center gap-1 p-0.5 rounded-xl bg-secondary/50 border border-border/40">
              <button
                type="button"
                onClick={() => handleModeSwitch("video")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all duration-200 ${
                  mediaMode === "video"
                    ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Video className="w-3.5 h-3.5" />
                <span>Video</span>
              </button>
              <button
                type="button"
                onClick={() => handleModeSwitch("audio")}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all duration-200 ${
                  mediaMode === "audio"
                    ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <Music className="w-3.5 h-3.5" />
                <span>Audio</span>
              </button>
            </div>

            {/* Resolution / Format Select */}
            <div className="relative">
              <select
                value={selectedFormat}
                onChange={(e) => setSelectedFormat(e.target.value)}
                className="h-9 pl-3 pr-8 bg-background/90 border border-border/60 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 appearance-none cursor-pointer transition-all min-w-[150px]"
              >
                {mediaMode === "video" ? (
                  videoFormats.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))
                ) : (
                  audioFormats.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))
                )}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-muted-foreground absolute right-2.5 top-3 pointer-events-none" />
            </div>

            {/* Options Toggle Button */}
            <button
              type="button"
              onClick={() => setShowOptions(!showOptions)}
              className={`h-9 px-3 rounded-xl border text-xs flex items-center gap-1.5 transition-all duration-200 ${
                showOptions
                  ? "bg-secondary text-foreground border-border shadow-sm"
                  : "bg-transparent text-muted-foreground hover:text-foreground border-transparent hover:bg-secondary/50"
              }`}
              title="Toggle destination folder and download options"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Options</span>
            </button>
          </div>

          {/* Right: Download Action Button */}
          <button
            type="button"
            onClick={triggerDownload}
            disabled={
              !urlText.trim() ||
              isSubmitting ||
              (Boolean(detectedMedia?.is_collection && detectedMedia.entries?.length) && selectedEntryIds.size === 0)
            }
            className="h-9 px-5 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-all duration-200 shadow-sm hover:shadow active:scale-[0.98]"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Adding...</span>
              </>
            ) : Boolean(detectedMedia?.is_collection && detectedMedia.entries?.length) ? (
              <>
                <Download className="w-3.5 h-3.5" />
                <span>
                  {selectedEntryIds.size === 0
                    ? "Select videos"
                    : selectedEntryIds.size === detectedMedia!.entries!.length
                    ? `Download all (${selectedEntryIds.size})`
                    : `Download (${selectedEntryIds.size})`}
                </span>
              </>
            ) : (
              <>
                <Download className="w-3.5 h-3.5" />
                <span>{urlCount > 1 ? `Download (${urlCount})` : "Download"}</span>
              </>
            )}
          </button>
        </div>

        {/* Options Drawer: Destination Folder & Transfer Flags */}
        {showOptions && (
          <div className="mt-3.5 pt-3 border-t border-border/40 space-y-3 text-xs animate-in fade-in duration-150">
            {/* Destination Folder Picker Row */}
            <div className="p-2.5 rounded-xl bg-secondary/30 border border-border/40 flex flex-wrap items-center justify-between gap-2.5">
              <div className="flex items-center gap-2 min-w-0 flex-1">
                <FolderOpen className="w-4 h-4 text-primary shrink-0" />
                <span className="text-muted-foreground font-medium shrink-0">Save to:</span>
                <span
                  className="font-mono text-[11px] text-foreground truncate max-w-[280px] sm:max-w-[420px]"
                  title={activeDownloadFolder}
                >
                  {activeDownloadFolder || "Default downloads folder"}
                </span>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  type="button"
                  onClick={handleBrowseFolder}
                  className="h-7 px-2.5 rounded-lg bg-card hover:bg-secondary text-foreground border border-border/60 text-[11px] font-medium flex items-center gap-1.5 shadow-sm transition-all"
                  title="Choose destination folder"
                >
                  <FolderOpen className="w-3 h-3" />
                  <span>Browse...</span>
                </button>

                {customDir && (
                  <button
                    type="button"
                    onClick={() => {
                      setCustomDir("");
                      if (onFolderChange) onFolderChange("");
                    }}
                    className="h-7 px-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/60 text-[11px] transition-all"
                    title="Reset to default download folder"
                  >
                    <RotateCcw className="w-3 h-3" />
                  </button>
                )}
              </div>
            </div>

            {/* Checkbox Options */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={skipExisting}
                  onChange={(e) => setSkipExisting(e.target.checked)}
                  className="rounded-md border-border/60 text-primary focus:ring-primary/20 h-4 w-4"
                />
                <span className="text-muted-foreground">Skip existing</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={expandCollections}
                  onChange={(e) => setExpandCollections(e.target.checked)}
                  className="rounded-md border-border/60 text-primary focus:ring-primary/20 h-4 w-4"
                />
                <span className="text-muted-foreground">Expand playlists</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={embedThumbnail}
                  onChange={(e) => setEmbedThumbnail(e.target.checked)}
                  className="rounded-md border-border/60 text-primary focus:ring-primary/20 h-4 w-4"
                />
                <span className="text-muted-foreground">Embed artwork</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={addMetadata}
                  onChange={(e) => setAddMetadata(e.target.checked)}
                  className="rounded-md border-border/60 text-primary focus:ring-primary/20 h-4 w-4"
                />
                <span className="text-muted-foreground">Add ID3 tags</span>
              </label>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
