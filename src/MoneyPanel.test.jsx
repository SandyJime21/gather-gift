import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MoneyPanel, dollars } from './MoneyPanel.jsx';
import { api } from './lib/api.js';

vi.mock('./lib/api.js', () => ({ api: vi.fn() }));

describe('MoneyPanel', () => {
  afterEach(() => vi.clearAllMocks());

  it('formats cents as dollars', () => {
    expect(dollars(12500)).toBe('$125.00');
  });

  it('shows Stripe health, ad revenue and affiliate setup', async () => {
    api.mockResolvedValue({
      stripe: { key_configured: true, webhook_configured: true, mode: 'live', reachable: true, available: [{ currency: 'usd', amount_cents: 12500 }], pending: [], error: null },
      ads: { paid_cents: 5000, awaiting_payment_cents: 2000, pending_review: 1, campaigns: [] },
      affiliates: {
        note: 'Earnings are reported by each program.',
        other_configured_hosts: [],
        stores: [
          { host: 'amazon.com', label: 'Amazon', configured: true, dashboard_url: 'https://a.example' },
          { host: 'target.com', label: 'Target', configured: false, dashboard_url: 'https://t.example' },
        ],
      },
    });
    render(<MoneyPanel />);
    expect(await screen.findByText('Connected')).toBeInTheDocument();
    expect(screen.getByText('$125.00')).toBeInTheDocument();
    expect(screen.getByText('links tagged')).toBeInTheDocument();
    expect(screen.getByText('not set up')).toBeInTheDocument();
    await waitFor(() => expect(api).toHaveBeenCalledWith('/support/money'));
  });
});
