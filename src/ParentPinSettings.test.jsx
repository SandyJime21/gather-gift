import {fireEvent,render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import ParentPinSettings from './ParentPinSettings.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
it('saves the household PIN directly without requiring a child or list',async()=>{
 api.mockResolvedValue({status:'saved'});
 render(<ParentPinSettings/>);
 fireEvent.change(screen.getByLabelText('Parent PIN'),{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Confirm parent PIN'),{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Your account password'),{target:{value:'parent-password'}});
 fireEvent.click(screen.getByRole('button',{name:'Save parent PIN'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Parent PIN saved');
 expect(api).toHaveBeenCalledExactlyOnceWith('/household-session/pin',{method:'POST',body:JSON.stringify({pin:'123456',password:'parent-password'})});
 expect(screen.getByLabelText('Parent PIN')).toHaveValue('');
 expect(screen.getByLabelText('Your account password')).toHaveValue('');
});
it('rejects mismatched PINs before saving',async()=>{
 render(<ParentPinSettings/>);
 fireEvent.change(screen.getByLabelText('Parent PIN'),{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Confirm parent PIN'),{target:{value:'654321'}});
 fireEvent.change(screen.getByLabelText('Your account password'),{target:{value:'parent-password'}});
 fireEvent.click(screen.getByRole('button',{name:'Save parent PIN'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('The PINs must match');
 expect(api).not.toHaveBeenCalled();
});
