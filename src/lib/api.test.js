import { afterEach, expect, it, vi } from 'vitest';
import { api, clearCsrfToken } from './api.js';
afterEach(() => { clearCsrfToken(); vi.unstubAllGlobals(); });
it('explains a network failure', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
  await expect(api('/auth/me')).rejects.toThrow('Cannot connect to the server');
});
it('explains an unavailable proxy response', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ status:502, ok:false, json:async()=>{throw new Error('not JSON');} }));
  await expect(api('/auth/me')).rejects.toThrow('server is unavailable');
});
it('shares the CSRF request across concurrent writes without retrying writes', async () => {
  const fetchMock=vi.fn().mockImplementation(async url => ({ok:true,status:200,json:async()=>url.endsWith('/csrf') ? {csrf_token:'token'} : {saved:true}}));
  vi.stubGlobal('fetch',fetchMock);
  await Promise.all([api('/one',{method:'POST'}),api('/two',{method:'POST'})]);
  expect(fetchMock.mock.calls.filter(([url])=>url.endsWith('/csrf'))).toHaveLength(1);
  expect(fetchMock).toHaveBeenCalledTimes(3);
});
it('preserves HTTP status so temporary failures are distinguishable from expired sessions',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:500,json:async()=>({error:'Temporary outage'})}));
 await expect(api('/auth/me')).rejects.toMatchObject({status:500,message:'Temporary outage'});
});
it('does not replace a newly signed-in CSRF token with an older session response',async()=>{
 let finishOld;
 const old=new Promise(resolve=>{finishOld=resolve;});
 const response=data=>({ok:true,status:200,json:async()=>data});
 const mock=vi.fn(async url=>url.endsWith('/auth/me')?old:response(url.endsWith('/csrf')?{csrf_token:'guest'}:url.endsWith('/login')?{csrf_token:'signed-in'}:{saved:true}));
 vi.stubGlobal('fetch',mock);
 const stale=api('/auth/me');
 await api('/auth/login',{method:'POST',body:'{}'});
 finishOld(response({csrf_token:'stale-guest'}));await stale;
 await api('/save',{method:'POST',body:'{}'});
 expect(mock.mock.calls.at(-1)[1].headers.get('X-CSRF-Token')).toBe('signed-in');
});
