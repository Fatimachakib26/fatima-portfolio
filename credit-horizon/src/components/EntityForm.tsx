"use client";
import { useState } from "react";
import { api } from "@/lib/client";
import { Modal, Field } from "./ui";

export type FieldDef = {
  key: string;
  label: string;
  type?: "text" | "textarea" | "select" | "number" | "date" | "range";
  options?: string[];
  required?: boolean;
  full?: boolean;
  hint?: string;
  min?: number;
  max?: number;
};

export default function EntityForm({
  title, fields, initial, endpoint, id, onClose, onSaved,
}: {
  title: string;
  fields: FieldDef[];
  initial: Record<string, any>;
  endpoint: string;
  id?: string | number;
  onClose: () => void;
  onSaved: (row: any) => void;
}) {
  const [f, setF] = useState<Record<string, any>>(initial);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setErr(null);
    try {
      const payload = Object.fromEntries(fields.map((fd) => [fd.key, fd.type === "number" || fd.type === "range" ? Number(f[fd.key] ?? 0) : f[fd.key] ?? ""]));
      const row = await api(id !== undefined ? `${endpoint}/${id}` : endpoint, { method: id !== undefined ? "PUT" : "POST", json: payload });
      onSaved(row);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal open onClose={onClose} title={title} wide>
      <form onSubmit={submit} className="grid gap-4 md:grid-cols-2">
        {fields.map((fd) => (
          <Field key={fd.key} label={`${fd.label}${fd.required ? " *" : ""}${fd.type === "range" ? ` : ${f[fd.key]}` : ""}`} hint={fd.hint} className={fd.full || fd.type === "textarea" ? "md:col-span-2" : ""}>
            {fd.type === "textarea" ? (
              <textarea className="input min-h-[70px]" required={fd.required} value={f[fd.key] ?? ""} onChange={(e) => setF({ ...f, [fd.key]: e.target.value })} />
            ) : fd.type === "select" ? (
              <select className="input" value={f[fd.key] ?? ""} onChange={(e) => setF({ ...f, [fd.key]: e.target.value })}>
                {fd.options!.map((o) => (
                  <option key={o} value={o}>
                    {o || "—"}
                  </option>
                ))}
              </select>
            ) : fd.type === "range" ? (
              <input type="range" min={fd.min ?? 0} max={fd.max ?? 100} className="w-full accent-brand-700" value={f[fd.key] ?? 0} onChange={(e) => setF({ ...f, [fd.key]: Number(e.target.value) })} />
            ) : (
              <input
                className="input"
                type={fd.type === "number" ? "number" : fd.type === "date" ? "date" : "text"}
                min={fd.min}
                max={fd.max}
                required={fd.required}
                value={f[fd.key] ?? ""}
                onChange={(e) => setF({ ...f, [fd.key]: e.target.value })}
              />
            )}
          </Field>
        ))}
        {err && <div className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700 md:col-span-2">{err}</div>}
        <div className="flex justify-end gap-2 md:col-span-2">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Annuler
          </button>
          <button className="btn-primary" disabled={saving}>
            {saving ? "Enregistrement…" : "Enregistrer"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
