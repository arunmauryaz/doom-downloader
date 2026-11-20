import { useState, useEffect, useRef, useCallback } from "react";
import { Header } from "@/components/Header";
import { LinkInput } from "@/components/LinkInput";
import { QueueList } from "@/components/QueueList";
import { SettingsDialog } from "@/components/SettingsDialog";
import { engineClient } from "@/lib/engineClient";
import {
  EngineStatus,
  FormatsResponse,
  QueueItem,
  QueueStats,
  AppConfig,
  MediaResolutionInfo,
} from "@/lib/types";

export function App() {
  const [theme, setTheme] = useState<"Light" | "Dark">("Dark");
  const [connected, setConnected] = useState(false);
  const [engineStatus, setEngineStatus] = useState<EngineStatus | null>(null);
  const [formats, setFormats] = useState<FormatsResponse | null>(null);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const pollTimerRef = useRef<number | null>(null);
  const isPollingRef = useRef(false);

  // Sync theme to document class
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "Dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [theme]);

  // Initial connection & loading formats/config
  const loadInitialData = useCallback(async () => {
    try {
      const [statusRes, formatsRes, configRes] = await Promise.all([
        engineClient.getStatus(),
        engineClient.getFormats(),
        engineClient.getConfig(),
      ]);
      setEngineStatus(statusRes);
      setFormats(formatsRes);
      setConfig(configRes);
      setConnected(true);

      if (configRes.theme) {
        setTheme(configRes.theme);
      }
    } catch {
      setConnected(false);
    }
  }, []);

  // Poll queue and stats
  const pollQueue = useCallback(async () => {
    if (isPollingRef.current) return;
    isPollingRef.current = true;
    try {
      const res = await engineClient.getQueue();
      setQueue(res.queue);
      setStats(res.stats);
      setConnected(true);
    } catch {
      setConnected(false);
    } finally {
      isPollingRef.current = false;
    }
  }, []);

  useEffect(() => {
    loadInitialData();
    pollQueue();

    const interval = window.setInterval(() => {
      pollQueue();
    }, 1000);
    pollTimerRef.current = interval;

    return () => {
      if (pollTimerRef.current) {
        window.clearInterval(pollTimerRef.current);
      }
    };
  }, [loadInitialData, pollQueue]);

  // Actions
  const handleToggleTheme = () => {
    const next = theme === "Dark" ? "Light" : "Dark";
    setTheme(next);
    engineClient.updateConfig({ theme: next }).catch(() => {});
  };

  const handleDownload = async (params: {
    url?: string;
    items?: Array<{ url: string; title?: string; thumbnail_url?: string; artist?: string; format?: string }>;
    format: string;
    download_dir?: string;
    skip_existing: boolean;
    expand: boolean;
    embed_thumbnail: boolean;
    add_metadata: boolean;
  }) => {
    await engineClient.enqueue(params);
    await pollQueue();
  };

  const handleInspectUrl = async (url: string): Promise<MediaResolutionInfo | null> => {
    try {
      return await engineClient.resolveUrl(url, true);
    } catch {
      return null;
    }
  };

  const handlePauseQueue = async () => {
    await engineClient.pauseQueue();
    await pollQueue();
  };

  const handleResumeQueue = async () => {
    await engineClient.resumeQueue();
    await pollQueue();
  };

  const handleClearCompleted = async () => {
    await engineClient.clearCompleted();
    await pollQueue();
  };

  const handlePauseItem = async (id: string) => {
    await engineClient.pauseItem(id);
    await pollQueue();
  };

  const handleResumeItem = async (id: string) => {
    await engineClient.resumeItem(id);
    await pollQueue();
  };

  const handleCancelItem = async (id: string) => {
    await engineClient.cancelItem(id);
    await pollQueue();
  };

  const handleRetryItem = async (id: string) => {
    await engineClient.retryItem(id);
    await pollQueue();
  };

  const handleRemoveItem = async (id: string) => {
    await engineClient.removeItem(id);
    await pollQueue();
  };

  const handleSaveConfig = async (updated: Partial<AppConfig>) => {
    const res = await engineClient.updateConfig(updated);
    setConfig(res.config);
    if (res.config.theme) setTheme(res.config.theme);
  };

  const handleOpenFile = async (path: string) => {
    if (window.electronAPI?.openFile) {
      const ok = await window.electronAPI.openFile(path);
      if (ok) return;
    }
    await engineClient.openFile(path);
  };

  const handleRevealFile = async (path: string) => {
    if (window.electronAPI?.revealFile) {
      const ok = await window.electronAPI.revealFile(path);
      if (ok) return;
    }
    await engineClient.revealFile(path);
  };

  const handleDeleteFile = async (item: QueueItem) => {
    if (item.filepath) {
      try {
        await engineClient.removeFile(item.filepath, true);
      } catch (e) {
        console.error("Failed to delete file from disk:", e);
      }
    }
    await engineClient.removeItem(item.id);
    await pollQueue();
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-background text-foreground select-none">
      {/* App Header */}
      <Header
        status={engineStatus}
        connected={connected}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* Main Work Area */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {/* Link Input Section */}
          <LinkInput
            formats={formats}
            defaultFormat={config?.default_format || "MP3 (320 kbps)"}
            defaultDownloadDir={config?.download_dir || ""}
            skipExisting={config?.skip_existing ?? true}
            expandCollections={false}
            embedThumbnail={config?.embed_thumbnail ?? true}
            addMetadata={config?.add_metadata ?? true}
            onDownload={handleDownload}
            onInspectUrl={handleInspectUrl}
          />

          {/* Queue List Section */}
          <QueueList
            items={queue}
            stats={stats}
            onPauseQueue={handlePauseQueue}
            onResumeQueue={handleResumeQueue}
            onClearCompleted={handleClearCompleted}
            onPauseItem={handlePauseItem}
            onResumeItem={handleResumeItem}
            onCancelItem={handleCancelItem}
            onRetryItem={handleRetryItem}
            onRemoveItem={handleRemoveItem}
            onOpenFile={handleOpenFile}
            onRevealFile={handleRevealFile}
            onDeleteFile={handleDeleteFile}
          />
        </div>
      </div>

      {/* Settings Modal */}
      <SettingsDialog
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        config={config}
        formats={formats}
        onSaveConfig={handleSaveConfig}
      />
    </div>
  );
}

export default App;
