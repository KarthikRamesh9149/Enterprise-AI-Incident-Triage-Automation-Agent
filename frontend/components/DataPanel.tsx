import type { ReactNode } from "react";

export function DataPanel({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-md border border-line bg-panel shadow-soft">
      <header className="flex items-center justify-between border-b border-line px-4 py-3">
        <h2 className="text-sm font-semibold text-ink">{title}</h2>
        {action}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

