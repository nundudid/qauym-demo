import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, errorMessage } from '../api/client';
import type { Me } from '../api/types';
import AuthShell from '../components/AuthShell';
import { btnPrimary, Field, Notice } from '../components/ui';
import { ME_KEY } from '../hooks/useMe';
import { validateEmail } from '../validation';

export default function LoginPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [touched, setTouched] = useState({ email: false, password: false });

  const errors = {
    email: validateEmail(email),
    password: password ? '' : 'Enter your password.',
  };
  const login = useMutation({
    mutationFn: () => api<Me>('/auth/login', { method: 'POST', body: { email, password } }),
    onSuccess: (me) => {
      queryClient.clear();
      queryClient.setQueryData(ME_KEY, me);
      navigate('/');
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setTouched({ email: true, password: true });
    if (!errors.email && !errors.password) login.mutate();
  }

  return (
    <AuthShell title="Sign in">
      <form onSubmit={submit} noValidate className="mt-4 space-y-3">
        <Field
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, email: true }))}
          error={touched.email ? errors.email : ''}
        />
        <Field
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onBlur={() => setTouched((t) => ({ ...t, password: true }))}
          error={touched.password ? errors.password : ''}
        />
        <button type="submit" className={`${btnPrimary} w-full`} disabled={login.isPending}>
          {login.isPending ? 'Signing in…' : 'Sign in'}
        </button>
        <Notice kind="error">{login.isError && errorMessage(login.error)}</Notice>
      </form>
      <p className="mt-4 text-sm">
        New to Qauym?{' '}
        <Link to="/register" className="font-medium underline">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
