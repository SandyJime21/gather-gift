import { useEffect, useMemo, useState } from 'react';
import { Card } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { api } from './lib/api.js';

export const HELP_INDEX = [
  { title: 'Reset my password', to: '/forgot-password', keywords: 'forgot password reset login sign in locked out email recover', answer: 'On the sign-in page choose "Forgot password" and enter your email. We will send a reset link.' },
  { title: 'My wish list', to: '/', keywords: 'wishes wishlist list add gift item my wishes', answer: 'Your wishes live on the home page. Add items there and choose who can see them.' },
  { title: 'Following & friends', to: '/following', keywords: 'following follow friends family requests browse people', answer: 'Use Following to see lists from people you follow and to answer follow requests.' },
  { title: 'Discover gift ideas', to: '/discover', keywords: 'discover ideas browse search gifts inspiration', answer: 'Discover shows gift ideas you can search and save to a list.' },
  { title: 'Gifting: reserved & purchased', to: '/gifting', keywords: 'gifting reserve reserved purchase purchased buy buying bought shopping cart', answer: 'Gifting is your private place for gifts you reserved or bought. Recipients cannot see it.' },
  { title: 'Gift games', to: '/games', keywords: 'game games secret santa draw names exchange play', answer: 'Open Games to set up a gift exchange or name draw for a family or group.' },
  { title: 'Settings', to: '/settings', keywords: 'settings account profile email name delete', answer: 'Settings holds your account details, privacy, display and notification options.' },
  { title: 'Notifications', to: '/notifications', keywords: 'notifications alerts bell email reminders', answer: 'See your updates on Notifications. Use the settings icon to manage alerts.' },
  { title: 'Help & support tickets', to: '/settings?tab=help', keywords: 'help support ticket bug problem contact feedback report issue', answer: 'Send a bug, feedback or help request under Help & support. Include your contact info and what went wrong, and you can follow replies there.' },
  { title: 'Birthdays & special days', to: '/', keywords: 'birthday birthdays special day occasion date anniversary holiday', answer: 'Add a birthday or special day on a profile so people can plan gifts ahead.' },
  { title: 'Invite family', to: '/settings', keywords: 'invite family household member invitation email join add child kid parent', answer: 'Invite people from your family or household settings. They get an email to join.' },
  { title: 'Themes & display', to: '/settings', keywords: 'theme themes dark christmas halloween color display text size appearance', answer: 'Pick a theme and display options in Settings.' },
  { title: 'Install the app', to: '/', keywords: 'install app phone home screen pwa mobile', answer: 'Use your browser menu, "Install" or "Add to Home Screen", to install the app.' },
  { title: 'Advertise with us', to: '/advertise', keywords: 'advertise ads advertising sponsor business', answer: 'Businesses can submit ads on the Advertise page.' },
];

export function searchHelp(query, index = HELP_INDEX) {
  const words = query.toLowerCase().split(/[^a-z0-9]+/).filter((word) => word.length > 1);
  if (!words.length) return [];
  return index
    .map((entry) => {
      const title = entry.title.toLowerCase();
      const keywords = entry.keywords.split(' ');
      const score = words.reduce((total, word) => total
        + (title.includes(word) ? 3 : 0)
        + (keywords.some((key) => key === word) ? 2 : keywords.some((key) => key.startsWith(word)) ? 1 : 0), 0);
      return { entry, score };
    })
    .filter((row) => row.score > 0)
    .sort((a, b) => b.score - a.score)
    .map((row) => row.entry);
}

export function HelpChatLogs() {
  const [chats, setChats] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    api('/support/help-chats').then((data) => setChats(data)).catch((err) => setError(err.message));
  }, []);
  return <Card className="settings-card mt-4"><Card.Body>
    <h2>Help assistant chats (last {chats?.days || 30} days)</h2>
    {error && <p className="text-danger">{error}</p>}
    {chats && !chats.chats.length && <p className="text-secondary mb-0">No assistant chats yet.</p>}
    {chats?.chats.map((chat) => <details className="ticket-row" key={chat.user_id}>
      <summary><strong>{chat.user_name}</strong> ({chat.user_email}) · {chat.messages.length} messages</summary>
      {chat.messages.map((m, i) => <p className="mb-1" key={i}><small>{new Date(m.created_at).toLocaleString()}</small> <strong>{m.sender === 'user' ? 'Customer' : 'Assistant'}:</strong> {m.message}</p>)}
    </details>)}
  </Card.Body></Card>;
}

export default function HelpAssistant({ signedIn = false }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [asked, setAsked] = useState('');
  const [note, setNote] = useState('');
  const [status, setStatus] = useState('');
  const helpIndex = useMemo(() => HELP_INDEX.map(entry => signedIn && entry.to === '/forgot-password' ? {...entry, to:'/settings?tab=account&section=password', answer:'Open the password section in Settings. Choose "Forgot password?" to request a reset link, or enter your current password to change it.'} : entry), [signedIn]);
  const results = useMemo(() => searchHelp(asked, helpIndex), [asked, helpIndex]);
  const submit = (event) => {
    event.preventDefault();
    const question = query.trim();
    if (!question) return;
    setAsked(question);
    setStatus('');
    if (signedIn) {
      const top = searchHelp(question, helpIndex)[0];
      api('/help/chat', { method: 'POST', body: JSON.stringify({ question, answer: top ? `${top.title}: ${top.answer}` : 'No answer found.' }) }).catch(() => {});
    }
  };
  const escalate = async () => {
    try {
      await api('/help/chat/escalate', { method: 'POST', body: JSON.stringify({ note }) });
      setStatus('Sent. Our support team has your chat. Follow replies in Settings > Help & support.');
      setNote('');
    } catch (err) { setStatus(err.message); }
  };

  return <div className="help-assistant">
    {open && <section className="help-assistant-panel" role="dialog" aria-label="Help assistant">
      <header><strong>Help assistant</strong><button type="button" className="btn-close" aria-label="Close help assistant" onClick={() => setOpen(false)} /></header>
      <p className="help-assistant-hint">Ask a question or search anything in the app.</p>
      <form onSubmit={submit} role="search">
        <input aria-label="Ask the help assistant" className="form-control" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. reset password, games, birthdays" />
        <button className="btn btn-primary" type="submit">Ask</button>
      </form>
      <div className="help-assistant-results" aria-live="polite">
        {asked && !results.length && <p>I could not find that. You can send this chat to our support team below.</p>}
        {results.slice(0, 4).map((entry, index) => <article key={entry.title}>
          <h4>{entry.title}</h4>
          {index === 0 && <p>{entry.answer}</p>}
          <Link to={entry.to} onClick={() => setOpen(false)}>Go there</Link>
        </article>)}
      </div>
      {asked && <div className="help-assistant-escalate">
        <p className="mb-1">Not enough help?</p>
        {signedIn ? <>
          <input aria-label="Note for support" className="form-control mb-2" value={note} maxLength={2000} onChange={(e) => setNote(e.target.value)} placeholder="Anything else we should know? (optional)" />
          <button type="button" className="btn btn-outline-primary btn-sm" onClick={escalate}>Contact support with this chat</button>
        </> : <Link to="/login" onClick={() => setOpen(false)}>Sign in to contact support</Link>}
        {status && <p role="status" className="mt-2 mb-0">{status}</p>}
      </div>}
    </section>}
    <button type="button" className="help-assistant-toggle btn btn-primary" aria-expanded={open} onClick={() => setOpen(!open)}>{open ? 'Close' : 'Help'}</button>
  </div>;
}
