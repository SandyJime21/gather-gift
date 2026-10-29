import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import FollowRequestActions from './FollowRequestActions.jsx';
import { api } from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
it.each([['Accept','/invitations/accept',{invitation_id:7}],['Decline','/invitations/7/decline',{}]])('responds directly with %s',async(label,path,body)=>{
 api.mockResolvedValue({});const changed=vi.fn();render(<FollowRequestActions invitationId={7} onChanged={changed}/>);
 fireEvent.click(screen.getByRole('button',{name:label}));
 await vi.waitFor(()=>expect(changed).toHaveBeenCalledOnce());
 expect(api).toHaveBeenCalledWith(path,{method:'POST',body:JSON.stringify(body)});
});
it('keeps the actions available when a request fails',async()=>{
 api.mockRejectedValue(new Error('Request no longer available.'));const changed=vi.fn();render(<FollowRequestActions invitationId={7} onChanged={changed}/>);
 fireEvent.click(screen.getByRole('button',{name:'Accept'}));
 expect(await screen.findByText('Request no longer available.')).toBeInTheDocument();
 expect(changed).not.toHaveBeenCalled();
 expect(screen.getByRole('button',{name:'Decline'})).not.toBeDisabled();
});
