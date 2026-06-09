"use client";

import { useEffect, useState } from "react";
import { DataPanel } from "@/components/DataPanel";
import { Rows } from "@/components/Rows";
import { api } from "@/lib/api";
import type { ApiRow } from "@/types/api";

export default function RunbooksPage() {
  const [rows, setRows] = useState<ApiRow[]>([]);
  useEffect(() => { api.runbooks().then(setRows); }, []);
  return <DataPanel title="Runbooks and Prompt-Injection Checks"><Rows rows={rows} fields={["title", "severity", "trust_score", "injection_warning", "summary"]} /></DataPanel>;
}

