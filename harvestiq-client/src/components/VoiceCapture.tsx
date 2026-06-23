"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useTranslation } from "@/stores/localizationStore";

type VoiceCaptureProps = {
  language?: string;
  onTranscript: (text: string) => void;
  label?: string;
};

export function VoiceCapture({ language, onTranscript, label }: VoiceCaptureProps) {
  const { t } = useTranslation();
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const defaultLabel = label ?? t("advisory.recordVoice", "Record voice");

  const startRecording = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        setLoading(true);
        try {
          const result = await api.transcribeVoice(blob, language);
          onTranscript(result.transcript);
        } catch (err) {
          setError(err instanceof Error ? err.message : t("voice.failed", "Transcription failed"));
        } finally {
          setLoading(false);
        }
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setRecording(true);
    } catch {
      setError(t("voice.microphoneRequired", "Microphone access is required for voice input."));
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant="outline"
        onClick={recording ? stopRecording : () => void startRecording()}
        disabled={loading}
      >
        {loading ? t("voice.transcribing", "Transcribing...") : recording ? t("voice.stopRecording", "Stop recording") : defaultLabel}
      </Button>
      {error && <p className="text-sm text-red-700">{error}</p>}
    </div>
  );
}
