import {useState} from 'react';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import FollowedFamilyBrowser from './FollowedFamilyBrowser.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:path=>path}));
function Browser(){const [budget,setBudget]=useState({minimum:'',maximum:'',currency:'USD'});return <FollowedFamilyBrowser household={{id:9,name:'Family'}} budget={budget} onBudgetChange={setBudget} renderGift={item=><h3>{item.name}</h3>}/>;}
it('opens member cards, filters all wishes by list and budget, and adds a private copy',async()=>{
 api.mockImplementation(async(path,options)=>{
  if(path==='/households/9')return {profiles:[{id:7,display_name:'Mia',photo_path:'/mia.jpg'},{id:8,display_name:'Sam'}]};
  if(path==='/profiles/7/wishlists')return {wishlists:[{id:11,title:'Birthday'},{id:12,title:'Christmas'}]};
  if(path==='/wishlists/11/items')return {items:[{id:1,name:'Puzzle',estimated_price:15,currency:'USD'}]};
  if(path==='/wishlists/12/items')return {items:[{id:2,name:'Console',estimated_price:500,currency:'USD'}]};
  if(path==='/personal-wishes'&&options?.method==='POST')return {};
  throw new Error(path);
 });
 render(<Browser/>);
 const member=await screen.findByRole('button',{name:'Mia View wishes'});
 expect(member.querySelector('img')).toHaveAttribute('src','/mia.jpg');
 fireEvent.click(member);
 expect(await screen.findByRole('heading',{name:'Puzzle'})).toBeInTheDocument();
 expect(screen.getByRole('heading',{name:'Console'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Filter'}));
 fireEvent.change(screen.getByLabelText('Wishlist'),{target:{value:'12'}});
 expect(screen.queryByRole('heading',{name:'Puzzle'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Wishlist'),{target:{value:''}});
 fireEvent.change(screen.getByLabelText('Price range'),{target:{value:'25'}});
 expect(screen.queryByRole('heading',{name:'Console'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Search wishes'),{target:{value:'puzzle'}});
 fireEvent.click(screen.getByRole('button',{name:'Add to my wishes'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/personal-wishes',expect.objectContaining({method:'POST'})));
 const copied=JSON.parse(api.mock.calls.find(([path])=>path==='/personal-wishes')[1].body);
 expect(copied).toMatchObject({name:'Puzzle',visibility:'private',viewer_ids:[]});
 fireEvent.click(screen.getByRole('button',{name:'All members'}));
 expect(await screen.findByRole('button',{name:'Sam View wishes'})).toBeInTheDocument();
});
