"use client";

import { CheckCircle2 } from "lucide-react";
import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { api } from "@/lib/api";
import type { ApiRow } from "@/types/api";

export default function ApprovalsPage() {
  const [rows, setRows] = useState<ApiRow[]>([]);
  const refresh = () => api.approvals().then(setRows);
  useEffect(() => {
    void refresh();
  }, []);
  async function approve(id: string) {
    await api.approve(id);
    refresh();
  }
  return (
    <DataPanel title="Human Approval Workflow">
      <div className="space-y-2">
        {rows.map((row) => (
          <div className="grid gap-3 rounded-md border border-line p-3 md:grid-cols-[1fr_auto]" key={String(row.id)}>
            <div>
              <div className="text-sm font-semibold">{String(row.action_type)} · {String(row.status)}</div>
              <div className="mt-1 text-sm text-slate-500">{String(row.request_reason)}</div>
            </div>
            <button onClick={() => approve(String(row.id))} className="inline-flex items-center gap-2 rounded-md bg-teal px-3 py-2 text-sm font-semibold text-white"><CheckCircle2 size={16} />Approve</button>
          </div>
        ))}
      </div>
    </DataPanel>
  );
}
