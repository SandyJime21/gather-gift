import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import ChildGameNotifications from './ChildGameNotifications.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('shows a read-only invitation and marks it read',async()=>{
 let read=false;
 api.mockImplementation(async(path)=>{if(path.endsWith('/read')){read=true;return {status:'read'};}return {notifications:[{id:4,message:'Invited to Secret Santa',read}]};});
 render(<ChildGameNotifications/>);
 expect(await screen.findByText('Invited to Secret Santa')).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Join'})).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Mark read'}));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Mark read'})).not.toBeInTheDocument());
 expect(api).toHaveBeenCalledWith('/child/game-notifications/4/read',{method:'POST',body:'{}'});
});
