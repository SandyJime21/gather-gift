import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {beforeEach,expect,it,vi} from 'vitest';
import ProfileListsEditor from './ProfileListsEditor.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
beforeEach(()=>{api.mockReset();});
it('adds a gift directly to the selected list and resets the form when switching lists',async()=>{
 let gifts=[];
 api.mockImplementation(async(path,options)=>{
  if(path==='/profiles/7')return {profile:{id:7,display_name:'Mia',can_edit:true,can_add:true}};
  if(path==='/profiles/7/wishlists')return {wishlists:[{id:11,title:'Birthday'},{id:12,title:'Christmas'}]};
  if(path==='/wishlists/12/items'&&options?.method==='POST'){gifts=[{id:50,...JSON.parse(options.body)}];return {item:gifts[0]};}
  if(path==='/wishlists/12/items')return {items:gifts};
  if(path==='/wishlists/11/items')return {items:[]};
  throw Error(path);
 });
 render(<MemoryRouter><ProfileListsEditor profile={{id:7,display_name:'Mia'}}/></MemoryRouter>);
 fireEvent.click(await screen.findByRole('button',{name:'Add gift'}));
 fireEvent.change(screen.getByLabelText('Wish name'),{target:{value:'Unfinished birthday idea'}});
 fireEvent.change(screen.getByLabelText('Wishlist'),{target:{value:'12'}});
 expect(screen.queryByLabelText('Wish name')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Add gift'}));
 expect(screen.getByLabelText('Wish name')).toHaveValue('');
 expect(screen.getByText('Adding to Christmas for Mia')).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Wish name'),{target:{value:'Christmas puzzle'}});
 fireEvent.click(screen.getByRole('button',{name:'Add to Christmas'}));
 expect(await screen.findByRole('status')).toHaveTextContent('Gift added to Christmas.');
 expect(await screen.findByText('Christmas puzzle')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/wishlists/12/items',expect.objectContaining({method:'POST'}));
 expect(api).not.toHaveBeenCalledWith('/wishlists/11/items',expect.objectContaining({method:'POST'}));
});
it('creates the first list without requiring child mode or a PIN',async()=>{
 api.mockImplementation(async(path,options)=>{
  if(path==='/profiles/7')return {profile:{id:7,can_edit:true,can_add:true}};
  if(path==='/profiles/7/wishlists'&&options?.method==='POST')return {wishlist:{id:13,title:'Christmas'}};
  if(path==='/profiles/7/wishlists')return {wishlists:[]};
  return {items:[]};
 });
 render(<MemoryRouter><ProfileListsEditor profile={{id:7}}/></MemoryRouter>);
 const name=await screen.findByLabelText('New list name');
 fireEvent.change(name,{target:{value:'Christmas'}});
 fireEvent.click(screen.getByRole('button',{name:'Create list'}));
 expect(await screen.findByRole('button',{name:'Rename Christmas'})).toBeInTheDocument();
 expect(screen.getByLabelText('Wishlist')).toHaveValue('13');
 expect(api).toHaveBeenCalledWith('/profiles/7/wishlists',expect.objectContaining({method:'POST',body:JSON.stringify({title:'Christmas'})}));
 expect(api).not.toHaveBeenCalledWith('/household-session/pin',expect.anything());
});
it('lets an authorized manager rename lists and edit their gifts inside the dialog section',async()=>{
 let name='Puzzle';
 api.mockImplementation(async(path,options)=>{
  if(path==='/profiles/7')return {profile:{id:7,can_edit:true,can_remove_wishes:true,can_add:true}};
  if(path==='/profiles/7/wishlists')return {wishlists:[{id:11,title:'Birthday',share_publicly:false}]};
  if(path==='/wishlists/11/items')return {items:[{id:12,name,estimated_price:'12.00'}]};
  if(path==='/items/12'){name=JSON.parse(options.body).name;return {};}
  if(path==='/wishlists/11')return {};
  throw new Error(path);
 });
 render(<MemoryRouter><ProfileListsEditor profile={{id:7}}/></MemoryRouter>);
 fireEvent.click(await screen.findByRole('button',{name:'Rename Birthday'}));
 fireEvent.change(screen.getByLabelText('List name'),{target:{value:'Christmas'}});
 fireEvent.submit(screen.getByLabelText('List name').closest('form'));
 expect(await screen.findByRole('button',{name:'Rename Christmas'})).toBeInTheDocument();
 fireEvent.click(await screen.findByRole('button',{name:'Edit gift'}));
 fireEvent.change(screen.getByLabelText('Gift name'),{target:{value:'Bigger puzzle'}});
 fireEvent.submit(screen.getByLabelText('Gift name').closest('form'));
 expect(await screen.findByText('Bigger puzzle')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/items/12',expect.objectContaining({method:'PATCH'}));
});
it("shows a separately signed-in adult's shared wishes without editing controls",async()=>{
 api.mockImplementation(async path=>path==='/profiles/8'?{profile:{id:8,is_adult:true,has_login:true,can_edit:false,can_remove_wishes:false,can_add:false}}:path==='/profiles/8/wishlists'?{wishlists:[{id:11,title:'Birthday'}]}:{items:[{id:12,name:'Shared gift'}]});
 render(<MemoryRouter><ProfileListsEditor profile={{id:8}}/></MemoryRouter>);
 expect(await screen.findByText('Shared gift')).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Edit gift'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Remove gift'})).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'New list'})).not.toBeInTheDocument();
});
