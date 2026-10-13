import React, { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "../ui/Button";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error caught by ErrorBoundary:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] p-6 text-center space-y-3 bg-surface border border-border rounded-card m-4">
          <div className="p-2 rounded-card bg-danger/10 text-danger border border-danger/30">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-text">
              {this.props.fallbackTitle || "Something went wrong"}
            </h3>
            <p className="text-xs text-text-muted max-w-sm">
              An unexpected error occurred while rendering this component. You can reload
              the view safely.
            </p>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={this.handleReset}
            className="gap-1.5"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reload component</span>
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
