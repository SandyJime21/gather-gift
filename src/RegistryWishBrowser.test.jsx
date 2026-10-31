import {fireEvent,render,screen,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import RegistryWishBrowser from './RegistryWishBrowser.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
it('groups family wishes by list with pets last and filters all gifts in a dialog',async()=>{
 api.mockImplementation(async path=>{
  if(path==='/profiles/1/wishlists')return {wishlists:[{id:11,title:'Christmas',share_publicly:false}]};
  if(path==='/profiles/2/wishlists')return {wishlists:[{id:12,title:'Christmas',share_publicly:true}]};
  return {items:[{id:path.includes('/11/')?1:2,name:path.includes('/11/')?'Pet bed':'Storybook',category:path.includes('/11/')?'pets':'books',estimated_price:25,currency:'USD'}]};
 });
 render(<RegistryWishBrowser family profiles={[{id:1,display_name:'Pretzel',profile_type:'pet'},{id:2,display_name:'Mia',profile_type:'person'}]} renderGift={item=><h4>{item.name}</h4>}/>);
 await screen.findByRole('heading',{name:'Pet bed'});
 expect(screen.getAllByRole('heading',{level:4}).map(e=>e.textContent)).toEqual(['Storybook','Pet bed']);
 fireEvent.click(screen.getByRole('button',{name:'View all'}));
 const dialog=await screen.findByRole('dialog');
 fireEvent.click(within(dialog).getByRole('button',{name:'Filter'}));
 fireEvent.change(within(dialog).getByLabelText('Sharing'),{target:{value:'private'}});
 expect(within(dialog).getByRole('heading',{name:'Pet bed'})).toBeInTheDocument();
 expect(within(dialog).queryByRole('heading',{name:'Storybook'})).not.toBeInTheDocument();
 fireEvent.change(within(dialog).getByLabelText('Search family wishes'),{target:{value:'missing'}});
 expect(within(dialog).getByText('No wishes match these filters.')).toBeInTheDocument();
});
it('loads follower gifts only when View all is opened and offers no sharing controls',async()=>{
 api.mockResolvedValue({wishlists:[]});
 const before=api.mock.calls.length;
 render(<RegistryWishBrowser preview={false} profiles={[{id:3,display_name:'Friend'}]} renderGift={()=>null} title="Friends wishes"/>);
 expect(api.mock.calls.length).toBe(before);
 fireEvent.click(screen.getByRole('button',{name:'View all gifts'}));
 await screen.findByText('No wishes match these filters.');
 expect(screen.queryByLabelText('Sharing')).not.toBeInTheDocument();
});
