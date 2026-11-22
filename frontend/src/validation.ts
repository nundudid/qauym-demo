export const POST_MAX = 1000;
export const COMMENT_MAX = 500;
export const BIO_MAX = 280;
export const DISPLAY_NAME_MAX = 80;
export const TAG_MAX = 30;
export const MAX_INTERESTS = 10;

/** Each validator returns an error message, or '' when the value is fine. */
export function validateEmail(value: string): string {
  if (!value.trim()) return 'Enter your email address.';
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim()) ? '' : 'Enter a valid email address.';
}

export function validateUsername(value: string): string {
  if (!value.trim()) return 'Choose a username.';
  return /^[a-z0-9_]{3,30}$/.test(value.trim().toLowerCase())
    ? ''
    : 'Use 3–30 characters: letters a–z, digits and underscore.';
}

export function validateNewPassword(value: string): string {
  if (!value) return 'Choose a password.';
  if (value.length < 8) return 'Use at least 8 characters.';
  return value.length > 128 ? 'Use at most 128 characters.' : '';
}
