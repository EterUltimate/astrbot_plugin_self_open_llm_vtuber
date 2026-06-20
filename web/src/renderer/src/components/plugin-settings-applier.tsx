import { useEffect, useRef } from 'react';
import i18n from '@/i18n';
import { useBgUrl } from '@/context/bgurl-context';
import { useLive2DConfig } from '@/context/live2d-config-context';
import { usePluginSettings } from '@/context/plugin-settings-context';
import { useProactiveSpeak } from '@/context/proactive-speak-context';
import { useSubtitle } from '@/context/subtitle-context';
import { useVAD } from '@/context/vad-context';
import { useWebSocket } from '@/context/websocket-context';
import {
  IMAGE_COMPRESSION_QUALITY_KEY,
  IMAGE_MAX_WIDTH_KEY,
} from '@/hooks/sidebar/setting/use-general-settings';

export function PluginSettingsApplier(): null {
  const { webuiSettings } = usePluginSettings();
  const {
    wsUrl, baseUrl, setBaseUrl, setWsUrl,
  } = useWebSocket();
  const bgUrlContext = useBgUrl();
  const { modelInfo, setModelInfo } = useLive2DConfig();
  const { setShowSubtitle } = useSubtitle();
  const {
    updateSettings: updateVADSettings,
    setAutoStopMic,
    setAutoStartMicOn,
    setAutoStartMicOnConvEnd,
    setSelectedMicId,
  } = useVAD();
  const { updateSettings: updateProactiveSpeakSettings } = useProactiveSpeak();
  const appliedSignatureRef = useRef('');

  useEffect(() => {
    if (!webuiSettings) {
      return;
    }

    const signature = JSON.stringify({
      settings: webuiSettings,
      modelUrl: modelInfo?.url || '',
    });
    if (signature === appliedSignatureRef.current) {
      return;
    }
    appliedSignatureRef.current = signature;

    const general = webuiSettings.general;
    if (general) {
      if (general.language) {
        void i18n.changeLanguage(general.language);
      }
      if (typeof general.ws_url === 'string' && general.ws_url && general.ws_url !== wsUrl) {
        setWsUrl(general.ws_url);
      }
      if (
        typeof general.base_url === 'string'
        && general.base_url
        && general.base_url !== baseUrl
      ) {
        setBaseUrl(general.base_url);
      }
      if (typeof general.show_subtitle === 'boolean') {
        setShowSubtitle(general.show_subtitle);
      }
      if (typeof general.use_camera_background === 'boolean') {
        bgUrlContext.setUseCameraBackground(general.use_camera_background);
      }
      if (typeof general.background_url === 'string' && general.background_url) {
        const nextBgUrl = general.background_url.startsWith('http')
          ? general.background_url
          : `${general.base_url || baseUrl}${general.background_url}`;
        bgUrlContext.setBackgroundUrl(nextBgUrl);
      }
      if (typeof general.image_compression_quality === 'number') {
        localStorage.setItem(
          IMAGE_COMPRESSION_QUALITY_KEY,
          String(general.image_compression_quality),
        );
      }
      if (typeof general.image_max_width === 'number') {
        localStorage.setItem(IMAGE_MAX_WIDTH_KEY, String(general.image_max_width));
      }
    }

    const live2d = webuiSettings.live2d;
    if (live2d && modelInfo) {
      setModelInfo({
        ...modelInfo,
        pointerInteractive:
          typeof live2d.pointer_interactive === 'boolean'
            ? live2d.pointer_interactive
            : modelInfo.pointerInteractive,
        scrollToResize:
          typeof live2d.scroll_to_resize === 'boolean'
            ? live2d.scroll_to_resize
            : modelInfo.scrollToResize,
      });
    }

    const asr = webuiSettings.asr;
    if (asr) {
      updateVADSettings({
        positiveSpeechThreshold: asr.positive_speech_threshold ?? 50,
        negativeSpeechThreshold: asr.negative_speech_threshold ?? 35,
        redemptionFrames: asr.redemption_frames ?? 35,
      });
      if (typeof asr.auto_stop_mic === 'boolean') {
        setAutoStopMic(asr.auto_stop_mic);
      }
      if (typeof asr.auto_start_mic_on === 'boolean') {
        setAutoStartMicOn(asr.auto_start_mic_on);
      }
      if (typeof asr.auto_start_mic_on_conv_end === 'boolean') {
        setAutoStartMicOnConvEnd(asr.auto_start_mic_on_conv_end);
      }
      if (typeof asr.selected_mic_id === 'string' && asr.selected_mic_id) {
        void setSelectedMicId(asr.selected_mic_id);
      }
    }

    const agent = webuiSettings.agent;
    if (agent) {
      updateProactiveSpeakSettings({
        allowProactiveSpeak: agent.allow_proactive_speak ?? false,
        idleSecondsToSpeak: agent.idle_seconds_to_speak ?? 5,
        allowButtonTrigger: agent.allow_button_trigger ?? false,
      });
    }
  }, [
    baseUrl,
    bgUrlContext,
    modelInfo,
    setAutoStartMicOn,
    setAutoStartMicOnConvEnd,
    setAutoStopMic,
    setBaseUrl,
    setModelInfo,
    setSelectedMicId,
    setShowSubtitle,
    setWsUrl,
    updateProactiveSpeakSettings,
    updateVADSettings,
    webuiSettings,
    wsUrl,
  ]);

  return null;
}

export default PluginSettingsApplier;
