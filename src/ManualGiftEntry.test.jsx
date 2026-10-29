import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import ManualGiftEntry from './ManualGiftEntry.jsx';
it('saves an unlisted wish without requiring a product link or price',async()=>{
 const save=vi.fn().mockResolvedValue({});
 render(<ManualGiftEntry onSave={save} initialName="A day at the zoo"/>);
 fireEvent.click(screen.getByRole('button',{name:"Can't find it? Add manually"}));
 expect(screen.getByLabelText('Wish name')).toHaveValue('A day at the zoo');
 fireEvent.change(screen.getByLabelText('Description'),{target:{value:'With my family'}});
 fireEvent.click(screen.getByRole('button',{name:'Save manual wish'}));
 await waitFor(()=>expect(save).toHaveBeenCalledWith(expect.objectContaining({name:'A day at the zoo',description:'With my family',estimated_price:null,product_url:''})));
 expect(await screen.findByRole('status')).toHaveTextContent('Your wish was saved.');
});
