"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { EmptyState } from "@/components/EmptyState";
import { StatusPill } from "@/components/StatusPill";
import { api } from "@/lib/api";
import type { Incident } from "@/types/api";

export function IncidentList({ compact = false }: { compact?: boolean }) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.incidents().then(setIncidents).catch((err) => setError(err.message));
  }, []);

  return (
    <DataPanel title="Active Incidents">
      {error && <div className="mb-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
      {!incidents.length ? <EmptyState title="No incidents loaded. Run the seed script to create demo data." /> : (
        <div className="space-y-2">
          {incidents.slice(0, compact ? 4 : 20).map((incident) => (
            <Link href={`/incidents/${incident.id}`} className="grid gap-3 rounded-md border border-line p-3 hover:border-teal md:grid-cols-[1fr_auto_auto]" key={incident.id}>
              <div>
                <div className="font-medium text-ink">{incident.title}</div>
                <div className="mt-1 line-clamp-1 text-sm text-slate-500">{incident.description}</div>
              </div>
              <StatusPill value={incident.severity} />
              <StatusPill value={incident.status} />
            </Link>
          ))}
        </div>
      )}
    </DataPanel>
  );
}

