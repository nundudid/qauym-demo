import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Navigate, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { ME_KEY, useMe } from '../hooks/useMe';
import { btnSecondary, Notice } from './ui';

function navClass({ isActive }: { isActive: boolean }) {
  return (
    'rounded-md px-2 py-1 text-sm font-medium ' +
    (isActive ? 'bg-slate-900 text-white underline' : 'text-slate-900 hover:bg-slate-200')
  );
}

/** Shell for signed-in pages: redirects to /login without a session. */
export default function Layout() {
  const me = useMe();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const logout = useMutation({
    mutationFn: () => api<void>('/auth/logout', { method: 'POST' }),
    onSettled: () => {
      queryClient.clear();
      queryClient.setQueryData(ME_KEY, null);
      navigate('/login');
    },
  });

  if (me.isPending) return <p className="p-6">Loading…</p>;
  if (me.isError) {
    return (
      <main className="p-6">
        <Notice kind="error">The server is not reachable. Reload the page to try again.</Notice>
      </main>
    );
  }
  if (!me.data) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-300 bg-white">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
          <span className="text-lg font-semibold">Qauym</span>
          <nav aria-label="Main" className="flex flex-1 flex-wrap items-center gap-1">
            <NavLink to="/" end className={navClass}>
              Feed
            </NavLink>
            <NavLink to="/people" className={navClass}>
              People
            </NavLink>
            <NavLink to="/communities" className={navClass}>
              Communities
            </NavLink>
            <NavLink to={`/u/${me.data.username}`} className={navClass}>
              My profile
            </NavLink>
            <NavLink to="/settings/profile" className={navClass}>
              Edit profile
            </NavLink>
            {me.data.role === 'admin' && (
              <NavLink to="/admin/runs" className={navClass}>
                Runs
              </NavLink>
            )}
          </nav>
          <button
            type="button"
            className={btnSecondary}
            onClick={() => logout.mutate()}
            disabled={logout.isPending}
          >
            Sign out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-4 py-6">
        <Outlet context={me.data} />
      </main>
    </div>
  );
}
