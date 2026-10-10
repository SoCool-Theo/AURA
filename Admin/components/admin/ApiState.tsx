"use client";
import { Button } from "@/components/ui/button";

export function ApiState({ loading, error, retry }: { loading: boolean; error?: string; retry: () => void }) {
  if (loading) return <p role="status" className="api-message">Loading from Aura…</p>;
  if (error) return <div role="alert" className="api-message"><p>{error}</p><Button variant="outline" onClick={retry}>Retry</Button></div>;
  return null;
}
export function Pagination({ total, limit, offset, onChange }: { total: number; limit: number; offset: number; onChange: (offset: number) => void }) {
  return <div className="page-controls api-pagination"><span>{total === 0 ? "0 results" : `${Math.min(offset + 1, total)}–${Math.min(offset + limit, total)} of ${total.toLocaleString()}`}</span><div className="inline-actions"><Button variant="outline" size="sm" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>Previous</Button><Button variant="outline" size="sm" disabled={offset + limit >= total || offset + limit > 10000} onClick={() => onChange(offset + limit)}>Next</Button></div>{offset + limit > 10000 && offset + limit < total && <small>Narrow the filters to browse more results.</small>}</div>;
}
export function Filter({ label, value, options, onChange }: { label: string; value: string; options: readonly string[]; onChange: (value: string) => void }) {
  return <label className="api-filter">{label}<select value={value} onChange={event => onChange(event.target.value)}><option value="">All</option>{options.map(option => <option key={option} value={option}>{humanize(option)}</option>)}</select></label>;
}
export function humanize(value: string) { return value.toLowerCase().replaceAll("_", " ").replace(/^./, char => char.toUpperCase()); }
export function utc(value: string | null) { return value ? new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "UTC" }).format(new Date(value)) + " UTC" : "Not recorded"; }
