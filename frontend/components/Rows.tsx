import type { ApiRow } from "@/types/api";

export function Rows({ rows, fields }: { rows: ApiRow[]; fields?: string[] }) {
  if (!rows.length) {
    return <div className="rounded-md border border-dashed border-line p-6 text-center text-sm text-slate-500">No records yet.</div>;
  }
  const keys = fields ?? Object.keys(rows[0]).filter((key) => !key.endsWith("_json")).slice(0, 6);
  return (
    <div className="overflow-hidden rounded-md border border-line">
      <table className="w-full border-collapse text-left text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>{keys.map((key) => <th className="border-b border-line px-3 py-2" key={key}>{key.replaceAll("_", " ")}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr className="border-b border-line last:border-b-0" key={String(row.id ?? index)}>
              {keys.map((key) => <td className="max-w-80 truncate px-3 py-2 text-slate-700" key={key}>{format(row[key])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function format(value: unknown) {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

