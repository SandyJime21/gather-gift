import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {beforeEach,expect,it,vi} from 'vitest';
import DeleteAccount,{AccountDeletedPage} from './DeleteAccount.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
const preview={confirmation_token:'preview-token',families:[{id:9,name:'Our Family',action:'transfer',successor:{id:2,name:'Alex'},children:2,pets:1}],children:[]};
beforeEach(()=>api.mockReset());
it('previews the named successor and defaults final focus to No without deleting',async()=>{
 api.mockResolvedValue(preview);const deleted=vi.fn();
 render(<MemoryRouter><DeleteAccount onDeleted={deleted}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'Delete account'}));
 expect(await screen.findByText('Ownership will transfer to Alex.')).toBeInTheDocument();
 expect(screen.getByText(/remove that adult from the family/)).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Current password'),{target:{value:'a-password'}});
 fireEvent.click(screen.getByRole('button',{name:'Continue to final confirmation'}));
 const no=screen.getByRole('button',{name:'No, keep my account'});
 expect(no).toHaveFocus();
 const yes=screen.getByRole('button',{name:'Yes, delete my account'});
 expect(yes.compareDocumentPosition(no)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 fireEvent.click(no);
 expect(api).toHaveBeenCalledTimes(1);expect(deleted).not.toHaveBeenCalled();
});
it('only deletes after the second explicit confirmation and includes the reviewed token',async()=>{
 api.mockImplementation(async(path)=>path==='/auth/account-deletion'?preview:{status:'deleted'});
 const deleted=vi.fn();render(<MemoryRouter><DeleteAccount onDeleted={deleted}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'Delete account'}));
 const password=await screen.findByLabelText('Current password');
 fireEvent.change(password,{target:{value:'current-password'}});
 fireEvent.click(screen.getByRole('button',{name:'Continue to final confirmation'}));
 expect(api).toHaveBeenCalledTimes(1);
 fireEvent.click(screen.getByRole('button',{name:'Yes, delete my account'}));
 await waitFor(()=>expect(deleted).toHaveBeenCalledTimes(1));
 expect(api).toHaveBeenCalledWith('/auth/account',{method:'DELETE',body:JSON.stringify({confirmation_token:'preview-token',password:'current-password',confirm:true})});
});
it('warns explicitly when a family will be deleted because there is no successor',async()=>{
 api.mockResolvedValue({...preview,families:[{id:9,name:'Our Family',action:'delete',successor:null,children:1,pets:0}]});
 render(<MemoryRouter><DeleteAccount onDeleted={()=>{}}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'Delete account'}));
 expect(await screen.findByText('No eligible adult can take over.')).toBeInTheDocument();
 expect(screen.getByText(/This family will be permanently deleted/)).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Continue to final confirmation'})).toBeDisabled();
});

it('explains the CSV backup and prevents deletion when it cannot be emailed',async()=>{
 api.mockResolvedValue({...preview,backup_available:false,backup_email:'owner@example.com'});
 render(<MemoryRouter><DeleteAccount onDeleted={()=>{}}/></MemoryRouter>);
 fireEvent.click(screen.getByRole('button',{name:'Delete account'}));
 expect(await screen.findByText(/We cannot email your backup right now/)).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Current password'),{target:{value:'current-password'}});
 expect(screen.getByRole('button',{name:'Continue to final confirmation'})).toBeDisabled();
});
it('confirms the emailed CSV without claiming a transferred family was erased',()=>{
 render(<MemoryRouter initialEntries={[{pathname:'/account-deleted',state:{deletionConfirmed:true,backup_delivery:'sent',backup_email:'owner@example.com',family_transferred:true}}]}><AccountDeletedPage/></MemoryRouter>);
 expect(screen.getByRole('status')).toHaveTextContent('owner@example.com');
 expect(screen.getByText(/shared profiles and lists with the new owner/)).toBeInTheDocument();
});
