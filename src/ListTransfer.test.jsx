import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import ListTransfer from './ListTransfer.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
it('copies before deletion and explains skipped duplicates without deleting the source',async()=>{
 api.mockImplementation(async(path,options)=>options?.method==='POST'?{transferred:2,skipped:1,already_present:0,remaining:3}:{wishlists:[{id:12,title:'Christmas'}]});
 render(<ListTransfer list={{id:11,title:'Birthday'}} inline/>);
 fireEvent.click(screen.getByRole('button',{name:'Move / copy gifts'}));
 expect(await screen.findByRole('option',{name:'Christmas'})).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Action'),{target:{value:'copy'}});
 fireEvent.click(screen.getByRole('button',{name:'Copy gifts'}));
 expect(await screen.findByRole('status')).toHaveTextContent('1 name/link matches skipped and kept in the original list');
 expect(api).toHaveBeenCalledWith('/wishlists/11/transfer',{method:'POST',body:JSON.stringify({wishlist_id:12,mode:'copy'})});
 expect(api.mock.calls.some(([,options])=>options?.method==='DELETE')).toBe(false);
});
