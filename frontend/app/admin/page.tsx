"use client";

import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { MetricGrid } from "@/components/MetricGrid";
import { Rows } from "@/components/Rows";
import { api } from "@/lib/api";
import type { ApiRow } from "@/types/api";

export default function AdminPage() {
  const [analytics, setAnalytics] = useState<Record<string, unknown>>({});
  const [audit, setAudit] = useState<ApiRow[]>([]);
  const [security, setSecurity] = useState<ApiRow[]>([]);
  useEffect(() => {
    api.adminAnalytics().then((data) => setAnalytics(data as Record<string, unknown>));
    api.adminAuditLogs().then(setAudit);
    api.adminSecurity().then(setSecurity);
  }, []);
  return (
    <div className="space-y-6">
      <MetricGrid metrics={analytics} />
      <DataPanel title="Audit Logs"><Rows rows={audit} fields={["action", "resource_type", "resource_id", "created_at"]} /></DataPanel>
      <DataPanel title="Security Dashboard"><Rows rows={security} fields={["event_type", "severity", "resource_type", "created_at"]} /></DataPanel>
    </div>
  );
}

