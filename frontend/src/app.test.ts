import { describe, expect, it, afterEach } from 'vitest';
import { buildQuery, getCsrfToken, getErrorMessage } from './api';
import { splitHighlight } from './highlight';
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

describe('getCsrfToken', () => {
  afterEach(() => {
    delete (globalThis as Record<string, unknown>).document;
  });

  it('returns null without a DOM', () => {
    expect(getCsrfToken()).toBeNull();
  });

  it('reads the csrftoken cookie', () => {
    (globalThis as Record<string, unknown>).document = {
      cookie: 'sessionid=abc; csrftoken=tok%2B123; other=x',
    };
    expect(getCsrfToken()).toBe('tok+123');
  });

  it('returns null when absent', () => {
    (globalThis as Record<string, unknown>).document = { cookie: 'sessionid=abc' };
    expect(getCsrfToken()).toBeNull();
  });
});

describe('splitHighlight', () => {
  const source = 'The Vendor shall maintain valid cyber insurance throughout the term.';
  it('splits around the matched action text', () => {
    const [before, hit, after] = splitHighlight(source, 'shall maintain valid cyber insurance');
    expect(before).toBe('The Vendor ');
    expect(hit).toBe('shall maintain valid cyber insurance');
    expect(after).toContain('throughout the term.');
  });

  it('returns full text when there is no usable match', () => {
    expect(splitHighlight(source, '')).toEqual([source, '', '']);
    expect(splitHighlight(source, 'xyz')).toEqual([source, '', '']);
  });
});
