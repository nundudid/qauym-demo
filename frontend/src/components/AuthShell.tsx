import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useMe } from '../hooks/useMe';

/** Frame for the sign-in and register pages; signed-in users go to the feed. */
export default function AuthShell({ title, children }: { title: string; children: ReactNode }) {
  const me = useMe();
  if (me.data) return <Navigate to="/" replace />;
  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10 text-slate-900">
      <main className="mx-auto max-w-sm rounded-lg border border-slate-300 bg-white p-6">
        <p className="text-lg font-semibold">Qauym</p>
        <h1 className="mt-1 text-2xl font-semibold">{title}</h1>
        {children}
      </main>
    </div>
  );
}
