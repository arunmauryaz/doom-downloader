import {
  EngineStatus,
  FormatsResponse,
  MediaResolutionInfo,
  QueueItem,
  QueueStats,
  AppConfig,
  DownloadFileItem,
} from "./types";

export class EngineClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(port: number = 8080, token: string | null = null) {
    this.baseUrl = `http://127.0.0.1:${port}`;
    this.token = token;
  }

  public setBaseUrl(port: number, token: string | null = null) {
    this.baseUrl = `http://127.0.0.1:${port}`;
    this.token = token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      ...(options.headers as Record<string, string>),
    };

    if (options.body && typeof options.body === "string") {
      headers["Content-Type"] = "application/json";
    }

    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const res = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!res.ok) {
      let errMsg = `Request failed: ${res.status} ${res.statusText}`;
      try {
        const errJson = await res.json();
        if (errJson && errJson.error) errMsg = errJson.error;
      } catch {
        // ignore
      }
      throw new Error(errMsg);
    }

    return (await res.json()) as T;
  }

  public async getStatus(): Promise<EngineStatus> {
    return this.request<EngineStatus>("/api/status");
  }

  public async getFormats(): Promise<FormatsResponse> {
    return this.request<FormatsResponse>("/api/formats");
  }

  public async resolveUrl(url: string, expand: boolean = false): Promise<MediaResolutionInfo> {
    const encoded = encodeURIComponent(url);
    return this.request<MediaResolutionInfo>(`/api/info?url=${encoded}&expand=${expand}`);
  }

  public async getQueue(): Promise<{ queue: QueueItem[]; stats: QueueStats }> {
    return this.request<{ queue: QueueItem[]; stats: QueueStats }>("/api/queue");
  }

  public async enqueue(params: {
    url?: string;
    items?: Array<{ url: string; title?: string; thumbnail_url?: string; artist?: string; format?: string }>;
    format?: string;
    download_dir?: string;
    expand?: boolean;
    skip_existing?: boolean;
    embed_thumbnail?: boolean;
    add_metadata?: boolean;
  }): Promise<{ enqueued_count: number; item_ids: string[] }> {
    return this.request<{ enqueued_count: number; item_ids: string[] }>("/api/download", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  public async pauseQueue(): Promise<{ message: string; stats: QueueStats }> {
    return this.request<{ message: string; stats: QueueStats }>("/api/queue/pause", {
      method: "POST",
    });
  }

  public async resumeQueue(): Promise<{ message: string; stats: QueueStats }> {
    return this.request<{ message: string; stats: QueueStats }>("/api/queue/resume", {
      method: "POST",
    });
  }

  public async clearCompleted(): Promise<{ message: string; removed_ids: string[] }> {
    return this.request<{ message: string; removed_ids: string[] }>("/api/queue/clear", {
      method: "POST",
    });
  }

  public async pauseItem(itemId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/queue/${itemId}/pause`, {
      method: "POST",
    });
  }

  public async resumeItem(itemId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/queue/${itemId}/resume`, {
      method: "POST",
    });
  }

  public async cancelItem(itemId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/queue/${itemId}/cancel`, {
      method: "POST",
    });
  }

  public async retryItem(itemId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/queue/${itemId}/retry`, {
      method: "POST",
    });
  }

  public async removeItem(itemId: string): Promise<{ message: string; removed: boolean }> {
    return this.request<{ message: string; removed: boolean }>(`/api/queue/${itemId}/remove`, {
      method: "POST",
    });
  }

  public async getConfig(): Promise<AppConfig> {
    return this.request<AppConfig>("/api/config");
  }

  public async updateConfig(config: Partial<AppConfig>): Promise<{ message: string; config: AppConfig }> {
    return this.request<{ message: string; config: AppConfig }>("/api/config", {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  public async getFiles(): Promise<{ download_dir: string; files: DownloadFileItem[] }> {
    return this.request<{ download_dir: string; files: DownloadFileItem[] }>("/api/files");
  }

  public async openFile(path: string): Promise<{ message: string }> {
    return this.request<{ message: string }>("/api/files/open", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
  }

  public async revealFile(path: string): Promise<{ message: string }> {
    return this.request<{ message: string }>("/api/files/reveal", {
      method: "POST",
      body: JSON.stringify({ path }),
    });
  }

  public async browseDirectory(): Promise<string | null> {
    const res = await this.request<{ selected_dir: string | null }>("/api/browse-directory", {
      method: "POST",
    });
    return res.selected_dir;
  }

  public async removeFile(path: string, deleteDisk: boolean = false): Promise<{ message: string }> {
    return this.request<{ message: string }>("/api/files/remove", {
      method: "POST",
      body: JSON.stringify({ path, delete_file: deleteDisk }),
    });
  }
}

export const engineClient = new EngineClient(8080);
