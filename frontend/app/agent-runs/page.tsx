"use client";

import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { Rows } from "@/components/Rows";
import { api, apiFetch } from "@/lib/api";
import type { ApiRow } from "@/types/api";

export default function AgentRunsPage() {
  const [runs, setRuns] = useState<ApiRow[]>([]);
  const [trace, setTrace] = useState<ApiRow[]>([]);
  useEffect(() => { api.agentRuns().then(setRuns); }, []);
  async function loadTrace(id: string) {
    setTrace(await apiFetch<ApiRow[]>(`/agent/runs/${id}/trace`));
  }
  return (
    <div className="space-y-6">
      <DataPanel title="Agent Runs">
        <div className="space-y-2">
          {runs.map((run) => (
            <button className="block w-full rounded-md border border-line p-3 text-left text-sm hover:border-teal" key={String(run.id)} onClick={() => loadTrace(String(run.id))}>
              {String(run.status)} · confidence {String(run.confidence_score)} · {String(run.final_summary)}
            </button>
          ))}
        </div>
      </DataPanel>
      <DataPanel title="Trace Viewer"><Rows rows={trace} fields={["node_name", "status", "output_summary", "latency_ms"]} /></DataPanel>
    </div>
  );
}

