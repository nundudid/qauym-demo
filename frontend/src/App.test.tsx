import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, expect, test, vi } from 'vitest';
import App from './App';
import { newKey } from './api/client';
import { validateEmail, validateNewPassword, validateUsername } from './validation';

afterEach(() => vi.unstubAllGlobals());

type Routes = Record<string, { status?: number; body?: unknown }>;

/** Stub fetch with canned responses keyed by "METHOD /path". */
function stubApi(routes: Routes) {
  const calls: { key: string; headers: Record<string, string>; body: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const key = `${init.method ?? 'GET'} ${url.replace('/api/v1', '').split('?')[0]}`;
      calls.push({
        key,
        headers: init.headers as Record<string, string>,
        body: init.body ? JSON.parse(init.body as string) : undefined,
      });
      const route = routes[key] ?? { status: 404, body: { detail: 'Not found.' } };
      return new Response(JSON.stringify(route.body ?? {}), { status: route.status ?? 200 });
    }),
  );
  return calls;
}

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const SIGNED_OUT = { status: 401, body: { detail: 'Sign in to continue.' } };
const ME = {
  id: 'u1',
  email: 'aru@example.com',
  username: 'aru',
  display_name: 'Aru',
  bio: '',
  interests: [],
  role: 'user',
};

test('validators accept good values and explain bad ones', () => {
  expect(validateEmail('aru@example.com')).toBe('');
  expect(validateEmail('aru@')).toMatch(/valid email/);
  expect(validateUsername('aru_01')).toBe('');
  expect(validateUsername('ab')).toMatch(/3–30/);
  expect(validateUsername('bad-name')).toMatch(/3–30/);
  expect(validateNewPassword('longenough')).toBe('');
  expect(validateNewPassword('short')).toMatch(/at least 8/);
});

test('newKey returns a version-4 UUID, different each time', () => {
  const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  expect(newKey()).toMatch(uuid);
  expect(newKey()).not.toBe(newKey());
});

test('signed-out visitors are redirected to the sign-in page', async () => {
  stubApi({ 'GET /me': SIGNED_OUT });
  renderAt('/');
  expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument();
});

test('sign-in shows inline validation and does not call the API', async () => {
  const calls = stubApi({ 'GET /me': SIGNED_OUT });
  renderAt('/login');
  fireEvent.change(await screen.findByLabelText('Email'), { target: { value: 'not-an-email' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

  expect(await screen.findByText(/Enter a valid email address/)).toBeInTheDocument();
  expect(screen.getByText(/Enter your password/)).toBeInTheDocument();
  expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true');
  expect(calls.some((c) => c.key === 'POST /auth/login')).toBe(false);
});

test('a rejected sign-in announces the generic server error', async () => {
  stubApi({
    'GET /me': SIGNED_OUT,
    'POST /auth/login': { status: 401, body: { detail: 'Invalid email or password.' } },
  });
  renderAt('/login');
  fireEvent.change(await screen.findByLabelText('Email'), {
    target: { value: 'aru@example.com' },
  });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'wrong-password' } });
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));

  const error = await screen.findByText(/Invalid email or password/);
  expect(error).toHaveAttribute('aria-live', 'polite');
});

test('register validates the username and password before submitting', async () => {
  const calls = stubApi({ 'GET /me': SIGNED_OUT });
  renderAt('/register');
  fireEvent.change(await screen.findByLabelText('Username'), { target: { value: 'No' } });
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'short' } });
  fireEvent.click(screen.getByRole('button', { name: 'Create account' }));

  expect(await screen.findByText(/Error: Use 3–30 characters/)).toBeInTheDocument();
  expect(screen.getByText(/Error: Use at least 8 characters/)).toBeInTheDocument();
  expect(calls.some((c) => c.key === 'POST /auth/register')).toBe(false);
});

test('the composer counts characters and posts with the required headers', async () => {
  const calls = stubApi({
    'GET /me': { body: ME },
    'GET /feed': { body: { items: [], next_cursor: null } },
    'POST /posts': { status: 201, body: {} },
  });
  renderAt('/');
  const box = await screen.findByLabelText('Write a post');
  const button = screen.getByRole('button', { name: 'Post' });
  expect(screen.getByText('0 / 1000 characters')).toBeInTheDocument();
  expect(button).toBeDisabled();

  fireEvent.change(box, { target: { value: 'x'.repeat(1001) } });
  expect(screen.getByText(/1001 \/ 1000 characters — too long/)).toBeInTheDocument();
  expect(button).toBeDisabled();

  fireEvent.change(box, { target: { value: 'Hello' } });
  expect(screen.getByText('5 / 1000 characters')).toBeInTheDocument();
  fireEvent.click(button);

  await vi.waitFor(() => expect(calls.some((c) => c.key === 'POST /posts')).toBe(true));
  const call = calls.find((c) => c.key === 'POST /posts')!;
  expect(call.body).toEqual({ body: 'Hello' });
  expect(call.headers['X-Qauym-Client']).toBe('web');
  expect(call.headers['Content-Type']).toBe('application/json');
  expect(call.headers['Idempotency-Key']).toMatch(/^[0-9a-f-]{36}$/);
});
