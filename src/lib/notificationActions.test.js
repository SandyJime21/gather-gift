import {afterEach,expect,it,vi} from 'vitest';
import {readNotification,dismissNotification} from './notificationActions.js';
import {api} from './api.js';
vi.mock('./api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
it('marks a reminder read without dismissing it',async()=>{
 await readNotification({id:'profile-completion-7',read:false});
 expect(api).toHaveBeenCalledExactlyOnceWith('/notifications/state',{method:'POST',body:JSON.stringify({id:'profile-completion-7',action:'read'})});
});
it('dismisses a price request only when Ignore is chosen',async()=>{
 await dismissNotification({id:'price-request-123'});
 expect(api).toHaveBeenCalledExactlyOnceWith('/notifications/state',{method:'POST',body:JSON.stringify({id:'price-request-123',action:'dismiss'})});
});
it('retains the existing read endpoint for purchase updates',async()=>{
 await readNotification({id:12,read:false});
 expect(api).toHaveBeenCalledExactlyOnceWith('/notifications/12/read',{method:'POST',body:JSON.stringify({})});
});
