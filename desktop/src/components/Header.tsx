import React from "react";
import {
  Moon,
  Sun,
  Settings,
  Activity,
} from "lucide-react";
import { EngineStatus } from "@/lib/types";

interface HeaderProps {
  status: EngineStatus | null;
  connected: boolean;
  theme: "Light" | "Dark";
  onToggleTheme: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  status,
  theme,
  onToggleTheme,
  onOpenSettings,
}) => {
  return (
    <header className="h-14 border-b border-border/40 bg-card/40 backdrop-blur-xl px-5 flex items-center justify-between select-none transition-colors">
      {/* Brand Minimal Logo Only (No text, No clutter) */}
      <div className="flex items-center gap-3">
        <div className="relative group cursor-pointer">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-neutral-800 to-neutral-950 dark:from-neutral-100 dark:to-neutral-300 text-white dark:text-neutral-900 flex items-center justify-center font-bold text-sm tracking-tight shadow-sm border border-neutral-700/50 dark:border-neutral-200/50 transition-all duration-200 group-hover:scale-105 group-hover:shadow-md">
            <span>D</span>
          </div>
          {/* Subtle live activity glow dot */}
          {status?.stats?.downloading ? (
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 rounded-full ring-2 ring-background animate-pulse" />
          ) : null}
        </div>
      </div>

      {/* Center: Live transfer speed pill (only when active) */}
      <div className="flex items-center justify-center">
        {status?.stats?.total_speed_str && status.stats.total_speed_str !== "0 KB/s" ? (
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-secondary/80 border border-border/60 text-foreground text-xs font-mono font-medium shadow-sm animate-in fade-in">
            <Activity className="w-3.5 h-3.5 text-emerald-500 animate-pulse" />
            <span>{status.stats.total_speed_str}</span>
          </div>
        ) : null}
      </div>

      {/* Right Controls: Soft Curved Pills */}
      <div className="flex items-center gap-2">
        {/* Theme Toggle Button */}
        <button
          onClick={onToggleTheme}
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-secondary/60 hover:bg-secondary text-muted-foreground hover:text-foreground border border-border/50 hover:border-border transition-all duration-200 hover:shadow-sm"
          title={`Switch to ${theme === "Dark" ? "Light" : "Dark"} theme`}
          aria-label="Toggle Theme"
        >
          {theme === "Dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-secondary/60 hover:bg-secondary text-muted-foreground hover:text-foreground border border-border/50 hover:border-border transition-all duration-200 hover:shadow-sm"
          title="Settings"
          aria-label="Settings"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
};
