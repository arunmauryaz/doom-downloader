export type QueueItemStatus =
  | "QUEUED"
  | "FETCHING"
  | "DOWNLOADING"
  | "CONVERTING"
  | "COMPLETED"
  | "EXISTS"
  | "FAILED"
  | "CANCELLED"
  | "PAUSED";

export interface QueueItem {
  id: string;
  url: string;
  title: string;
  artist: string;
  duration: number;
  format_label: string;
  status: QueueItemStatus;
  percent: number;
  speed: number;
  speed_str: string;
  eta_str: string;
  downloaded_bytes: number;
  total_bytes: number;
  status_message: string;
  error_message: string;
  filepath: string;
  thumbnail_url?: string;
}

export interface QueueStats {
  total: number;
  queued: number;
  downloading: number;
  completed: number;
  exists?: number;
  failed: number;
  cancelled: number;
  paused?: number;
  is_paused: boolean;
  total_speed?: number;
  total_speed_str?: string;
}

export interface EngineStatus {
  service: string;
  version: string;
  ffmpeg_available: boolean;
  download_dir: string;
  stats: QueueStats;
}

export interface FormatEntry {
  label: string;
  ext: string;
  quality?: string;
  codec?: string;
  height?: number;
}

export interface FormatsResponse {
  default_format: string;
  file_format: string;
  audio_formats: FormatEntry[];
  video_formats: FormatEntry[];
}

export interface CollectionEntry {
  id?: string;
  title: string;
  artist?: string;
  url?: string;
  stream_url?: string;
  thumbnail_url?: string;
  duration?: number;
}

export interface MediaResolutionInfo {
  url: string;
  title: string;
  artist: string;
  platform: string;
  media_type: string;
  suggested_mode: "Audio" | "Video" | "File";
  default_format: string;
  thumbnail_url?: string;
  stream_url?: string;
  is_collection?: boolean;
  collection_count?: number;
  entries?: CollectionEntry[];
}

export interface DownloadFileItem {
  name: string;
  path: string;
  size: number;
  modified: number;
  ext: string;
}

export interface AppConfig {
  download_dir: string;
  default_format: string;
  embed_thumbnail: boolean;
  crop_square: boolean;
  skip_existing: boolean;
  add_metadata: boolean;
  max_concurrent_downloads: number;
  browser_cookies?: "none" | "chrome" | "edge" | "brave" | "firefox";
  theme: "Light" | "Dark";
  color_accent?: string;
}

declare global {
  interface Window {
    electronAPI?: {
      isElectron?: boolean;
      selectFolder: (defaultPath?: string) => Promise<string | null>;
      revealFile: (filePath: string) => Promise<boolean>;
      openFile: (filePath: string) => Promise<boolean>;
    };
  }
}
