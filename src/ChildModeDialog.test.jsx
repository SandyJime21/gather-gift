import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import ChildModeDialog from './ChildModeDialog.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
const controls={web_search:false,product_links:false,manage_pets:false,switch_siblings:false,game_invites:false};
const initial=()=>({controls:{...controls},available:false,enabled:false,has_parent_pin:false,wishlist_ids:[1,2],wishlists:[{id:1,title:'Everyday wishes'},{id:2,title:'Birthday'}]});

it('sets the parent PIN then saves the child lists and activities from one dialog',async()=>{
 let data=initial();let saved;
 api.mockImplementation(async(path,options)=>{
  if(path==='/household-session/pin'){expect(JSON.parse(options.body)).toEqual({pin:'123456',password:'parent-password'});return {status:'saved'};}
  if(options?.method==='PATCH'){saved=JSON.parse(options.body);data={...data,enabled:saved.enabled,wishlist_ids:saved.wishlist_ids,controls:{...controls,web_search:true},has_parent_pin:true,available:true};return data;}
  return data;
 });
 render(<ChildModeDialog profile={{id:7,display_name:'Mia'}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Child mode & PIN'}));
 expect(await screen.findByLabelText('Enable child mode for Mia')).toBeDisabled();
 fireEvent.change(screen.getByLabelText('Parent PIN'),{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Confirm parent PIN'),{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Your account password'),{target:{value:'parent-password'}});
 fireEvent.click(screen.getByRole('button',{name:'Save parent PIN'}));
 await screen.findByText('Parent PIN saved.');
 fireEvent.click(screen.getByLabelText('Enable child mode for Mia'));
 fireEvent.click(screen.getByLabelText('Birthday'));
 fireEvent.click(screen.getByText('Allowed activities'));
 fireEvent.click(screen.getByLabelText('Search online for gifts'));
 fireEvent.click(screen.getByRole('button',{name:'Save child mode settings'}));
 await screen.findByText('Child mode settings saved.');
 expect(saved).toEqual({enabled:true,wishlist_ids:[1],...controls,web_search:true});
 expect(screen.getByLabelText('Your account password')).toHaveValue('');
});

it('does not send mismatched PINs',async()=>{
 api.mockResolvedValue(initial());
 render(<ChildModeDialog profile={{id:7,display_name:'Mia'}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Child mode & PIN'}));
 await screen.findByLabelText('Parent PIN');
 fireEvent.change(screen.getByLabelText('Parent PIN'),{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Confirm parent PIN'),{target:{value:'654321'}});
 fireEvent.change(screen.getByLabelText('Your account password'),{target:{value:'parent-password'}});
 fireEvent.click(screen.getByRole('button',{name:'Save parent PIN'}));
 await screen.findByText('The PINs must match.');
 expect(api).not.toHaveBeenCalledWith('/household-session/pin',expect.anything());
});

it('requires an approved wishlist while child mode is enabled',async()=>{
 api.mockResolvedValue({...initial(),has_parent_pin:true,enabled:true,wishlist_ids:[]});
 render(<ChildModeDialog profile={{id:7,display_name:'Mia'}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Child mode & PIN'}));
 await screen.findByLabelText('Enable child mode for Mia');
 expect(screen.getByRole('button',{name:'Save child mode settings'})).toBeDisabled();
 fireEvent.click(screen.getByLabelText('Everyday wishes'));
 await waitFor(()=>expect(screen.getByRole('button',{name:'Save child mode settings'})).toBeEnabled());
});

it('opens PIN setup directly even when a PIN already exists',async()=>{
 api.mockResolvedValue({...initial(),has_parent_pin:true});
 render(<ChildModeDialog profile={{id:7,display_name:'Mia'}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Set / change parent PIN'}));
 const pin=await screen.findByLabelText('Parent PIN');
 expect(pin.closest('details')).toBeNull();
 expect(pin).toBeEnabled();
});

it('allows saving a PIN inline before any lists or child account are enabled',async()=>{
 api.mockImplementation(async(path)=>path==='/household-session/pin'?{status:'saved'}:{...initial(),wishlist_ids:[],wishlists:[]});
 render(<ChildModeDialog embedded profile={{id:7,display_name:'Mia'}}/>);
 const pin=await screen.findByLabelText('Parent PIN');
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 fireEvent.change(pin,{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Confirm parent PIN'),{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Your account password'),{target:{value:'parent-password'}});
 fireEvent.click(screen.getByRole('button',{name:'Save parent PIN'}));
 expect(await screen.findByText('Parent PIN saved.')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/household-session/pin',expect.objectContaining({method:'POST'}));
 expect(api).not.toHaveBeenCalledWith('/profiles/7/child-controls',expect.objectContaining({method:'PATCH'}));
});
