"use client";

import React from "react";

import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { t } from "@/stores/localizationStore";

type Props = {
  children: React.ReactNode;
  fallbackTitle?: string;
};

type State = {
  hasError: boolean;
  errorMessage: string;
};

/**
 * React Error Boundary — catches render-time exceptions in any child component
 * and displays a farmer-friendly card instead of crashing the whole page.
 */
export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, errorMessage: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    const message =
      error instanceof Error ? error.message : "An unexpected error occurred";
    return { hasError: true, errorMessage: message };
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo) {
    // Log for debugging — in production this would go to an error tracker
    console.error("[ErrorBoundary] Caught render error:", error, info.componentStack);
  }

  override render() {
    if (this.state.hasError) {
      return (
        <Card className="dashboard-card">
          <CardHeader>
            <CardTitle>{this.props.fallbackTitle ?? t("errorBoundary.unavailable", "Unavailable")}</CardTitle>
            <CardDescription className="text-amber-700">
              {t("errorBoundary.desc", "This section is temporarily unavailable. It will reload when connectivity is restored.")}
            </CardDescription>
          </CardHeader>
        </Card>
      );
    }

    return this.props.children;
  }
}
