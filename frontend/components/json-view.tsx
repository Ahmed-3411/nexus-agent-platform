export function JsonView({ value, empty = "No data recorded." }: { value: unknown; empty?: string }) {
  if (value === null || value === undefined || (typeof value === "object" && Object.keys(value).length === 0)) {
    return <p className="text-sm text-slate-400">{empty}</p>;
  }
  return <pre className="max-h-80 overflow-auto rounded-2xl bg-[#151821] p-4 text-xs leading-6 text-slate-200 shadow-inner">{JSON.stringify(value, null, 2)}</pre>;
}
