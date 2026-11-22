import { useId, type InputHTMLAttributes, type ReactNode } from 'react';

const base =
  'inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium ' +
  'disabled:cursor-not-allowed disabled:opacity-60';
export const btnPrimary = `${base} bg-blue-700 text-white hover:bg-blue-800`;
export const btnSecondary = `${base} border border-slate-400 bg-white text-slate-900 hover:bg-slate-100`;
export const btnDanger = `${base} border border-red-700 bg-white text-red-800 hover:bg-red-50`;
export const inputClass =
  'mt-1 block w-full rounded-md border border-slate-400 bg-white px-3 py-2 text-slate-900';
export const card = 'rounded-lg border border-slate-300 bg-white p-4';

type FieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  error?: string;
  hint?: string;
};

/** A labelled input whose validation error is announced politely. */
export function Field({ label, error, hint, ...input }: FieldProps) {
  const id = useId();
  const describedBy = [hint && `${id}-hint`, `${id}-error`].filter(Boolean).join(' ');
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-900">
        {label}
      </label>
      <input
        id={id}
        className={inputClass}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        {...input}
      />
      {hint && (
        <p id={`${id}-hint`} className="mt-1 text-sm text-slate-600">
          {hint}
        </p>
      )}
      <p id={`${id}-error`} aria-live="polite" className="mt-1 text-sm text-red-800">
        {error && <>Error: {error}</>}
      </p>
    </div>
  );
}

/** Always rendered, so screen readers announce a message when it appears. */
export function Notice({ kind, children }: { kind: 'error' | 'status'; children?: ReactNode }) {
  const tone = kind === 'error' ? 'text-red-800' : 'text-green-800';
  return (
    <p aria-live="polite" className={`text-sm ${tone} ${children ? 'mt-2' : ''}`}>
      {children && kind === 'error' ? <>Error: {children}</> : children}
    </p>
  );
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}
