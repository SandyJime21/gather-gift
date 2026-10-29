import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import FamilyInvites, { InvitationInbox } from './FamilyInvites.jsx';
import { api } from './lib/api.js';
vi.mock('./lib/api.js', () => ({ api: vi.fn() }));
afterEach(() => vi.clearAllMocks());
it('shares only selected lists back to a mutual connection', async () => {
  api.mockImplementation(async (path, options) => {
    if (path === '/family-connections') return { connections: [{ user_id: 7, name: 'Alex', mutual: true, shared_households: [] }] };
    if (path === '/households/1') return { profiles: [{ id: 11, display_name: 'Shared member' }, { id: 12, display_name: 'Private member' }] };
    if (path === '/family-connections/7/share') {
      expect(JSON.parse(options.body)).toEqual({ household_id: 1, share_all_profiles: true });
      return { message: 'Selected lists shared.' };
    }
    throw new Error(path);
  });
  render(<MemoryRouter><FamilyInvites households={[{ id: 1, name: 'Our family', role: 'owner', registry_type: 'family' }]} /></MemoryRouter>);
  fireEvent.click(screen.getByRole('button', { name: 'View family connections' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Share my lists back' }));
  fireEvent.change(screen.getByLabelText('Family to share back'), { target: { value: '1' } });

  fireEvent.click(await screen.findByRole('button', { name: 'Share family wishlists' }));
  expect(await screen.findByText('Selected lists shared.')).toBeInTheDocument();
});

it('finds an existing family and sends a follow request for selected lists', async () => {
  api.mockImplementation(async (path, options) => {
    if(path==='/invitations')return {sent:[],received:[]};
    if(path==='/families/lookup')return {match:{name:'Alex family',photo:null}};
    if(path==='/households/1')return {profiles:[{id:11,display_name:'Sam'}]};
    if(path==='/households/1/invitations'){
      expect(JSON.parse(options.body)).toEqual({email:'alex@example.com',role:'shopper',share_all_profiles:true});
      return {email_message:{delivery:'sent'}};
    }
    throw new Error(path);
  });
  render(<MemoryRouter><FamilyInvites households={[{id:1,name:'Our family',role:'owner',registry_type:'family'}]}/></MemoryRouter>);
  expect(screen.queryByLabelText('Person, family name or email')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Send request'}));
  fireEvent.change(screen.getByLabelText('Person, family name or email'),{target:{value:'alex@example.com'}});
  fireEvent.click(screen.getByRole('button',{name:'Find people'}));
  expect(await screen.findByText('Alex family')).toBeInTheDocument();
  expect(screen.queryByLabelText('Share this family registry')).not.toBeInTheDocument();

  fireEvent.click(await screen.findByRole('button',{name:'Send follow request'}));
  expect(await screen.findByText('Request sent.')).toBeInTheDocument();
});

it('keeps sent requests visible and refreshes their response status',async()=>{
 let accepted=false;
 api.mockImplementation(async path=>{
  if(path==='/invitations')return {received:[],sent:[{id:9,family:'Our family',email:'guest@example.com',recipient_name:'Guest family',status:accepted?'accepted':'pending'}]};
  throw Error(path);
 });
 render(<MemoryRouter><FamilyInvites households={[]}/></MemoryRouter>);
 expect(await screen.findByRole('heading',{name:'Sent requests (1)'})).toBeVisible();
 expect(screen.getByText('Guest family')).toBeVisible();
 expect(screen.getByText('Pending - waiting for a response')).toBeVisible();
 accepted=true;window.dispatchEvent(new Event('invitations-updated'));
 expect(await screen.findByText('No requests sent yet.')).toBeVisible();
 expect(screen.queryByText('Accepted')).not.toBeInTheDocument();
 expect(screen.queryByText('Pending - waiting for a response')).not.toBeInTheDocument();
});

it('shows only pending requests and removes a received request after acceptance', async () => {
 let accepted=false;
 api.mockImplementation(async path=>{
  if(path==='/invitations/accept'){accepted=true;return {};}
  if(path==='/invitations')return {sent:[{id:2,family:'Old family',email:'old@example.com',status:'accepted'}],received:[{id:1,family:'New family',email:'me@example.com',status:accepted?'accepted':'pending'}]};
  throw new Error(path);
 });
 render(<InvitationInbox pendingOnly/>);
 expect(await screen.findByText('New family')).toBeInTheDocument();
 expect(screen.queryByText('To old@example.com')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Accept follow request'}));
 expect(await screen.findByText('No received requests.')).toBeInTheDocument();
 expect(screen.queryByText('New family')).not.toBeInTheDocument();
});

it('removes declined requests from the pending sent list', async()=>{
 let declined=false;
 api.mockImplementation(async()=>({sent:[{id:3,family:'Our family',email:'friend@example.com',status:declined?'declined':'pending'}],received:[]}));
 render(<InvitationInbox pendingOnly/>);
 expect(await screen.findByText('Request sent')).toBeInTheDocument();
 declined=true;fireEvent(window,new Event('invitations-updated'));
 expect(await screen.findByText('No requests sent yet.')).toBeInTheDocument();
 expect(screen.queryByText('Request sent')).not.toBeInTheDocument();
});
