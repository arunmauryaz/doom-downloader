import React, { useState, useEffect, useRef } from "react";
import {
  FolderOpen,
  File,
  FileAudio,
  FileVideo,
  ExternalLink,
  Search,
  X,
  RefreshCw,
  Play,
  Copy,
  Trash2,
  Check,
} from "lucide-react";
import { DownloadFileItem } from "@/lib/types";
import { formatBytes } from "@/lib/utils";

interface FilesPanelProps {
  files: DownloadFileItem[];
  downloadDir: string;
  isOpen: boolean;
  onClose: () => void;
  onOpenFile: (path: string) => void;
  onRevealFile: (path: string) => void;
  onRefresh: () => void;
  onRemoveFile?: (path: string) => Promise<void>;
}

interface ContextMenuState {
  file: DownloadFileItem;
  x: number;
  y: number;
}

export const FilesPanel: React.FC<FilesPanelProps> = ({
  files,
  downloadDir,
  isOpen,
  onClose,
  onOpenFile,
  onRevealFile,
  onRefresh,
  onRemoveFile,
}) => {
  const [filterQuery, setFilterQuery] = useState("");
  const [fileTypeFilter, setFileTypeFilter] = useState<"All" | "Audio" | "Video" | "Other">("All");
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);
  const [copiedPath, setCopiedPath] = useState(false);
  const contextMenuRef = useRef<HTMLDivElement | null>(null);

  // Close context menu when clicking outside or on window blur
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(e.target as Node)) {
        setContextMenu(null);
      }
    };
    if (contextMenu) {
      window.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      window.removeEventListener("mousedown", handleClickOutside);
    };
  }, [contextMenu]);

  if (!isOpen) return null;

  const audioExts = ["mp3", "m4a", "wav", "flac", "opus", "ogg"];
  const videoExts = ["mp4", "mkv", "webm", "mov", "avi"];

  const filtered = files.filter((f) => {
    // Type filter
    if (fileTypeFilter === "Audio" && !audioExts.includes(f.ext)) return false;
    if (fileTypeFilter === "Video" && !videoExts.includes(f.ext)) return false;
    if (fileTypeFilter === "Other" && (audioExts.includes(f.ext) || videoExts.includes(f.ext))) return false;

    // Search query filter
    if (!filterQuery.trim()) return true;
    const q = filterQuery.toLowerCase();
    return f.name.toLowerCase().includes(q) || f.ext.toLowerCase().includes(q);
  });

  const getFileIcon = (ext: string) => {
    if (audioExts.includes(ext)) {
      return (
        <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
          <FileAudio className="w-4 h-4" />
        </div>
      );
    }
    if (videoExts.includes(ext)) {
      return (
        <div className="w-8 h-8 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center shrink-0">
          <FileVideo className="w-4 h-4" />
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-xl bg-secondary text-muted-foreground flex items-center justify-center shrink-0">
        <File className="w-4 h-4" />
      </div>
    );
  };

  const formatRelativeTime = (timestamp: number) => {
    if (!timestamp) return "";
    const now = Date.now() / 1000;
    const diff = Math.max(0, now - timestamp);
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const handleContextMenu = (e: React.MouseEvent, file: DownloadFileItem) => {
    e.preventDefault();
    setContextMenu({
      file,
      x: Math.min(e.clientX, window.innerWidth - 200),
      y: Math.min(e.clientY, window.innerHeight - 180),
    });
  };

  const handleCopyPath = (path: string) => {
    navigator.clipboard.writeText(path);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 1500);
    setContextMenu(null);
  };

  const handleDeleteHistory = async (path: string) => {
    setContextMenu(null);
    if (onRemoveFile) {
      await onRemoveFile(path);
    }
  };

  return (
    <div className="w-92 border-l border-border/50 bg-card/75 backdrop-blur-2xl flex flex-col h-full select-none shadow-xl transition-all duration-300">
      {/* Explorer Header */}
      <div className="h-14 border-b border-border/40 px-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-secondary flex items-center justify-center">
            <FolderOpen className="w-4 h-4 text-foreground" />
          </div>
          <div>
            <span className="font-semibold text-xs tracking-tight">App Downloads</span>
            <span className="ml-1.5 text-[10px] text-muted-foreground font-mono">
              ({files.length})
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={onRefresh}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/70 transition-all"
            title="Refresh downloads history"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/70 transition-all"
            title="Close Explorer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Destination Folder & Open in Explorer Button */}
      <div className="px-4 py-2.5 bg-secondary/30 border-b border-border/30 flex items-center justify-between text-xs">
        <div className="truncate text-muted-foreground font-mono text-[11px] max-w-[210px]" title={downloadDir}>
          {downloadDir}
        </div>
        <button
          onClick={() => onRevealFile(downloadDir)}
          className="text-foreground hover:underline text-[11px] font-medium flex items-center gap-1 transition-all shrink-0 ml-2"
          title="Open downloads folder in Windows Explorer"
        >
          <ExternalLink className="w-3 h-3" />
          <span>Open Folder</span>
        </button>
      </div>

      {/* Search Input & Filter Pills */}
      <div className="p-3 border-b border-border/30">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-2.5 pointer-events-none" />
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            placeholder="Search app downloads..."
            className="w-full h-8 pl-8 pr-3 bg-secondary/40 border border-border/40 rounded-xl text-xs focus:outline-none focus:ring-2 focus:ring-primary/20 font-mono transition-all"
          />
        </div>

        <div className="flex items-center gap-1 mt-2">
          {(["All", "Audio", "Video", "Other"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setFileTypeFilter(t)}
              className={`px-2 py-0.5 rounded-lg text-[11px] font-medium transition-all ${
                fileTypeFilter === t
                  ? "bg-primary text-primary-foreground font-semibold"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/50"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Files List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {filtered.length === 0 ? (
          <div className="text-center py-16 text-xs text-muted-foreground">
            <FolderOpen className="w-8 h-8 stroke-1 text-muted-foreground/40 mx-auto mb-2" />
            <p>{files.length === 0 ? "No downloads yet from this app." : "No files matching query."}</p>
          </div>
        ) : (
          filtered.map((file) => (
            <div
              key={file.path}
              onContextMenu={(e) => handleContextMenu(e, file)}
              className="group p-2.5 rounded-2xl bg-secondary/30 hover:bg-secondary/70 border border-transparent hover:border-border/60 transition-all duration-200 flex items-center justify-between gap-3 text-xs"
            >
              <div
                className="flex items-center gap-2.5 min-w-0 flex-1 cursor-pointer"
                onClick={() => onOpenFile(file.path)}
                title={`Click to play: ${file.name}\n(Right click for options)`}
              >
                {getFileIcon(file.ext)}
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium text-foreground text-xs">{file.name}</div>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-mono mt-0.5">
                    <span>{formatBytes(file.size)}</span>
                    {file.modified > 0 && (
                      <>
                        <span>•</span>
                        <span>{formatRelativeTime(file.modified)}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Action buttons on hover */}
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => onOpenFile(file.path)}
                  className="w-7 h-7 rounded-xl flex items-center justify-center bg-card hover:bg-primary hover:text-primary-foreground text-foreground border border-border/50 shadow-sm transition-all"
                  title="Play file"
                >
                  <Play className="w-3 h-3 fill-current ml-0.5" />
                </button>
                <button
                  onClick={() => onRevealFile(file.path)}
                  className="w-7 h-7 rounded-xl flex items-center justify-center bg-card hover:bg-secondary text-muted-foreground hover:text-foreground border border-border/50 shadow-sm transition-all"
                  title="Show in Windows Explorer"
                >
                  <ExternalLink className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Custom Context Menu on Right Click */}
      {contextMenu && (
        <div
          ref={contextMenuRef}
          style={{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }}
          className="fixed z-50 min-w-[180px] bg-card/95 backdrop-blur-2xl border border-border/80 rounded-2xl shadow-2xl p-1.5 text-xs animate-in fade-in duration-100"
        >
          <div className="px-2.5 py-1.5 text-[10px] text-muted-foreground truncate border-b border-border/40 font-mono">
            {contextMenu.file.name}
          </div>

          <button
            onClick={() => {
              onOpenFile(contextMenu.file.path);
              setContextMenu(null);
            }}
            className="w-full px-2.5 py-1.5 rounded-xl flex items-center gap-2 hover:bg-secondary/80 text-foreground transition-all"
          >
            <Play className="w-3.5 h-3.5 fill-current text-emerald-500" />
            <span>Play / Open File</span>
          </button>

          <button
            onClick={() => {
              onRevealFile(contextMenu.file.path);
              setContextMenu(null);
            }}
            className="w-full px-2.5 py-1.5 rounded-xl flex items-center gap-2 hover:bg-secondary/80 text-foreground transition-all"
          >
            <FolderOpen className="w-3.5 h-3.5 text-primary" />
            <span>Show in Folder</span>
          </button>

          <button
            onClick={() => handleCopyPath(contextMenu.file.path)}
            className="w-full px-2.5 py-1.5 rounded-xl flex items-center gap-2 hover:bg-secondary/80 text-foreground transition-all"
          >
            {copiedPath ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5 text-muted-foreground" />}
            <span>{copiedPath ? "Path Copied!" : "Copy Full Path"}</span>
          </button>

          {onRemoveFile && (
            <div className="pt-1 mt-1 border-t border-border/40">
              <button
                onClick={() => handleDeleteHistory(contextMenu.file.path)}
                className="w-full px-2.5 py-1.5 rounded-xl flex items-center gap-2 hover:bg-destructive/10 text-destructive transition-all"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Remove from List</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
