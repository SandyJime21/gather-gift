import {fireEvent,render,screen} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import MoveGiftList from './MoveGiftList.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
it('offers only this members lists and moves the selected gift',async()=>{
 api.mockImplementation(async(path,options)=>options?.method==='POST'?{list_title:'Christmas'}:{wishlists:[{id:12,title:'Christmas'}]});
 render(<MoveGiftList item={{id:7,profile_id:3,recipient:'Mia',can_edit:true}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Move to another list'}));
 await screen.findByRole('option',{name:'Christmas'});
 fireEvent.click(screen.getByRole('button',{name:'Move gift'}));
 expect(await screen.findByText('Moved to Christmas.')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/profiles/3/wishlists');
 expect(api).toHaveBeenCalledWith('/items/7/move-list',{method:'POST',body:JSON.stringify({wishlist_id:12})});
});
it('does not offer move to a follower',()=>{
 render(<MoveGiftList item={{id:7,can_edit:false}}/>);
 expect(screen.queryByRole('button')).not.toBeInTheDocument();
});
