import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import ProductActions from './ProductActions.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
const product={id:5,name:'Puzzle',estimated_price:'20',currency:'USD',product_url:'https://example.com/puzzle'};
it('sends suggestions to claimed adults without editing their lists',async()=>{
 api.mockResolvedValue({});
 render(<ProductActions product={product} listOnly profiles={[{id:8,display_name:'Joined adult',can_edit:false,can_suggest:true}]}/>);
 fireEvent.click(screen.getByRole('button',{name:'+ Wish'}));
 fireEvent.change(screen.getByLabelText('Whose wishlist?'),{target:{value:'8'}});
 expect(screen.queryByLabelText('Wishlist')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Send suggestion'}));
 expect(await screen.findByRole('status')).toHaveTextContent('Suggestion sent');
 expect(api).toHaveBeenCalledWith('/profiles/8/suggestions',expect.objectContaining({method:'POST'}));
});
it('adds a Discover product privately to Buying now',async()=>{
 api.mockResolvedValue({});
 render(<ProductActions product={product} profiles={[]} selfName="Alex"/>);
 fireEvent.click(screen.getByRole('button',{name:'Buying now'}));
 fireEvent.click(screen.getByRole('button',{name:'Add to Buying now'}));
 expect(await screen.findByRole('status')).toHaveTextContent('Added to Buying now');
 const body=JSON.parse(api.mock.calls[0][1].body);
 expect(api.mock.calls[0][0]).toBe('/private-gifts');
 expect(body).toMatchObject({name:'Puzzle',recipient:'Alex',buying_now:true});
});
it('only offers controlled profiles when copying to a wishlist',async()=>{
 api.mockImplementation(async path=>path==='/profiles/7/wishlists'?{wishlists:[{id:11,title:'Christmas'}]}:{});
 render(<ProductActions product={product} listOnly profiles={[{id:7,display_name:'Mia',can_edit:true},{id:8,display_name:'Other adult',can_edit:false}]}/>);
 fireEvent.click(screen.getByRole('button',{name:'+ Wish'}));
 expect(screen.queryByRole('option',{name:'Other adult'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Whose wishlist?'),{target:{value:'7'}});
 await waitFor(()=>expect(screen.getByLabelText('Wishlist')).toHaveValue('11'));
 fireEvent.click(screen.getByRole('button',{name:'Add to list'}));
 expect(await screen.findByRole('status')).toHaveTextContent('Added to your wishlist');
 expect(api).toHaveBeenCalledWith('/wishlists/11/items',expect.objectContaining({method:'POST'}));
});
