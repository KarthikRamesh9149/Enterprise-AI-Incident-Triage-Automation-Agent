"use client";

import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { IncidentList } from "@/components/IncidentList";
import { MetricGrid } from "@/components/MetricGrid";
import { Rows } from "@/components/Rows";
import { api } from "@/lib/api";
import type { ApiRow } from "@/types/api";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<Record<string, unknown>>({});
  const [observability, setObservability] = useState<ApiRow>({});
  const [security, setSecurity] = useState<ApiRow[]>([]);

  useEffect(() => {
    api.adminAnalytics().then((data) => setMetrics(data as Record<string, unknown>)).catch(() => setMetrics({ mode: "viewer", incidents: "see list" }));
    api.adminObservability().then(setObservability).catch(() => setObservability({ note: "Admin role required for observability metrics" }));
    api.adminSecurity().then(setSecurity).catch(() => setSecurity([]));
  }, []);

  return (
    <div className="space-y-6">
      <MetricGrid metrics={Object.keys(metrics).length ? metrics : { incidents: "-", tool_calls: "-", agent_runs: "-", approvals_pending: "-" }} />
      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <IncidentList compact />
        <DataPanel title="Observability Snapshot">
          <pre className="overflow-auto rounded-md bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(observability, null, 2)}</pre>
        </DataPanel>
      </div>
      <DataPanel title="Recent Security Events">
        <Rows rows={security} fields={["event_type", "severity", "resource_type", "created_at"]} />
      </DataPanel>
    </div>
  );
}

