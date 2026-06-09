"use client";

import { Search } from "lucide-react";
import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { Rows } from "@/components/Rows";
import { api } from "@/lib/api";
import type { ApiRow, Tool } from "@/types/api";

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [incidents, setIncidents] = useState<ApiRow[]>([]);
  const [output, setOutput] = useState<ApiRow>({});
  useEffect(() => { api.tools().then(setTools); api.incidents().then((rows) => setIncidents(rows as unknown as ApiRow[])); }, []);
  const incidentId = String(incidents[0]?.id ?? "");
  async function searchLogs() {
    setOutput(await api.callTool("search-logs", { incident_id: incidentId, query: "timeout" }));
  }
  async function searchRunbooks() {
    setOutput(await api.callTool("search-runbooks", { incident_id: incidentId, query: "checkout" }));
  }
  return (
    <div className="space-y-6">
      <DataPanel title="Tool Registry">
        <Rows rows={tools as unknown as ApiRow[]} fields={["name", "permission_level", "risk_level", "requires_approval", "is_enabled"]} />
      </DataPanel>
      <DataPanel title="MCP Console" action={<Search size={16} />}>
        <div className="mb-4 flex gap-2">
          <button onClick={searchLogs} className="rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Search logs</button>
          <button onClick={searchRunbooks} className="rounded-md border border-line px-3 py-2 text-sm font-semibold">Search runbooks</button>
        </div>
        <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(output, null, 2)}</pre>
      </DataPanel>
    </div>
  );
}

