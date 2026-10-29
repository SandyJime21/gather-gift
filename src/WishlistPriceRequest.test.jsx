import {fireEvent,render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import WishlistPriceRequest from './WishlistPriceRequest.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
it('sends the selected member, wishlist and price range',async()=>{
 api.mockResolvedValue({message:'Request sent.'});
 render(<WishlistPriceRequest profile={{id:7,display_name:'Mia'}} lists={[{id:11,title:'Christmas'}]} listId="11"/>);
 fireEvent.click(screen.getByRole('button',{name:'Request more wishes'}));
 expect(screen.getByLabelText('Minimum price')).toHaveValue(0);
 expect(screen.getByLabelText('Maximum price')).toHaveValue(50);
 fireEvent.click(screen.getByRole('button',{name:'Send request'}));
 expect(await screen.findByText('Request sent.')).toBeInTheDocument();
 expect(api).toHaveBeenCalledExactlyOnceWith('/profiles/7/price-requests',{method:'POST',body:JSON.stringify({minimum:'0',maximum:'50',currency:'USD',wishlist_id:11})});
});
