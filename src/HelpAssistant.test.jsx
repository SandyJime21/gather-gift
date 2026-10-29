import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import HelpAssistant, { searchHelp } from './HelpAssistant.jsx';
import { api } from './lib/api.js';

vi.mock('./lib/api.js', () => ({ api: vi.fn(() => Promise.resolve({})) }));

const ask = (text) => {
  fireEvent.change(screen.getByLabelText('Ask the help assistant'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Ask' }));
};

describe('HelpAssistant', () => {
  afterEach(() => vi.clearAllMocks());

  it('finds entries by keyword', () => {
    expect(searchHelp('how do I reset my password')[0].title).toBe('Reset my password');
    expect(searchHelp('zzzz')).toEqual([]);
  });

  it('logs the chat and escalates it to support when signed in', async () => {
    render(<MemoryRouter><HelpAssistant signedIn /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'Help' }));
    ask('secret santa game');
    expect(screen.getByRole('heading', { name: 'Gift games' })).toBeInTheDocument();
    expect(api).toHaveBeenCalledWith('/help/chat', expect.objectContaining({ method: 'POST' }));
    fireEvent.click(screen.getByRole('button', { name: 'Contact support with this chat' }));
    await waitFor(() => expect(api).toHaveBeenCalledWith('/help/chat/escalate', expect.objectContaining({ method: 'POST' })));
    expect(await screen.findByRole('status')).toHaveTextContent('Sent.');
  });

  it('asks guests to sign in and does not log', () => {
    render(<MemoryRouter><HelpAssistant /></MemoryRouter>);
    fireEvent.click(screen.getByRole('button', { name: 'Help' }));
    ask('qqqq');
    expect(screen.getByRole('link', { name: 'Sign in to contact support' })).toBeInTheDocument();
    expect(api).not.toHaveBeenCalled();
  });
});

it.each([true,false])('routes password help according to signed-in status (%s)',signedIn=>{
 render(<MemoryRouter><HelpAssistant signedIn={signedIn}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'Help'}));
 ask('forgot password');
 expect(screen.getAllByRole('link',{name:'Go there'})[0]).toHaveAttribute('href',signedIn?'/settings?tab=account&section=password':'/forgot-password');
 if(signedIn)expect(screen.getByText(/Open the password section in Settings/)).toBeInTheDocument();
});
