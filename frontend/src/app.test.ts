import { describe, expect, it } from 'vitest';
import { buildQuery, getErrorMessage } from './api';
import { validateContractTitle, validateDateOrder, validateEmail, validatePassword } from './validation';

describe('buildQuery', () => {
  it('skips empty params and encodes values', () => {
    expect(buildQuery({ workspace: 'abc', search: '', status: undefined })).toBe('?workspace=abc');
    expect(buildQuery({})).toBe('');
    expect(buildQuery({ search: 'a&b' })).toBe('?search=a%26b');
  });
});

describe('getErrorMessage', () => {
  it('returns Error message or fallback', () => {
    expect(getErrorMessage(new Error('boom'))).toBe('boom');
    expect(getErrorMessage(null, 'fallback')).toBe('fallback');
  });
});

describe('validation', () => {
  it('validates email and password', () => {
    expect(validateEmail('not-an-email')).not.toBeNull();
    expect(validateEmail('user@example.com')).toBeNull();
    expect(validatePassword('short')).not.toBeNull();
    expect(validatePassword('long-enough-1')).toBeNull();
  });

  it('validates contract title and date order', () => {
    expect(validateContractTitle('  ')).not.toBeNull();
    expect(validateContractTitle('Vendor Agreement')).toBeNull();
    expect(validateDateOrder('2026-05-01', '2026-04-01')).not.toBeNull();
    expect(validateDateOrder('2026-04-01', '2026-05-01')).toBeNull();
  });
});
