import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {CreateWishlist} from './App.jsx';
import {clearCsrfToken} from './lib/api.js';
import CreateWishlistManager from './CreateWishlist.jsx';

afterEach(()=>vi.unstubAllGlobals());

it('creates matching lists for selected members with optional child approval',async()=>{
 clearCsrfToken();
 let sent;
 vi.stubGlobal('fetch',vi.fn(async(url,options={})=>{
  if(url==='/api/auth/csrf')return {ok:true,json:async()=>({csrf_token:'test'})};
  sent=JSON.parse(options.body);
  return {ok:true,json:async()=>({wishlists:[{id:81,profile_id:1,name:'Mia',title:'Christmas'},{id:82,profile_id:2,name:'Pretzel',title:'Christmas'}]})};
 }));
 render(<MemoryRouter><CreateWishlist profiles={[
  {id:1,display_name:'Mia',household_name:'Family',can_edit:true,is_adult:false,profile_type:'person'},
  {id:2,display_name:'Pretzel',household_name:'Family',can_edit:true,profile_type:'pet'},
  {id:3,display_name:'Other adult',household_name:'Family',can_edit:false,is_adult:true},
 ]}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'New list'}));
 expect(screen.queryByLabelText('Other adult / Family')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Select all managed members'}));
 const permission=screen.getByLabelText('Let selected children add wishes to this list in child mode');
 expect(permission).toBeChecked();
 fireEvent.click(permission);
 fireEvent.change(screen.getByLabelText('List name'),{target:{value:'Christmas'}});
 fireEvent.click(screen.getByRole('button',{name:'Create list'}));
 await waitFor(()=>expect(sent).toEqual({title:'Christmas',profile_ids:[1,2],allow_child_items:false}));
 expect(await screen.findByRole('link',{name:'Mia: Christmas'})).toHaveAttribute('href','/profiles/1?wishlist=81');
 expect(screen.getByRole('link',{name:'Pretzel: Christmas'})).toHaveAttribute('href','/profiles/2?wishlist=82');
});

it('assigns an existing list name only to members who do not already have it',async()=>{
 clearCsrfToken();let assigned=false,sent;
 vi.stubGlobal('fetch',vi.fn(async(url,options={})=>{
  let result={};
  if(url==='/api/auth/csrf')result={csrf_token:'test'};
  else if(url==='/api/profiles/1/wishlists')result={wishlists:[{id:11,title:'Christmas'}]};
  else if(url==='/api/profiles/2/wishlists')result={wishlists:assigned?[{id:22,title:'Christmas'}]:[]};
  else if(url==='/api/profiles/3/wishlists')result={wishlists:[{id:33,title:'Christmas'}]};
  else if(url==='/api/wishlists/batch'){sent=JSON.parse(options.body);assigned=true;result={wishlists:[{id:22,profile_id:2,name:'Sam',title:'Christmas'}]};}
  return {ok:true,json:async()=>result};
 }));
 render(<MemoryRouter><CreateWishlistManager profiles={[
  {id:1,display_name:'Mia',household_name:'Family',can_edit:true,is_adult:false},
  {id:2,display_name:'Sam',household_name:'Family',can_edit:true,is_adult:false},
  {id:3,display_name:'Pretzel',household_name:'Family',can_edit:true,profile_type:'pet'},
 ]}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'New list'}));
 fireEvent.click(screen.getByRole('button',{name:'Assign existing'}));
 await waitFor(()=>expect(screen.getByLabelText('Existing list')).toHaveValue('11'));
 expect(screen.getByLabelText('Mia / Family')).toBeDisabled();
 expect(screen.getByLabelText('Pretzel / Family')).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Select all managed members'}));
 expect(screen.getByLabelText('Sam / Family')).toBeChecked();
 fireEvent.click(screen.getByRole('button',{name:'Assign list name'}));
 expect(await screen.findByRole('link',{name:'Sam: Christmas'})).toHaveAttribute('href','/profiles/2?wishlist=22');
 expect(sent).toEqual({source_wishlist_id:11,profile_ids:[2],allow_child_items:true});
});

it('opens quick assignment for the selected list from Manage lists',async()=>{
 clearCsrfToken();
 vi.stubGlobal('fetch',vi.fn(async()=>({ok:true,json:async()=>({wishlists:[{id:11,title:'Christmas'}]})})));
 render(<MemoryRouter><CreateWishlistManager profiles={[{id:1,display_name:'Mia',household_name:'Family',can_edit:true}]}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'Manage lists'}));
 fireEvent.click(await screen.findByRole('button',{name:'Assign this list to other members'}));
 await waitFor(()=>expect(screen.getByLabelText('Existing list')).toHaveValue('11'));
 expect(screen.getByText(/Reuse the name only/)).toBeInTheDocument();
});

it('only deletes a managed list after confirmation and allows cancelling',async()=>{
 clearCsrfToken();let deleted=false;
 vi.stubGlobal('fetch',vi.fn(async(url,options={})=>{
  if(options.method==='DELETE'){deleted=true;return {ok:true,json:async()=>({status:'deleted'})};}
  return {ok:true,json:async()=>url==='/api/auth/csrf'?{csrf_token:'test'}:{wishlists:[{id:11,title:'Christmas'}]}};
 }));
 render(<MemoryRouter><CreateWishlistManager profiles={[{id:1,display_name:'Mia',household_name:'Family',can_edit:true}]}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'Manage lists'}));
 fireEvent.click(await screen.findByRole('button',{name:'Delete list'}));
 let confirmation=(await screen.findByRole('heading',{name:'Delete this list?'})).closest('.modal-content');
 expect(confirmation).toHaveTextContent('Christmas');
 expect(confirmation).toHaveTextContent('Mia');
 expect(deleted).toBe(false);
 fireEvent.click(within(confirmation).getByRole('button',{name:'Cancel'}));
 expect(deleted).toBe(false);
 fireEvent.click(await screen.findByRole('button',{name:'Delete list'}));
 confirmation=(await screen.findByRole('heading',{name:'Delete this list?'})).closest('.modal-content');
 fireEvent.click(within(confirmation).getByRole('button',{name:'Yes, delete list'}));
 expect(await screen.findByText('List deleted. Gifts on other lists were kept.')).toBeInTheDocument();
 expect(deleted).toBe(true);
 expect(screen.queryByRole('button',{name:'Delete list'})).not.toBeInTheDocument();
});
