import {fireEvent,render,screen,within} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {expect,it,vi} from 'vitest';
import {DemoRegistry,PublicInfo} from './PublicInfo.jsx';
import CommerceAdmin from './CommerceAdmin.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
it('keeps demo reservations and wishes local without contacting account APIs',async()=>{
 render(<MemoryRouter><DemoRegistry/></MemoryRouter>);
 fireEvent.click(screen.getAllByRole('button',{name:'Reserve demo gift'})[0]);
 expect(screen.getByText('Reserved in demo')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Mark demo purchased'}));
 expect(screen.getByText('Purchased in demo')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Try adding a demo wish'}));
 const dialog=await screen.findByRole('dialog');
 fireEvent.change(within(dialog).getByLabelText('Demo gift name'),{target:{value:'My sample gift'}});
 fireEvent.click(within(dialog).getByRole('button',{name:'Add demo wish'}));
 expect(await screen.findByText('My sample gift')).toBeInTheDocument();
 expect(api).not.toHaveBeenCalled();
});
it('explains that shopping works without store approval',()=>{
 render(<MemoryRouter><PublicInfo page="disclosure"/></MemoryRouter>);
 expect(screen.getByText(/A store link still works/)).toBeInTheDocument();
});
it('shows real click counts without claiming earnings and warns before migrations',async()=>{
 api.mockResolvedValue({schema_ready:false,providers:[],outbound:[{provider:'direct',merchant:'shop.example',outbound_events:3}],reporting_message:'No conversion reporting.'});
 render(<CommerceAdmin/>);
 expect(await screen.findByText(/Commerce storage is not installed/)).toBeInTheDocument();
 expect(screen.getAllByText('Not connected')).toHaveLength(2);
 expect(screen.getAllByText('3')).toHaveLength(2);
});
