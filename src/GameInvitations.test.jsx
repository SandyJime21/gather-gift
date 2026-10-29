import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter,Routes,Route} from 'react-router-dom';
import {afterEach,expect,it,vi} from 'vitest';
import {GameInvitationPage,GameInviteComposer} from './GameInvitations.jsx';
import GiftGamesPage from './GiftGames.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
it('preserves the invitation when a guest creates an account',async()=>{
 api.mockResolvedValue({host:'Alex',title:'Christmas exchange'});
 render(<MemoryRouter initialEntries={['/game-invitations/8/token']}><Routes><Route path="/game-invitations/:gameId/:token" element={<GameInvitationPage user={null}/>}/></Routes></MemoryRouter>);
 const link=await screen.findByRole('button',{name:'Create an account'});
 expect(link).toHaveAttribute('href','/register?next=%2Fgame-invitations%2F8%2Ftoken');
 expect(api).toHaveBeenCalledExactlyOnceWith('/game-invitations/8/token');
});
it('requires separate game and follow decisions instead of automatically accepting',async()=>{
 api.mockImplementation(async(path,options)=>options?{joined:true,game_id:8,message:'Saved'}:{host:'Alex',title:'Christmas exchange'});
 render(<MemoryRouter initialEntries={['/game-invitations/8/token']}><Routes><Route path="/game-invitations/:gameId/:token" element={<GameInvitationPage user={{id:2}}/>}/></Routes></MemoryRouter>);
 const join=await screen.findByLabelText('Join this game?');
 expect(screen.getByRole('button',{name:'Save my choices'})).toBeDisabled();
 fireEvent.change(join,{target:{value:'yes'}});
 fireEvent.change(screen.getByLabelText('Allow Alex to follow you?'),{target:{value:'no'}});
 fireEvent.click(screen.getByRole('button',{name:'Save my choices'}));
 expect(await screen.findByRole('button',{name:'Open game'})).toHaveAttribute('href','/following?tab=games&game=8');
 expect(api).toHaveBeenCalledWith('/game-invitations/8/token',{method:'POST',body:JSON.stringify({join_game:true,allow_follow:false})});
});
it('invites an email address without requiring an existing account',async()=>{
 api.mockResolvedValue({message:'Invitation emailed.',game:{id:8}});
 render(<GameInviteComposer gameId={8}/>);
 fireEvent.change(screen.getByLabelText('Person, family name or email'),{target:{value:'new@example.com'}});
 fireEvent.click(screen.getByRole('button',{name:'Send game invitation'}));
 expect(await screen.findByText('Invitation emailed.')).toBeInTheDocument();
 expect(api).toHaveBeenCalledExactlyOnceWith('/games/8/email-invitations',{method:'POST',body:JSON.stringify({email:'new@example.com'})});
});
it('places a create button inside the empty games message',async()=>{
 api.mockImplementation(async path=>path==='/games/options'?{households:[{id:1,name:'My registry',can_host:true,profiles:[{id:1,name:'Alex'}]}]}:{games:[]});
 render(<MemoryRouter><GiftGamesPage/></MemoryRouter>);
 const create=await screen.findByRole('button',{name:'Create a game'});
 expect(create.closest('.empty-state')).toHaveTextContent('No active games yet.');
 fireEvent.click(create);
 await waitFor(()=>expect(screen.getByText('Plan your exchange')).toBeInTheDocument());
 expect(screen.getByText(/You are not following anyone yet/)).toBeInTheDocument();
});
