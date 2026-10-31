import {useState} from 'react';
import {fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {FamilyCollectionManager,FamilyCollectionCards} from './FamilyCollections.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:value=>value}));
it('selects matching managed lists and saves one family sharing choice',async()=>{
 api.mockImplementation(async path=>path.startsWith('/profiles/')?{wishlists:[{id:path.includes('/7/')?11:12,title:'Christmas'}]}:{collection:{}});
 render(<FamilyCollectionManager profiles={[{id:7,display_name:'Mia',can_edit:true,household_id:9,household_name:'Gonzales'},{id:8,display_name:'Sam',can_edit:true,household_id:9,household_name:'Gonzales'},{id:10,display_name:'Joined adult',can_edit:false,household_id:9}]}/>);
 fireEvent.click(screen.getByRole('button',{name:'Family collection'}));
 await screen.findByLabelText('Mia / Christmas');
 fireEvent.change(screen.getByLabelText('Choose matching lists'),{target:{value:'christmas'}});
 expect(screen.getByLabelText('Mia / Christmas')).toBeChecked();
 expect(screen.getByLabelText('Sam / Christmas')).toBeChecked();
 expect(screen.queryByText('Joined adult')).not.toBeInTheDocument();
 fireEvent.click(screen.getByLabelText('Share selected lists with approved followers'));
 fireEvent.click(screen.getByRole('button',{name:'Save family collection'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/households/9/list-collections',expect.objectContaining({method:'POST'})));
 const body=JSON.parse(api.mock.calls.find(([path,options])=>options?.method==='POST')[1].body);
 expect(body).toMatchObject({title:'Gonzales - Christmas',wishlist_ids:[11,12],share_publicly:true,use_family_photo:true});
});
function Browser(){const [budget,setBudget]=useState({minimum:'',maximum:'',currency:'USD'});return <FamilyCollectionCards household={{id:9}} budget={budget} onBudgetChange={setBudget} renderGift={item=><h3>{item.name}</h3>}/>;}
it('opens a collection with artwork and filters wishes by type and search',async()=>{
 api.mockImplementation(async path=>path.endsWith('/list-collections')?{collections:[{id:1,title:'Gonzales Christmas',cover_url:'https://images.example/art.jpg',list_count:2}]}:{items:[{id:1,name:'Puzzle',category:'toys',recipient:'Mia',profile_id:7,estimated_price:20},{id:2,name:'Storybook',category:'books',recipient:'Sam',profile_id:8,estimated_price:30}]});
 render(<Browser/>);
 fireEvent.click(await screen.findByRole('button',{name:'Gonzales Christmas 2 member lists'}));
 const dialog=await screen.findByRole('dialog');
 expect(await within(dialog).findByRole('heading',{name:'Puzzle'})).toBeInTheDocument();
 expect(within(dialog).getByRole('heading',{name:'Storybook'})).toBeInTheDocument();
 fireEvent.click(within(dialog).getByRole('button',{name:'Filter'}));
 fireEvent.change(within(dialog).getByLabelText('Gift type'),{target:{value:'books'}});
 expect(within(dialog).queryByRole('heading',{name:'Puzzle'})).not.toBeInTheDocument();
 fireEvent.change(within(dialog).getByLabelText('Search family collection'),{target:{value:'not present'}});
 expect(within(dialog).getByText('No shared wishes match these filters.')).toBeInTheDocument();
});
