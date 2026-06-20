import { useCallback, useEffect, useState } from 'react';
import { useProactiveSpeak } from '@/context/proactive-speak-context';
import { usePluginSettings } from '@/context/plugin-settings-context';

interface UseAgentSettingsProps {
  onSave?: (callback: () => void) => () => void
  onCancel?: (callback: () => void) => () => void
}

export function useAgentSettings({ onSave, onCancel }: UseAgentSettingsProps = {}) {
  const { settings: persistedSettings, updateSettings } = useProactiveSpeak();
  const { saveWebUISettings } = usePluginSettings();

  const [tempSettings, setTempSettings] = useState({
    allowProactiveSpeak: persistedSettings.allowProactiveSpeak,
    idleSecondsToSpeak: persistedSettings.idleSecondsToSpeak,
    allowButtonTrigger: persistedSettings.allowButtonTrigger,
  });

  const [originalSettings, setOriginalSettings] = useState({
    ...persistedSettings,
  });

  useEffect(() => {
    if (persistedSettings) {
      setOriginalSettings(persistedSettings);
      setTempSettings(persistedSettings);
    }
  }, [persistedSettings]);

  const handleAllowProactiveSpeakChange = useCallback((checked: boolean) => {
    setTempSettings((prev) => ({
      ...prev,
      allowProactiveSpeak: checked,
    }));
  }, []);

  const handleIdleSecondsChange = useCallback((value: number) => {
    setTempSettings((prev) => ({
      ...prev,
      idleSecondsToSpeak: value,
    }));
  }, []);

  const handleAllowButtonTriggerChange = useCallback((checked: boolean) => {
    setTempSettings((prev) => ({
      ...prev,
      allowButtonTrigger: checked,
    }));
  }, []);

  const handleSave = useCallback(() => {
    updateSettings(tempSettings);
    saveWebUISettings({
      agent: {
        allow_proactive_speak: tempSettings.allowProactiveSpeak,
        idle_seconds_to_speak: tempSettings.idleSecondsToSpeak,
        allow_button_trigger: tempSettings.allowButtonTrigger,
      },
    });
    setOriginalSettings(tempSettings);
  }, [saveWebUISettings, updateSettings, tempSettings]);

  const handleCancel = useCallback(() => {
    setTempSettings(originalSettings);
    updateSettings(originalSettings);
  }, [originalSettings, updateSettings]);

  useEffect(() => {
    if (!onSave || !onCancel) return;

    const cleanupSave = onSave(handleSave);
    const cleanupCancel = onCancel(handleCancel);

    return () => {
      cleanupSave?.();
      cleanupCancel?.();
    };
  }, [onSave, onCancel, handleSave, handleCancel]);

  return {
    settings: tempSettings,
    handleAllowProactiveSpeakChange,
    handleIdleSecondsChange,
    handleAllowButtonTriggerChange,
  };
}
