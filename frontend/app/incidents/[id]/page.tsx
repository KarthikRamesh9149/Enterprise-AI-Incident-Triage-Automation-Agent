"use client";

import { Bot, FileText, Play, ShieldCheck } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { Rows } from "@/components/Rows";
import { StatusPill } from "@/components/StatusPill";
import { api } from "@/lib/api";
import type { ApiRow, Incident } from "@/types/api";

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [timeline, setTimeline] = useState<ApiRow[]>([]);
  const [toolCalls, setToolCalls] = useState<ApiRow[]>([]);
  const [approvals, setApprovals] = useState<ApiRow[]>([]);
  const [reports, setReports] = useState<ApiRow[]>([]);
  const [result, setResult] = useState("");

  function refresh() {
    api.incident(params.id).then(setIncident);
    api.incidentTimeline(params.id).then(setTimeline);
    api.incidentToolCalls(params.id).then(setToolCalls);
    api.incidentApprovals(params.id).then(setApprovals);
    api.incidentReports(params.id).then(setReports);
  }

  useEffect(refresh, [params.id]);

  async function runAgent() {
    const data = await api.runAgent(params.id);
    setResult(JSON.stringify(data, null, 2));
    refresh();
  }

  async function generateReport() {
    const data = await api.generateReport(params.id);
    setResult(JSON.stringify(data, null, 2));
    refresh();
  }

  if (!incident) return <div className="text-sm text-slate-500">Loading incident...</div>;

  return (
    <div className="space-y-6">
      <section className="rounded-md border border-line bg-white p-5 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-ink">{incident.title}</h1>
            <p className="mt-2 max-w-4xl text-sm text-slate-600">{incident.description}</p>
            <div className="mt-3 flex gap-2"><StatusPill value={incident.severity} /><StatusPill value={incident.status} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={runAgent} className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white"><Play size={16} />Run agent</button>
            <button onClick={generateReport} className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm font-semibold"><FileText size={16} />Generate report</button>
          </div>
        </div>
      </section>
      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <DataPanel title="Incident Timeline"><Rows rows={timeline} fields={["event_type", "title", "actor_type", "created_at"]} /></DataPanel>
        <DataPanel title="Human Approval Queue"><Rows rows={approvals} fields={["action_type", "resource_type", "status", "created_at"]} /></DataPanel>
      </div>
      <div className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <DataPanel title="MCP Tool Calls"><Rows rows={toolCalls} fields={["tool_name", "status", "latency_ms", "created_at"]} /></DataPanel>
        <DataPanel title="Reports"><Rows rows={reports} fields={["title", "created_at", "file_path"]} /></DataPanel>
      </div>
      {result && (
        <DataPanel title="Latest Agent or Report Result" action={<ShieldCheck size={16} className="text-teal" />}>
          <pre className="max-h-96 overflow-auto rounded-md bg-slate-950 p-4 text-xs text-slate-100">{result}</pre>
        </DataPanel>
      )}
      <DataPanel title="Agent Trace">
        <div className="flex items-center gap-2 text-sm text-slate-600"><Bot size={16} />Open Agent Runs after a triage run to inspect stored trace steps.</div>
      </DataPanel>
    </div>
  );
}

