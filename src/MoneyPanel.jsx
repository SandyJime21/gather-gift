import { useEffect, useState } from 'react';
import { Alert, Badge, Card, Form, Table } from 'react-bootstrap';
import { api } from './lib/api.js';

export const dollars = (cents, currency = 'usd') =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: (currency || 'usd').toUpperCase() }).format((cents || 0) / 100);

export function MoneyPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { api('/support/money').then(setData).catch((err) => setError(err.message)); }, []);
  if (error) return <Alert variant="danger">{error}</Alert>;
  if (!data) return <p role="status">Checking Stripe…</p>;
  const { stripe, ads, affiliates } = data;
  const healthy = stripe.reachable && stripe.webhook_configured;
  return <>
    <Card className="settings-card mb-4"><Card.Body>
      <h2>Stripe connection</h2>
      <p>
        <Badge bg={healthy ? 'success' : 'danger'}>{healthy ? 'Connected' : 'Needs attention'}</Badge>{' '}
        <Badge bg={stripe.mode === 'live' ? 'primary' : 'warning'} text={stripe.mode === 'live' ? undefined : 'dark'}>{stripe.mode} mode</Badge>
      </p>
      <ul className="mb-2">
        <li>Secret key: {stripe.key_configured ? 'set' : 'missing'}</li>
        <li>Webhook secret: {stripe.webhook_configured ? 'set' : 'missing'}</li>
        <li>Stripe reachable with this key: {stripe.reachable ? 'yes' : 'no'}</li>
      </ul>
      {stripe.error && <Alert variant="warning" className="mb-2">{stripe.error}</Alert>}
      {stripe.reachable && <p className="mb-0">
        Available balance: <strong>{stripe.available.map((row) => dollars(row.amount_cents, row.currency)).join(', ') || '$0.00'}</strong>
        {' · '}Pending: <strong>{stripe.pending.map((row) => dollars(row.amount_cents, row.currency)).join(', ') || '$0.00'}</strong>
      </p>}
    </Card.Body></Card>

    <Card className="settings-card mb-4"><Card.Body>
      <h2>Advertising revenue</h2>
      <p>Paid: <strong>{dollars(ads.paid_cents)}</strong> · Approved, awaiting payment: <strong>{dollars(ads.awaiting_payment_cents)}</strong> · Waiting for review: <strong>{ads.pending_review}</strong></p>
      {ads.campaigns.length ? <div className="table-responsive"><Table size="sm" aria-label="Ad payments"><thead><tr><th>Business</th><th>Ad</th><th>Status</th><th>Amount</th><th>Paid</th><th>Stripe payment</th></tr></thead><tbody>
        {ads.campaigns.map((row) => <tr key={row.id}><td>{row.business_name}<br /><small>{row.email}</small></td><td>{row.title}</td><td>{row.status}</td><td>{dollars(row.amount_cents)}</td><td>{row.paid ? 'Yes' : 'No'}</td><td><small>{row.payment_intent || '—'}</small></td></tr>)}
      </tbody></Table></div> : <p className="text-secondary mb-0">No ad campaigns yet.</p>}
    </Card.Body></Card>

    <Card className="settings-card mb-4"><Card.Body>
      <h2>Affiliate programs</h2>
      <p className="text-secondary">{affiliates.note}</p>
      <ul className="mb-2">
        {affiliates.stores.map((store) => <li key={store.host}>
          <strong>{store.label}</strong> ({store.host}): {store.configured ? <Badge bg="success">links tagged</Badge> : <Badge bg="secondary">not set up</Badge>}{' '}
          <a href={store.dashboard_url} target="_blank" rel="noreferrer noopener">View earnings dashboard</a>
        </li>)}
      </ul>
      {affiliates.other_configured_hosts.length > 0 && <p className="mb-2">Other stores with affiliate rules: {affiliates.other_configured_hosts.join(', ')}</p>}
      <p className="small text-secondary mb-0">Add a store by setting <code>AMAZON_ASSOCIATE_TAG</code> or a <code>STORE_AFFILIATE_RULES</code> entry (for example <code>{'{"walmart.com": {"query": {"your_param": "your_id"}}}'}</code>) in Render.</p>
    </Card.Body></Card>
  </>;
}

export function AccountsPanel() {
  const [query, setQuery] = useState('');
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const timer = setTimeout(() => {
      api('/support/users?q=' + encodeURIComponent(query)).then((result) => { setError(''); setData(result); }).catch((err) => setError(err.message));
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);
  return <Card className="settings-card mb-4"><Card.Body>
    <h2>User accounts</h2>
    <Form.Group controlId="account-search" className="mb-3"><Form.Label>Search by name or email</Form.Label><Form.Control value={query} onChange={(e) => setQuery(e.target.value)} /></Form.Group>
    {error && <Alert variant="danger">{error}</Alert>}
    {data && <><p className="text-secondary">{data.total} accounts total. Showing {data.users.length}.</p>
      <div className="table-responsive"><Table size="sm" aria-label="User accounts"><thead><tr><th>Name</th><th>Email</th><th>Type</th><th>Joined</th></tr></thead><tbody>
        {data.users.map((row) => <tr key={row.id}><td>{row.name}</td><td>{row.email || '—'}</td><td>{row.kind}</td><td>{new Date(row.created_at).toLocaleDateString()}</td></tr>)}
      </tbody></Table></div></>}
  </Card.Body></Card>;
}
