import React, { useState } from "react";
import {
  Pause,
  Play,
  RotateCcw,
  X,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Layers,
  Search,
  FolderOpen,
  Music,
  Video,
} from "lucide-react";
import { QueueItem, QueueStats } from "@/lib/types";
import { formatBytes, formatDuration } from "@/lib/utils";

interface QueueListProps {
  items: QueueItem[];
  stats: QueueStats | null;
  onPauseQueue: () => void;
  onResumeQueue: () => void;
  onClearCompleted: () => void;
  onPauseItem: (id: string) => void;
  onResumeItem: (id: string) => void;
  onCancelItem: (id: string) => void;
  onRetryItem: (id: string) => void;
  onRemoveItem: (id: string) => void;
  onOpenFile: (path: string) => void;
  onRevealFile: (path: string) => void;
  onDeleteFile: (item: QueueItem) => void;
}

export const QueueList: React.FC<QueueListProps> = ({
  items,
  stats,
  onPauseQueue,
  onResumeQueue,
  onClearCompleted,
  onPauseItem,
  onResumeItem,
  onCancelItem,
  onRetryItem,
  onRemoveItem,
  onOpenFile,
  onRevealFile,
  onDeleteFile,
}) => {
  const [filter, setFilter] = useState<"All" | "Active" | "Completed" | "Failed">("All");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredItems = items.filter((item) => {
    if (filter === "Active") {
      const activeStates = ["DOWNLOADING", "FETCHING", "CONVERTING", "QUEUED"];
      if (!activeStates.includes(item.status)) return false;
    } else if (filter === "Completed") {
      if (!["COMPLETED", "EXISTS"].includes(item.status)) return false;
    } else if (filter === "Failed") {
      if (!["FAILED", "CANCELLED"].includes(item.status)) return false;
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = item.title?.toLowerCase().includes(q);
      const matchArtist = item.artist?.toLowerCase().includes(q);
      const matchUrl = item.url?.toLowerCase().includes(q);
      if (!matchTitle && !matchArtist && !matchUrl) return false;
    }

    return true;
  });

  return (
    <div className="flex-1 flex flex-col min-h-0 px-5 pb-5 select-none">
      {/* Queue Header & Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between pb-3.5 gap-2 border-b border-border/40">
        {/* Soft Pill Filters */}
        <div className="flex items-center gap-1.5 p-0.5 rounded-xl bg-secondary/40 border border-border/30">
          {(["All", "Active", "Completed", "Failed"] as const).map((tab) => {
            const count =
              tab === "All"
                ? items.length
                : tab === "Active"
                ? items.filter((i) => ["DOWNLOADING", "FETCHING", "CONVERTING", "QUEUED"].includes(i.status)).length
                : tab === "Completed"
                ? items.filter((i) => ["COMPLETED", "EXISTS"].includes(i.status)).length
                : items.filter((i) => ["FAILED", "CANCELLED"].includes(i.status)).length;

            return (
              <button
                key={tab}
                onClick={() => setFilter(tab)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all duration-200 ${
                  filter === tab
                    ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {tab}
                <span className="ml-1.5 text-[10px] opacity-70 font-mono">
                  {count}
                </span>
              </button>
            );
          })}
        </div>

        {/* Search Input */}
        {items.length > 4 && (
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search transfers..."
              className="h-8 pl-8 pr-3 bg-secondary/40 border border-border/50 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-primary/20 w-40 sm:w-48 font-mono transition-all"
            />
          </div>
        )}

        {/* Global Dispatch Controls */}
        <div className="flex items-center gap-2">
          {stats?.is_paused ? (
            <button
              onClick={onResumeQueue}
              className="h-8 px-3 rounded-xl border border-emerald-500/40 bg-emerald-500/10 hover:bg-emerald-500/20 text-xs font-medium flex items-center gap-1.5 text-emerald-500 transition-all duration-200"
              title="Resume background queue scheduler"
            >
              <Play className="w-3 h-3 fill-current" />
              <span>Resume</span>
            </button>
          ) : (
            <button
              onClick={onPauseQueue}
              className="h-8 px-3 rounded-xl border border-border/60 bg-secondary/50 hover:bg-secondary text-xs font-medium flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-all duration-200"
              title="Pause queue scheduler"
            >
              <Pause className="w-3 h-3" />
              <span>Pause</span>
            </button>
          )}

          <button
            onClick={onClearCompleted}
            className="h-8 px-3 rounded-xl border border-border/60 bg-secondary/50 hover:bg-secondary text-xs font-medium text-muted-foreground hover:text-foreground flex items-center gap-1.5 transition-all duration-200"
            title="Clear completed and skipped items"
          >
            <Trash2 className="w-3 h-3" />
            <span>Clear Done</span>
          </button>
        </div>
      </div>

      {/* Queue Cards List */}
      <div className="flex-1 overflow-y-auto pt-3.5 space-y-2.5 pr-1">
        {filteredItems.length === 0 ? (
          <div className="h-52 border border-dashed border-border/60 rounded-2xl flex flex-col items-center justify-center text-center p-6 text-muted-foreground bg-card/20">
            <Layers className="w-8 h-8 stroke-1 text-muted-foreground/40 mb-2.5" />
            <p className="text-xs font-medium">
              {items.length === 0
                ? "Queue is empty. Paste a link above to begin downloading."
                : "No downloads matching the current filter."}
            </p>
          </div>
        ) : (
          filteredItems.map((item) => (
            <div
              key={item.id}
              className="group bg-card/60 backdrop-blur-md border border-border/60 hover:border-border rounded-2xl p-3.5 transition-all duration-200 shadow-sm hover:shadow"
            >
              <div className="flex items-start justify-between gap-3">
                {/* Thumbnail if available */}
                {item.thumbnail_url ? (
                  <img
                    src={item.thumbnail_url}
                    alt={item.title}
                    referrerPolicy="no-referrer"
                    className="w-14 h-11 object-cover rounded-xl border border-border/50 shrink-0 bg-secondary shadow-sm"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = "none";
                    }}
                  />
                ) : (
                  <div className="w-11 h-11 rounded-xl bg-secondary/70 border border-border/40 flex items-center justify-center shrink-0 text-muted-foreground">
                    {item.format_label?.toLowerCase().includes("mp3") || item.format_label?.toLowerCase().includes("flac") ? (
                      <Music className="w-4 h-4" />
                    ) : (
                      <Video className="w-4 h-4" />
                    )}
                  </div>
                )}

                {/* Left Meta */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs text-foreground truncate max-w-[280px] sm:max-w-[400px]">
                      {item.title}
                    </span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-mono border border-border/50 bg-secondary/70 text-muted-foreground shrink-0">
                      {item.format_label}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-[11px] text-muted-foreground mt-1">
                    <span className="truncate max-w-[200px]">{item.artist || "Web"}</span>
                    {item.duration > 0 && (
                      <>
                        <span>•</span>
                        <span className="font-mono">{formatDuration(item.duration)}</span>
                      </>
                    )}
                    {item.total_bytes > 0 && (
                      <>
                        <span>•</span>
                        <span className="font-mono">
                          {formatBytes(item.downloaded_bytes)} / {formatBytes(item.total_bytes)}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Right Status & Actions */}
                <div className="flex items-center gap-2.5">
                  <div className="text-right">
                    <div className="flex items-center justify-end gap-1 text-[11px] font-mono">
                      {item.status === "COMPLETED" && (
                        <span className="flex items-center gap-1 text-emerald-500 font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Done
                        </span>
                      )}
                      {item.status === "EXISTS" && (
                        <span className="text-muted-foreground font-mono">Already saved</span>
                      )}
                      {item.status === "DOWNLOADING" && (
                        <span className="text-foreground font-semibold font-mono">
                          {item.percent.toFixed(1)}%
                        </span>
                      )}
                      {item.status === "CONVERTING" && (
                        <span className="text-blue-500 font-medium">Converting</span>
                      )}
                      {item.status === "FETCHING" && (
                        <span className="text-muted-foreground">Connecting</span>
                      )}
                      {item.status === "QUEUED" && (
                        <span className="text-muted-foreground">Queued</span>
                      )}
                      {item.status === "PAUSED" && (
                        <span className="text-amber-500 font-medium">Paused</span>
                      )}
                      {item.status === "FAILED" && (
                        <span className="flex items-center gap-1 text-destructive font-medium">
                          <AlertCircle className="w-3.5 h-3.5" /> Failed
                        </span>
                      )}
                      {item.status === "CANCELLED" && (
                        <span className="text-muted-foreground">Cancelled</span>
                      )}
                    </div>

                    {item.status === "DOWNLOADING" && (
                      <div className="text-[10px] text-muted-foreground font-mono mt-0.5">
                        {item.speed_str} • {item.eta_str}
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-1.5 border-l border-border/40 pl-2.5">
                    {/* Instant Play and Reveal for completed files */}
                    {item.filepath && (item.status === "COMPLETED" || item.status === "EXISTS") && (
                      <>
                        <button
                          onClick={() => onOpenFile(item.filepath)}
                          className="h-7 px-2.5 rounded-lg flex items-center gap-1 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 text-[11px] font-medium transition-all"
                          title="Play downloaded file in default player"
                        >
                          <Play className="w-3 h-3 fill-current" />
                          <span>Play</span>
                        </button>
                        <button
                          onClick={() => onRevealFile(item.filepath)}
                          className="w-7 h-7 rounded-lg flex items-center justify-center bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                          title="Show file in folder and select it"
                        >
                          <FolderOpen className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => onDeleteFile(item)}
                          className="w-7 h-7 rounded-lg flex items-center justify-center bg-secondary/50 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
                          title="Delete file from disk"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </>
                    )}

                    {item.status === "DOWNLOADING" || item.status === "QUEUED" ? (
                      <button
                        onClick={() => onPauseItem(item.id)}
                        className="w-7 h-7 rounded-full flex items-center justify-center bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                        title="Pause"
                      >
                        <Pause className="w-3 h-3" />
                      </button>
                    ) : item.status === "PAUSED" ? (
                      <button
                        onClick={() => onResumeItem(item.id)}
                        className="w-7 h-7 rounded-full flex items-center justify-center bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 transition-all"
                        title="Resume"
                      >
                        <Play className="w-3 h-3 fill-current" />
                      </button>
                    ) : null}

                    {["FAILED", "CANCELLED"].includes(item.status) && (
                      <button
                        onClick={() => onRetryItem(item.id)}
                        className="w-7 h-7 rounded-full flex items-center justify-center bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                        title="Retry"
                      >
                        <RotateCcw className="w-3 h-3" />
                      </button>
                    )}

                    {["DOWNLOADING", "FETCHING", "CONVERTING", "QUEUED"].includes(item.status) && (
                      <button
                        onClick={() => onCancelItem(item.id)}
                        className="w-7 h-7 rounded-full flex items-center justify-center bg-secondary/50 text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
                        title="Cancel"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}

                    {["COMPLETED", "EXISTS", "FAILED", "CANCELLED", "PAUSED"].includes(item.status) && (
                      <button
                        onClick={() => onRemoveItem(item.id)}
                        className="w-7 h-7 rounded-full flex items-center justify-center bg-secondary/50 text-muted-foreground hover:text-foreground hover:bg-secondary transition-all"
                        title="Remove from queue"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Smooth Rounded Progress Bar */}
              {(item.status === "DOWNLOADING" || item.status === "CONVERTING") && (
                <div className="mt-2.5 w-full bg-secondary/70 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-200 ${
                      item.status === "CONVERTING" ? "bg-blue-500 animate-pulse" : "bg-primary"
                    }`}
                    style={{ width: `${Math.min(100, Math.max(0, item.percent))}%` }}
                  />
                </div>
              )}

              {/* Status Message */}
              {(item.error_message || item.status_message) && (
                <div
                  className={`mt-1.5 text-[11px] truncate font-mono ${
                    item.error_message ? "text-destructive" : "text-muted-foreground/70"
                  }`}
                  title={item.error_message || item.status_message}
                >
                  {item.error_message || item.status_message}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
