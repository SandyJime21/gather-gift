import {api} from './api.js';
export async function readNotification(row){
 if(row.read)return;
 const id=String(row.id);
 if(/^\d+$/.test(id))await api('/notifications/'+id+'/read',{method:'POST',body:JSON.stringify({})});
 else if(id.startsWith('availability-'))await api('/availability-alerts/'+id.slice(13)+'/read',{method:'POST',body:JSON.stringify({})});
 else await api('/notifications/state',{method:'POST',body:JSON.stringify({id:row.id,action:'read'})});
 window.dispatchEvent(new Event('notifications-updated'));
}
export async function dismissNotification(row){
 await api('/notifications/state',{method:'POST',body:JSON.stringify({id:row.id,action:'dismiss'})});
 window.dispatchEvent(new Event('notifications-updated'));
}
