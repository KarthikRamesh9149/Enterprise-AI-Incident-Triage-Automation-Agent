export function MetricGrid({ metrics }: { metrics: Record<string, unknown> }) {
  return (
    <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
      {Object.entries(metrics).map(([key, value]) => (
        <div className="rounded-md border border-line bg-white p-4 shadow-soft" key={key}>
          <div className="text-xs font-medium uppercase text-slate-500">{key.replaceAll("_", " ")}</div>
          <div className="mt-2 text-2xl font-semibold text-ink">{String(value)}</div>
        </div>
      ))}
    </div>
  );
}

