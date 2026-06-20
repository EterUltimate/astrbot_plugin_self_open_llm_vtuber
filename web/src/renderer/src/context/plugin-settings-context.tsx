import {
  createContext, useCallback, useContext, useMemo, useState,
} from 'react';
import { ModelInfo } from '@/context/live2d-config-context';
import { WebUISettingsPayload } from '@/services/websocket-service';
import { useWebSocket } from '@/context/websocket-context';

interface PluginSettingsContextState {
  webuiSettings: WebUISettingsPayload | null;
  setWebUISettings: (settings: WebUISettingsPayload) => void;
  live2dModelEntries: ModelInfo[];
  setLive2DModelEntries: (models: ModelInfo[]) => void;
  saveWebUISettings: (settings: WebUISettingsPayload) => void;
  refreshLive2DModels: () => void;
}

export const PluginSettingsContext = createContext<PluginSettingsContextState | null>(null);

export function PluginSettingsProvider({ children }: { children: React.ReactNode }) {
  const { sendMessage } = useWebSocket();
  const [webuiSettings, setWebUISettings] = useState<WebUISettingsPayload | null>(null);
  const [live2dModelEntries, setLive2DModelEntries] = useState<ModelInfo[]>([]);

  const saveWebUISettings = useCallback((settings: WebUISettingsPayload) => {
    sendMessage({
      type: 'update-webui-settings',
      settings,
    });
  }, [sendMessage]);

  const refreshLive2DModels = useCallback(() => {
    sendMessage({
      type: 'refresh-live2d-models',
    });
  }, [sendMessage]);

  const contextValue = useMemo(() => ({
    webuiSettings,
    setWebUISettings,
    live2dModelEntries,
    setLive2DModelEntries,
    saveWebUISettings,
    refreshLive2DModels,
  }), [
    live2dModelEntries,
    refreshLive2DModels,
    saveWebUISettings,
    webuiSettings,
  ]);

  return (
    <PluginSettingsContext.Provider value={contextValue}>
      {children}
    </PluginSettingsContext.Provider>
  );
}

export function usePluginSettings() {
  const context = useContext(PluginSettingsContext);
  if (!context) {
    throw new Error('usePluginSettings must be used within PluginSettingsProvider');
  }
  return context;
}
