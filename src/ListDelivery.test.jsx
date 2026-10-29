import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {ListDelivery,GiftDelivery} from './ListDelivery.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('saves address privately unless sharing is enabled',async()=>{
 api.mockResolvedValue({address:null,shared:false,can_edit:true});
 render(<ListDelivery listId={3}/>);
 fireEvent.click(await screen.findByText('Delivery address'));
 fireEvent.change(screen.getByLabelText('Recipient and delivery address (optional)'),{target:{value:'Recipient, 123 Example St'}});
 expect(screen.getByRole('checkbox')).not.toBeChecked();
 fireEvent.click(screen.getByRole('button',{name:'Save address'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/wishlists/3/delivery',{method:'PATCH',body:JSON.stringify({address:'Recipient, 123 Example St',shared:false})}));
});
it('copies a shared address for store checkout',async()=>{
 const copy=vi.fn().mockResolvedValue();Object.defineProperty(navigator,'clipboard',{value:{writeText:copy},configurable:true});
 api.mockResolvedValue({addresses:[{list:'Birthday',address:'123 Example St'}]});
 render(<GiftDelivery itemId={7}/>);
 fireEvent.click(screen.getByRole('button',{name:'Delivery address'}));
 fireEvent.click(await screen.findByRole('button',{name:'Copy address'}));
 expect(copy).toHaveBeenCalledWith('123 Example St');
 expect(await screen.findByRole('button',{name:'Copied'})).toBeInTheDocument();
});
