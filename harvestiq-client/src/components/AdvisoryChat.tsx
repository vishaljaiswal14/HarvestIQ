"use client";

import { useState } from "react";

import { VoiceCapture } from "@/components/VoiceCapture";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAdvisory, type AdvisoryResult } from "@/hooks/useAdvisory";
import { useTranslation } from "@/stores/localizationStore";
import { api } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  text: string;
  meta?: AdvisoryResult;
};

type AdvisoryChatProps = {
  farmId: string;
  language: string;
};

export function AdvisoryChat({ farmId, language }: AdvisoryChatProps) {
  const advisory = useAdvisory();
  const { t } = useTranslation();
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);

  const sendQuery = async (text: string) => {
    console.log("[CHAT UI DEBUG] Send handler triggered. Query:", text);
    const trimmed = text.trim();
    if (!trimmed) return;

    // 1. Check if completely offline right at the UI level
    if (typeof window !== 'undefined' && !navigator.onLine) {
      console.log("[CHAT UI DEBUG] Local-first bypass active. Evading mutation engine locks.");
      
      // Push the user's message directly to the local UI state array immediately
      setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
      setQuery(""); // Clear the input field

      // Fetch the local fallback diagnostic response from our api layer
      try {
        const localResponse = await api.askAdvisory({ farm_id: farmId, query: trimmed, language });
        
        // Push the local edge response directly into the UI state array
        setMessages((prev) => [
          ...prev, 
          { 
            role: "assistant", 
            text: localResponse.synthesis,
            meta: localResponse
          }
        ]);
      } catch (err) {
        console.error("[CHAT UI DEBUG] Failed to resolve local api rule fallback:", err);
      }
      return; // Terminate early so the mutation engine never gets touched
    }

    // 2. Original online mutation path (untouched)
    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setQuery("");

    try {
      const result = await advisory.mutateAsync({
        farm_id: farmId,
        query: trimmed,
        language,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: result.synthesis, meta: result },
      ]);
    } catch (err) {
      const message = err instanceof Error ? err.message : t("advisory.failed", "Advisory request failed");
      setMessages((prev) => [...prev, { role: "assistant", text: message }]);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("advisory.pageTitle", "Farm Advisory")}</CardTitle>
        <CardDescription>
          {t("advisory.answersDisclaimer", "Answers are compiled from deterministic farm data and verified knowledge sources.")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="max-h-96 space-y-3 overflow-y-auto rounded-md border border-emerald-100 p-3">
          {messages.length === 0 && (
            <p className="text-sm text-emerald-700">
              {t("advisory.defaultPrompt", "Ask about crop stress, soil health, weather, or disease management.")}
            </p>
          )}
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`rounded-md p-3 text-sm ${
                message.role === "user" ? "bg-emerald-100" : "bg-white border border-emerald-50"
              }`}
            >
              {message.meta?.source === "on-device-fallback" && (
                <div className="mb-2 inline-flex items-center gap-1 rounded bg-amber-50 px-2 py-0.5 text-xs font-semibold text-amber-800 border border-amber-200">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
                  {t("advisory.offlineDiagnostic", "Offline Edge AI Diagnostic")}
                </div>
              )}
              <p className="whitespace-pre-wrap">{message.text}</p>
              {message.meta && (
                <details className="mt-2 text-xs text-emerald-700">
                  <summary className="cursor-pointer">{t("advisory.explainability", "Explainability & citations")}</summary>
                  <p className="mt-1">{message.meta.explainability.summary}</p>
                  {message.meta.citations.length > 0 && (
                    <ul className="mt-1 list-disc pl-4">
                      {message.meta.citations.map((citation, index) => (
                        <li key={`${citation.document_id}-${index}`}>
                          {citation.source}: {citation.title || citation.document_id}
                        </li>
                      ))}
                    </ul>
                  )}
                  <p className="mt-1">{t("advisory.snapshot", "Snapshot:")} {message.meta.intelligence_snapshot_version}</p>
                </details>
              )}
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={t("advisory.placeholder", "Ask about your crop, soil, or weather...")}
            onKeyDown={(event) => {
              if (event.key === "Enter") void sendQuery(query);
            }}
          />
          <Button onClick={() => void sendQuery(query)} disabled={advisory.isPending}>
            {t("advisory.send", "Send")}
          </Button>
        </div>

        <VoiceCapture
          language={language}
          label={t("advisory.recordVoice", "Record voice")}
          onTranscript={(transcript) => {
            setQuery(transcript);
            void sendQuery(transcript);
          }}
        />
      </CardContent>
    </Card>
  );
}
