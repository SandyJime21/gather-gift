import {afterEach,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {AdultMemberInvite,GiftSuggestions} from './FamilyAccountTools.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:p=>p}));
afterEach(()=>vi.clearAllMocks());
it('invites an adult to create their own login without pretending delivery succeeded',async()=>{
 api.mockResolvedValueOnce({email_message:{delivery:'not_configured'}});
 render(<AdultMemberInvite householdId={1} profile={{id:7,has_login:false}} email="adult@example.com"/>);
 fireEvent.click(screen.getByRole('button',{name:'Invite to join family'}));
 expect(await screen.findByText('Email was not delivered. Check email settings and try again.')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/households/1/adult-invitations',expect.objectContaining({body:JSON.stringify({profile_id:7,email:'adult@example.com'})}));
});
it('lets the recipient choose a list and approve a suggestion once',async()=>{
 let accepted=false;
 api.mockImplementation(async(path,options)=>{
  if(path==='/gift-suggestions')return {suggestions:accepted?[]:[{id:1,profile_id:7,sender:'Sandra',gift:{name:'Suggested book'}}]};
  if(path==='/profiles/7/wishlists')return {wishlists:[{id:10,title:'Birthday'},{id:11,title:'Christmas'}]};
  if(path==='/gift-suggestions/1/respond'){expect(JSON.parse(options.body)).toEqual({action:'accept',wishlist_id:11});accepted=true;return {};}
  throw Error(path);
 });
 render(<GiftSuggestions/>);
 expect(await screen.findByText('Sandra suggested a gift')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Add to list'})).toBeDisabled();
 fireEvent.change(await screen.findByLabelText('List for Suggested book'),{target:{value:'11'}});
 fireEvent.click(screen.getByRole('button',{name:'Add to list'}));
 await waitFor(()=>expect(screen.queryByText('Suggested book')).not.toBeInTheDocument());
});

it('shows and copies the adult invitation link even when email delivery is unavailable',async()=>{
 const link='https://example.com/accept-invitation/private-adult-token';
 api.mockResolvedValue({email_message:{delivery:'not_configured',link}});
 const copy=vi.fn().mockResolvedValue();Object.defineProperty(navigator,'clipboard',{value:{writeText:copy},configurable:true});
 render(<AdultMemberInvite householdId={2} profile={{id:8,has_login:false}} email="adult@example.com"/>);
 fireEvent.click(screen.getByRole('button',{name:'Invite to join family'}));
 expect(await screen.findByLabelText('Invitation link')).toHaveValue(link);
 fireEvent.click(screen.getByRole('button',{name:'Copy link'}));
 expect(await screen.findByRole('button',{name:'Copied'})).toBeInTheDocument();
 expect(copy).toHaveBeenCalledWith(link);
 expect(screen.getByText('Email was not delivered. Check email settings and try again.')).toBeInTheDocument();
});
