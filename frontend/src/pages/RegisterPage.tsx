import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError, errorMessage } from '../api/client';
import type { Me } from '../api/types';
import AuthShell from '../components/AuthShell';
import { btnPrimary, Field, Notice } from '../components/ui';
import { ME_KEY } from '../hooks/useMe';
import {
  DISPLAY_NAME_MAX,
  validateEmail,
  validateNewPassword,
  validateUsername,
} from '../validation';

type FieldName = 'email' | 'username' | 'display_name' | 'password';

export default function RegisterPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [values, setValues] = useState({ email: '', username: '', display_name: '', password: '' });
  const [touched, setTouched] = useState<Partial<Record<FieldName, boolean>>>({});

  const register = useMutation({
    mutationFn: () =>
      api<Me>('/auth/register', {
        method: 'POST',
        body: {
          email: values.email,
          username: values.username,
          password: values.password,
          ...(values.display_name.trim() && { display_name: values.display_name }),
        },
      }),
    onSuccess: (me) => {
      queryClient.clear();
      queryClient.setQueryData(ME_KEY, me);
      navigate('/');
    },
  });

  // Field errors reported by the server (422) are shown next to their fields.
  const serverErrors: Partial<Record<string, string>> = {};
  if (register.error instanceof ApiError) {
    for (const e of register.error.fieldErrors) serverErrors[e.field] = e.message;
  }
  const errors: Record<FieldName, string> = {
    email: validateEmail(values.email),
    username: validateUsername(values.username),
    display_name:
      values.display_name.trim().length > DISPLAY_NAME_MAX
        ? `Use at most ${DISPLAY_NAME_MAX} characters.`
        : '',
    password: validateNewPassword(values.password),
  };
  const valid = Object.values(errors).every((e) => !e);

  function bind(name: FieldName) {
    return {
      value: values[name],
      onChange: (e: { target: { value: string } }) =>
        setValues((v) => ({ ...v, [name]: e.target.value })),
      onBlur: () => setTouched((t) => ({ ...t, [name]: true })),
      error: touched[name] ? errors[name] || serverErrors[name] || '' : '',
    };
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    setTouched({ email: true, username: true, display_name: true, password: true });
    if (valid) register.mutate();
  }

  return (
    <AuthShell title="Create your account">
      <form onSubmit={submit} noValidate className="mt-4 space-y-3">
        <Field label="Email" type="email" autoComplete="email" {...bind('email')} />
        <Field
          label="Username"
          autoComplete="username"
          autoCapitalize="none"
          hint="3–30 characters: letters a–z, digits and underscore."
          {...bind('username')}
        />
        <Field label="Display name (optional)" autoComplete="name" {...bind('display_name')} />
        <Field
          label="Password"
          type="password"
          autoComplete="new-password"
          hint="At least 8 characters."
          {...bind('password')}
        />
        <button type="submit" className={`${btnPrimary} w-full`} disabled={register.isPending}>
          {register.isPending ? 'Creating account…' : 'Create account'}
        </button>
        <Notice kind="error">{register.isError && errorMessage(register.error)}</Notice>
      </form>
      <p className="mt-4 text-sm">
        Already have an account?{' '}
        <Link to="/login" className="font-medium underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
