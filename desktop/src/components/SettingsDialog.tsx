import React, { useState, useEffect } from "react";
import { X, Save, Check } from "lucide-react";
import { AppConfig, FormatsResponse } from "@/lib/types";

interface SettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  config: AppConfig | null;
  formats: FormatsResponse | null;
  onSaveConfig: (updated: Partial<AppConfig>) => Promise<void>;
}

export const SettingsDialog: React.FC<SettingsDialogProps> = ({
  isOpen,
  onClose,
  config,
  formats,
  onSaveConfig,
}) => {
  const [downloadDir, setDownloadDir] = useState("");
  const [defaultFormat, setDefaultFormat] = useState("");
  const [maxWorkers, setMaxWorkers] = useState(2);
  const [skipExisting, setSkipExisting] = useState(true);
  const [embedThumbnail, setEmbedThumbnail] = useState(true);
  const [cropSquare, setCropSquare] = useState(true);
  const [addMetadata, setAddMetadata] = useState(true);
  const [browserCookies, setBrowserCookies] = useState<string>("none");
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    if (config) {
      setDownloadDir(config.download_dir || "");
      setDefaultFormat(config.default_format || "");
      setMaxWorkers(config.max_concurrent_downloads || 2);
      setSkipExisting(config.skip_existing ?? true);
      setEmbedThumbnail(config.embed_thumbnail ?? true);
      setCropSquare(config.crop_square ?? true);
      setAddMetadata(config.add_metadata ?? true);
      setBrowserCookies(config.browser_cookies || "none");
    }
  }, [config, isOpen]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSaveConfig({
        download_dir: downloadDir,
        default_format: defaultFormat,
        max_concurrent_downloads: Number(maxWorkers),
        skip_existing: skipExisting,
        embed_thumbnail: embedThumbnail,
        crop_square: cropSquare,
        add_metadata: addMetadata,
        browser_cookies: browserCookies as any,
      });
      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        onClose();
      }, 500);
    } finally {
      setIsSaving(false);
    }
  };

  const audioFormats = formats?.audio_formats || [];
  const videoFormats = formats?.video_formats || [];

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-md flex items-center justify-center p-4 select-none animate-in fade-in duration-200">
      <div className="bg-card/90 backdrop-blur-2xl border border-border/60 w-full max-w-md rounded-3xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="h-14 border-b border-border/40 px-5 flex items-center justify-between">
          <span className="font-semibold text-sm tracking-tight">Preferences</span>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-xl flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/70 transition-all"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4 text-xs">
          {/* Download Directory */}
          <div className="space-y-1.5">
            <label className="font-medium text-foreground">Download Directory</label>
            <input
              type="text"
              value={downloadDir}
              onChange={(e) => setDownloadDir(e.target.value)}
              className="w-full h-9 px-3 bg-secondary/40 border border-border/50 rounded-xl text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
            />
          </div>

          {/* Default Format */}
          <div className="space-y-1.5">
            <label className="font-medium text-foreground">Default Output Profile</label>
            <select
              value={defaultFormat}
              onChange={(e) => setDefaultFormat(e.target.value)}
              className="w-full h-9 px-3 bg-secondary/40 border border-border/50 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer transition-all"
            >
              <optgroup label="Video">
                {videoFormats.map((f) => (
                  <option key={f.label} value={f.label}>
                    {f.label}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Audio">
                {audioFormats.map((f) => (
                  <option key={f.label} value={f.label}>
                    {f.label}
                  </option>
                ))}
              </optgroup>
              <option value="Original file">Original file</option>
            </select>
          </div>

          {/* Concurrent Downloads */}
          <div className="space-y-1.5">
            <label className="font-medium text-foreground">Max Concurrent Downloads</label>
            <input
              type="number"
              min={1}
              max={8}
              value={maxWorkers}
              onChange={(e) => setMaxWorkers(parseInt(e.target.value) || 2)}
              className="w-full h-9 px-3 bg-secondary/40 border border-border/50 rounded-xl text-xs font-mono focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
            />
          </div>

          {/* Browser Cookies (Unlocks 1080p/4K & Age-Gated Content) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="font-medium text-foreground">Browser Cookies (Bilibili 1080p+ / Age Gate)</label>
            </div>
            <select
              value={browserCookies}
              onChange={(e) => setBrowserCookies(e.target.value)}
              className="w-full h-9 px-3 bg-secondary/40 border border-border/50 rounded-xl text-xs font-medium focus:outline-none focus:ring-2 focus:ring-primary/20 cursor-pointer transition-all"
            >
              <option value="none">None (Default - Anonymous)</option>
              <option value="chrome">Google Chrome</option>
              <option value="edge">Microsoft Edge</option>
              <option value="brave">Brave Browser</option>
              <option value="firefox">Mozilla Firefox</option>
            </select>
            <p className="text-[10px] text-muted-foreground/80 leading-normal">
              Extracts local session cookies to unlock 1080p/4K on Bilibili and age-restricted media without storing passwords.
            </p>
          </div>

          {/* Checkboxes */}
          <div className="pt-2 border-t border-border/40 space-y-2.5">
            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={skipExisting}
                onChange={(e) => setSkipExisting(e.target.checked)}
                className="rounded-md border-border/60 text-primary focus:ring-primary/20 h-4 w-4"
              />
              <span className="text-muted-foreground">Skip re-downloading files already saved</span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={embedThumbnail}
                onChange={(e) => setEmbedThumbnail(e.target.checked)}
                className="rounded-md border-border/60 text-primary focus:ring-primary/20 h-4 w-4"
              />
              <span className="text-muted-foreground">Embed cover artwork into media</span>
            </label>

            <label className="flex items-center gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={addMetadata}
                onChange={(e) => setAddMetadata(e.target.checked)}
                className="rounded-md border-border/60 text-primary focus:ring-primary/20 h-4 w-4"
              />
              <span className="text-muted-foreground">Write artist, title, and album metadata</span>
            </label>
          </div>
        </div>

        {/* Footer */}
        <div className="h-14 border-t border-border/40 px-5 bg-secondary/20 flex items-center justify-end gap-2.5">
          <button
            onClick={onClose}
            className="h-9 px-4 rounded-xl text-xs font-medium border border-border/60 bg-secondary/40 hover:bg-secondary text-muted-foreground hover:text-foreground transition-all"
          >
            Cancel
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving}
            className="h-9 px-4 rounded-xl text-xs font-semibold bg-primary text-primary-foreground hover:bg-primary/90 flex items-center gap-2 transition-all shadow-sm active:scale-95"
          >
            {savedSuccess ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span>Saved</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>Save Settings</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
