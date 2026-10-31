import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import GiftItemAction from './GiftItemAction.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
it('opens the managed gift editor directly and saves that item',async()=>{
 api.mockResolvedValue({});render(<GiftItemAction item={{id:8,name:'Puzzle',can_edit:true}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Edit gift'}));
 expect(await screen.findByLabelText('Gift name')).toHaveValue('Puzzle');
 fireEvent.click(screen.getByRole('button',{name:'Save gift'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/items/8',expect.objectContaining({method:'PATCH'})));
});
it('uses the owner personal-wish editor endpoint',async()=>{
 api.mockResolvedValue({});render(<GiftItemAction item={{id:8,name:'Book',can_edit:true,personal_wish_id:12}}/>);
 fireEvent.click(screen.getByRole('button',{name:'Edit gift'}));
 fireEvent.click(await screen.findByRole('button',{name:'Save gift'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/personal-wishes/12',expect.objectContaining({method:'PATCH'})));
});
it('shows only this gift details for another persons gift',async()=>{
 render(<GiftItemAction item={{id:9,name:'Toy',description:'Blue edition',can_edit:false}}/>);
 fireEvent.click(screen.getByRole('button',{name:'View gift'}));
 expect(await screen.findByText('Blue edition')).toBeInTheDocument();
 expect(screen.queryByLabelText('Gift name')).not.toBeInTheDocument();
 expect(screen.queryByRole('link',{name:'View wish'})).not.toBeInTheDocument();
});
