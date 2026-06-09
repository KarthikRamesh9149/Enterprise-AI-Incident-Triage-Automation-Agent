"use client";

import { Play } from "lucide-react";
import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { api } from "@/lib/api";
import type { ApiRow } from "@/types/api";

export default function EvalsPage() {
  const [summary, setSummary] = useState<ApiRow>({});
  const refresh = () => api.evalsSummary().then(setSummary);
  useEffect(() => {
    void refresh();
  }, []);
  async function run() {
    await api.runEvals();
    refresh();
  }
  return (
    <DataPanel title="Evaluation Dashboard" action={<button onClick={run} className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white"><Play size={14} />Run evals</button>}>
      <pre className="rounded-md bg-slate-950 p-4 text-xs text-slate-100">{JSON.stringify(summary, null, 2)}</pre>
    </DataPanel>
  );
}
