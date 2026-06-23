import { type AdvisoryResult } from "@/lib/api";

/**
 * Lightweight agronomic rules matrix for on-device diagnostics fallback when offline.
 */
export function evaluateOfflineQuery(query: string): AdvisoryResult {
  const q = query.toLowerCase();
  let synthesis = "";

  if (q.includes("yellow leaves") || q.includes("yellowing") || q.includes("पीली पत्तियां")) {
    synthesis = "Potential Nitrogen (N) deficiency detected; check soil moisture trends. Consider applying nitrogen-rich organic compost or urea as recommended.";
  } else if (q.includes("wilt") || q.includes("wilting") || q.includes("dry") || q.includes("सूखा") || q.includes("मुरझा")) {
    synthesis = "Possible water stress or dehydration. Please verify irrigation schedules and check local soil moisture levels.";
  } else if (q.includes("spot") || q.includes("rust") || q.includes("lesions") || q.includes("blight") || q.includes("धब्बे") || q.includes("गेरूआ")) {
    synthesis = "Fungal or bacterial disease activity suspected. Inspect the underside of leaves and isolate affected crops to prevent spread.";
  } else if (q.includes("insect") || q.includes("bug") || q.includes("pest") || q.includes("aphid") || q.includes("कीड़े") || q.includes("कीट")) {
    synthesis = "Insect or pest infestation suspected. Monitor leaf surfaces closely and consider applying organic neem oil spray as a safe countermeasure.";
  } else {
    synthesis = "No active connection. Local diagnostic fallback active: Keep soil moist, maintain weed clearance, and check your latest NPK soil card values.";
  }

  return {
    advisory_id: "offline-" + Date.now(),
    farm_id: "offline-farm",
    synthesis,
    language: "en",
    explainability: {
      summary: "Rule-based on-device diagnostics matching localized symptoms matrix.",
      inputs: { query },
      primary_factor: "offline_fallback",
    },
    citations: [
      {
        source: "Local Rules",
        document_id: "local-rules-matrix",
        title: "On-Device Agronomy Diagnostic Rules",
        excerpt: "Lightweight diagnostic symptoms matrix for offline resilience.",
      },
    ],
    intelligence_snapshot_version: "on-device-rules-v1",
    source: "on-device-fallback",
  };
}
