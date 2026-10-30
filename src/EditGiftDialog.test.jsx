import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import EditGiftDialog from './EditGiftDialog.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
it('edits real item details without clearing the existing photo',async()=>{
 api.mockResolvedValue({});const close=vi.fn();
 render(<EditGiftDialog item={{id:8,name:'Old name',description:'Old notes',image_path:'/api/uploads/photo.jpg',estimated_price:'12.50'}} onClose={close}/>);
 fireEvent.change(await screen.findByLabelText('Gift name'),{target:{value:'New name'}});
 fireEvent.change(screen.getByLabelText('Additional notes'),{target:{value:'Blue, size small'}});
 fireEvent.click(screen.getByRole('button',{name:'Save gift'}));
 await waitFor(()=>expect(close).toHaveBeenCalled());
 const [path,options]=api.mock.calls.at(-1),payload=JSON.parse(options.body);
 expect(path).toBe('/items/8');expect(payload).toMatchObject({name:'New name',description:'Blue, size small',estimated_price:'12.50'});
 expect(payload).not.toHaveProperty('image_url');
});
