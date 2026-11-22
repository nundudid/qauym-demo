import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useOutletContext } from 'react-router-dom';
import type { Run, RunTrigger } from '../api/analytics';
import { api, errorMessage } from '../api/client';
import type { Me } from '../api/types';
import { btnPrimary, formatTime, Notice } from '../components/ui';

const cell = 'border-b border-slate-200 px-3 py-2 text-left align-top';

function statusText(run: Run): string {
  return run.is_active ? `${run.status} (active)` : run.status;
}

export default function AdminRunsPage() {
  const me = useOutletContext<Me>();
  const queryClient = useQueryClient();
  const isAdmin = me.role === 'admin';
  const runs = useQuery({
    queryKey: ['admin', 'runs'],
    queryFn: () => api<{ items: Run[] }>('/admin/analytics/runs'),
    enabled: isAdmin,
  });
  const trigger = useMutation({
    mutationFn: () => api<RunTrigger>('/admin/analytics/runs', { method: 'POST' }),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['admin', 'runs'] }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['communities'] }),
  });

  if (!isAdmin) {
    return (
      <>
        <h1 className="text-2xl font-semibold">Page not found</h1>
        <p className="mt-2">This page is only available to administrators.</p>
      </>
    );
  }
  const items = runs.data?.items ?? [];

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Analytics runs</h1>
        <button
          type="button"
          className={btnPrimary}
          onClick={() => trigger.mutate()}
          disabled={trigger.isPending}
        >
          {trigger.isPending ? 'Running…' : 'Run now'}
        </button>
      </div>
      <p className="mt-1 text-sm text-slate-700">
        One run builds a snapshot of the user graph, runs Leiden and Louvain, validates both and
        publishes the Leiden result. Louvain is kept for comparison and never shown to users.
      </p>
      <Notice kind="status">
        {trigger.data &&
          (trigger.data.started
            ? `Run finished: ${trigger.data.runs.map((r) => `${r.algorithm} ${r.status}`).join(', ')}.`
            : `No new run started. ${trigger.data.reason}`)}
      </Notice>
      <Notice kind="error">
        {(trigger.isError && errorMessage(trigger.error)) ||
          (runs.isError && errorMessage(runs.error))}
      </Notice>
      <p aria-live="polite" className="text-sm text-slate-600">
        {runs.isPending && 'Loading runs…'}
        {runs.data && items.length === 0 && 'No runs yet. Press “Run now” to start the first one.'}
      </p>

      {items.length > 0 && (
        <div className="mt-4 overflow-x-auto rounded-lg border border-slate-300 bg-white">
          <table className="w-full min-w-[46rem] border-collapse text-sm">
            <caption className="sr-only">Analytics runs, newest first</caption>
            <thead>
              <tr className="bg-slate-100">
                {[
                  'Started',
                  'Algorithm',
                  'Status',
                  'Duration',
                  'Modularity',
                  'Communities',
                  'Graph',
                  'Error',
                ].map((heading) => (
                  <th key={heading} scope="col" className={`${cell} font-semibold`}>
                    {heading}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((run) => (
                <tr key={run.id}>
                  <td className={cell}>{formatTime(run.started_at)}</td>
                  <th scope="row" className={`${cell} font-medium capitalize`}>
                    {run.algorithm}
                  </th>
                  <td className={`${cell} ${run.is_active ? 'font-semibold' : ''}`}>
                    {statusText(run)}
                  </td>
                  <td className={cell}>
                    {run.duration_ms === null ? '–' : `${run.duration_ms.toFixed(0)} ms`}
                  </td>
                  <td className={cell}>
                    {run.modularity === null ? '–' : run.modularity.toFixed(3)}
                  </td>
                  <td className={cell}>{run.n_communities ?? '–'}</td>
                  <td className={cell}>
                    {run.node_count === null
                      ? '–'
                      : `${run.node_count} users, ${run.edge_count} edges`}
                  </td>
                  <td className={`${cell} break-words`}>{run.error_message ?? '–'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
