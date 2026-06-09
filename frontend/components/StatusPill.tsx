export function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const tone = normalized.includes("sev1") || normalized.includes("error") || normalized.includes("high")
    ? "border-red-200 bg-red-50 text-red-700"
    : normalized.includes("sev2") || normalized.includes("pending") || normalized.includes("medium")
      ? "border-amber-200 bg-amber-50 text-amber-800"
      : normalized.includes("resolved") || normalized.includes("success") || normalized.includes("healthy")
        ? "border-teal-200 bg-teal-50 text-teal-700"
        : "border-slate-200 bg-slate-50 text-slate-700";
  return <span className={`inline-flex rounded-md border px-2 py-1 text-xs font-medium ${tone}`}>{value}</span>;
}

