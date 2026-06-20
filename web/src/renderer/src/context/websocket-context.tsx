/* eslint-disable react/jsx-no-constructed-context-values */
import React, {
  useContext, useCallback, useEffect, useState,
} from 'react';
import { wsService } from '@/services/websocket-service';
import { useLocalStorage } from '@/hooks/utils/use-local-storage';

const DEFAULT_WS_URL = 'ws://127.0.0.1:12396';
const DEFAULT_BASE_URL = 'http://127.0.0.1:12397';

export interface HistoryInfo {
  uid: string;
  latest_message: {
    role: 'human' | 'ai';
    timestamp: string;
    content: string;
  } | null;
  timestamp: string | null;
}

interface WebSocketContextProps {
  sendMessage: (message: object) => void;
  wsState: string;
  reconnect: () => void;
  wsUrl: string;
  setWsUrl: (url: string) => void;
  baseUrl: string;
  setBaseUrl: (url: string) => void;
}

export const WebSocketContext = React.createContext<WebSocketContextProps>({
  sendMessage: wsService.sendMessage.bind(wsService),
  wsState: 'CLOSED',
  reconnect: () => wsService.connect(DEFAULT_WS_URL),
  wsUrl: DEFAULT_WS_URL,
  setWsUrl: () => {},
  baseUrl: DEFAULT_BASE_URL,
  setBaseUrl: () => {},
});

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}

export const defaultWsUrl = DEFAULT_WS_URL;
export const defaultBaseUrl = DEFAULT_BASE_URL;

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [wsUrl, setWsUrl] = useLocalStorage('wsUrl', DEFAULT_WS_URL);
  const [baseUrl, setBaseUrl] = useLocalStorage('baseUrl', DEFAULT_BASE_URL);
  const [wsState, setWsState] = useState<string>(wsService.getCurrentState());

  const handleSetWsUrl = useCallback((url: string) => {
    setWsUrl((currentUrl) => (currentUrl === url ? currentUrl : url));
  }, [setWsUrl]);

  const handleSetBaseUrl = useCallback((url: string) => {
    setBaseUrl((currentUrl) => (currentUrl === url ? currentUrl : url));
  }, [setBaseUrl]);

  const sendMessage = useCallback((message: object) => {
    wsService.sendMessage(message);
  }, []);

  const reconnect = useCallback(() => {
    wsService.connect(wsUrl);
  }, [wsUrl]);

  useEffect(() => {
    wsService.connect(wsUrl);
  }, [wsUrl]);

  useEffect(() => {
    const stateSubscription = wsService.onStateChange(setWsState);
    return () => {
      stateSubscription.unsubscribe();
    };
  }, []);

  const value = {
    sendMessage,
    wsState,
    reconnect,
    wsUrl,
    setWsUrl: handleSetWsUrl,
    baseUrl,
    setBaseUrl: handleSetBaseUrl,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}
