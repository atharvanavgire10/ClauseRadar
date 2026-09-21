export function validateEmail(value: string): string | null {
  const v = value.trim().toLowerCase();
  if (!v) return 'Email is required.';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return 'Enter a valid email address.';
  return null;
}

export function validatePassword(value: string): string | null {
  if (!value) return 'Password is required.';
  if (value.length < 8) return 'Password must be at least 8 characters.';
  return null;
}

export function validateContractTitle(value: string): string | null {
  if (!value.trim()) return 'Title is required.';
  if (value.trim().length > 300) return 'Title must be 300 characters or fewer.';
  return null;
}

export function validateDateOrder(start: string, end: string): string | null {
  if (start && end && end < start) return 'End date cannot be before start date.';
  return null;
}
