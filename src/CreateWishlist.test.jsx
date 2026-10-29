import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {CreateWishlist} from './App.jsx';
import {clearCsrfToken} from './lib/api.js';

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
