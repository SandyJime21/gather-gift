import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GiftGamesPage from './GiftGames.jsx';
import { api } from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:path=>path}));
afterEach(()=>vi.clearAllMocks());
const participants=[{id:1,name:'Alex'},{id:2,name:'Blair'}];
const base={id:1,title:'Family exchange',kind:'secret_santa',status:'drawn',version:1,participants,can_host:false,your_profile_id:1,assignment_profiles:[1],gifts:[],order:[],max_steals:2};
it('reveals only the active secret recipient and lets the player hide it',async()=>{
 api.mockImplementation(async(path)=>{if(path==='/games/options')return {households:[]};if(path==='/games')return {games:[base]};if(path==='/games/1')return {game:base};if(path==='/games/1/assignment')return {recipient:{id:2,name:'Blair',can_view_wishes:true}};throw Error('Unexpected request');});
 render(<MemoryRouter initialEntries={['/games?game=1']}><GiftGamesPage GiftFinder={()=>null} activeProfileId={1}/></MemoryRouter>);
 fireEvent.click(await screen.findByRole('button',{name:'Reveal my recipient'}));
 expect(await screen.findByText('You are gifting Blair!')).toBeInTheDocument();
 expect(screen.getByRole('link',{name:'Browse their wishes'})).toHaveAttribute('href','/profiles/2');
 fireEvent.click(screen.getByRole('button',{name:'Hide recipient'}));
 expect(screen.queryByText('You are gifting Blair!')).not.toBeInTheDocument();
});
it('shows wrapped gifts and sends versioned white-elephant actions',async()=>{
 const game={...base,kind:'white_elephant',status:'active',your_profile_id:2,current_player_id:2,order:[1,2],gifts:[{id:'opened',opened:true,name:'Puzzle',holder_id:1,steals:0},{id:'wrapped',opened:false,holder_id:null,steals:0}]};
 api.mockImplementation(async(path,options)=>{if(path==='/games/options')return {households:[]};if(path==='/games')return {games:[game]};if(path==='/games/1')return {game};if(path==='/games/1/turn'){expect(JSON.parse(options.body)).toEqual({action:'steal',gift_id:'opened',version:1});return {game:{...game,version:2,current_player_id:1}};}throw Error('Unexpected request');});
 render(<MemoryRouter initialEntries={['/games?game=1']}><GiftGamesPage GiftFinder={()=>null} activeProfileId={2}/></MemoryRouter>);
 expect(await screen.findByText('Wrapped gift 2')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Steal this gift'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Steal this gift'})).not.toBeInTheDocument());
 expect(screen.queryByRole('button',{name:'Open gift'})).not.toBeInTheDocument();
});

it('selects participants across followed families and formats a money budget',async()=>{
 const homes=[{id:1,name:'Our family',can_host:true,profiles:[{id:1,name:'Alex'}]},{id:2,name:'Followed family',can_host:false,profiles:[{id:2,name:'Blair'}]}];
 api.mockImplementation(async(path,options)=>{
  if(path==='/games/options')return {households:homes};
  if(path==='/games' && !options)return {games:[]};
  if(path==='/games' && options){const body=JSON.parse(options.body);expect(body.participants).toEqual([1,2]);expect(body.budget).toBe('1.03');return {game:{...base,status:'waiting'}};}
  if(path==='/games/1')return {game:{...base,status:'waiting'}};
  throw Error(path);
 });
 render(<MemoryRouter><GiftGamesPage GiftFinder={()=>null}/></MemoryRouter>);
 fireEvent.click(await screen.findByRole('button',{name:'+ Create a game'}));
 expect(screen.queryByLabelText('Family')).not.toBeInTheDocument();
 expect(screen.queryByLabelText('Game name')).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Gift budget (USD, optional)'),{target:{value:'1.033333'}});
 fireEvent.blur(screen.getByLabelText('Gift budget (USD, optional)'));
 fireEvent.click(screen.getByLabelText('Our family'));
 expect(screen.getByLabelText('Alex')).toBeChecked();
 fireEvent.change(screen.getByLabelText('Search game participants'),{target:{value:'Followed family'}});
 expect(screen.queryByLabelText('Alex')).not.toBeInTheDocument();
 fireEvent.click(screen.getByLabelText('Followed family'));
 expect(screen.getByLabelText('Blair')).toBeChecked();
 expect(screen.getByText('2 selected')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Create game'}));
 expect(await screen.findByRole('button',{name:'All games'})).toBeInTheDocument();
});
