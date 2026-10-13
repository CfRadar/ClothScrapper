import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Shield,
  XCircle,
} from "lucide-react";
import { getPreflight } from "../../lib/api";
import type { PreflightCheck, PreflightResponse } from "../../types";
import { Button } from "../../ui/Button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../ui/Dialog";

export interface SystemCheckDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SystemCheckDialog({ open, onOpenChange }: SystemCheckDialogProps) {
  const [preflight, setPreflight] = useState<PreflightResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchChecks = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPreflight();
      setPreflight(data);
    } catch (err: any) {
      setError(err.message || "Failed to query system preflight.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchChecks();
    }
  }, [open]);

  const renderStatusIcon = (status: "pass" | "warn" | "fail") => {
    switch (status) {
      case "pass":
        return <CheckCircle2 className="w-4 h-4 text-success shrink-0" />;
      case "warn":
        return <AlertTriangle className="w-4 h-4 text-warning shrink-0" />;
      case "fail":
        return <XCircle className="w-4 h-4 text-danger shrink-0" />;
    }
  };

  const groupChecks = (checks: PreflightCheck[]) => {
    const groups: Record<string, PreflightCheck[]> = {
      "Secrets & Authorization": [],
      "Network & SSRF Hardening": [],
      "Application Controls": [],
      "Audit & Scanning": [],
    };

    checks.forEach((c) => {
      if (["api_key", "free_models", "run_tokens"].includes(c.id)) {
        groups["Secrets & Authorization"].push(c);
      } else if (["cors_origin", "ssrf_allowlist", "social_adapters"].includes(c.id)) {
        groups["Network & SSRF Hardening"].push(c);
      } else if (["rate_limiting", "security_headers", "app_env", "file_permissions"].includes(c.id)) {
        groups["Application Controls"].push(c);
      } else {
        groups["Audit & Scanning"].push(c);
      }
    });

    return groups;
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent maxWidth="max-w-xl" className="max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-accent" />
            <DialogTitle>System status & security preflight</DialogTitle>
          </div>
          <DialogDescription>
            Live verification of application status, CORS boundaries, SSRF defenses,
            and scraper safeguards.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {loading && !preflight ? (
            <div className="flex items-center justify-center p-8 space-x-2 text-text-muted text-xs">
              <RefreshCw className="w-4 h-4 animate-spin text-accent" />
              <span>Checking system health and defenses...</span>
            </div>
          ) : error ? (
            <div className="p-3 text-xs bg-danger/10 border border-danger/30 rounded-input text-danger">
              {error}
            </div>
          ) : preflight ? (
            <div className="space-y-4">
              {Object.entries(groupChecks(preflight.checks)).map(
                ([groupName, checks]) => {
                  if (checks.length === 0) return null;
                  return (
                    <div key={groupName} className="space-y-1.5">
                      <h4 className="text-[11px] font-semibold uppercase tracking-wider text-text-muted">
                        {groupName}
                      </h4>
                      <div className="border border-border rounded-input divide-y divide-border bg-surface-2/30">
                        {checks.map((check) => (
                          <div
                            key={check.id}
                            className="flex items-start justify-between gap-3 p-2.5 text-xs"
                          >
                            <div className="space-y-0.5 min-w-0">
                              <div className="font-medium text-text">
                                {check.label}
                              </div>
                              <div className="text-[11px] text-text-muted break-words">
                                {check.detail}
                              </div>
                            </div>
                            <div className="shrink-0 pt-0.5">
                              {renderStatusIcon(check.status)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                }
              )}
            </div>
          ) : null}
        </div>

        <DialogFooter className="flex items-center justify-between sm:justify-between">
          <div className="flex items-center gap-1.5 text-[11px] text-text-muted">
            <Clock className="w-3.5 h-3.5" />
            <span>
              {preflight
                ? `Generated at ${new Date(
                    preflight.generated_at * 1000
                  ).toLocaleTimeString()}`
                : "No data"}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              loading={loading}
              onClick={fetchChecks}
              className="gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Re-check</span>
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onOpenChange(false)}
            >
              Close
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
