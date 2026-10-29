import {afterEach,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {AdvertisingInquiryForm,AdvertisingAlertSettings,AdvertisingRequestInbox} from './AdvertisingRequests.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());

it('sends an advertising inquiry to the portal rather than opening a mail draft',async()=>{
 api.mockResolvedValue({request_id:1,message:'Your advertising request has been sent to our team.'});
 render(<AdvertisingInquiryForm/>);
 for(const [label,value] of [['Your name','Alex'],['Your email','alex@example.com'],['Business or brand (optional)','Gift shop'],['Advertising request','I would like to advertise a holiday sale.']])fireEvent.change(screen.getByLabelText(label),{target:{value}});
 fireEvent.click(screen.getByRole('button',{name:'Send advertising request'}));
 expect(await screen.findByText('Your advertising request has been sent to our team.')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/ads/requests',{method:'POST',body:JSON.stringify({name:'Alex',email:'alex@example.com',business_name:'Gift shop',message:'I would like to advertise a holiday sale.'})});
 expect(screen.getByLabelText('Your email')).toHaveValue('');
});

it('requires a confirmation code before enabling advertising email alerts',async()=>{
 api.mockImplementation(async(path)=>{
  if(path==='/support/advertising-alerts')return {settings:{},mail_available:true};
  if(path.endsWith('/verify-email'))return {challenge_id:'challenge-1',message:'Code sent.'};
  if(path.endsWith('/confirm-email'))return {settings:{name:'Sandra',email:'alerts@example.com',verified_at:'2026-10-27',enabled:true},message:'Notification email confirmed.'};
  throw Error(path);
 });
 render(<AdvertisingAlertSettings/>);
 const toggle=await screen.findByRole('checkbox',{name:'Email me new advertising requests and campaign submissions'});
 expect(toggle).toBeDisabled();expect(toggle).not.toBeChecked();
 fireEvent.change(screen.getByLabelText('Notification recipient name'),{target:{value:'Sandra'}});
 fireEvent.change(screen.getByLabelText('Advertising notification email'),{target:{value:'alerts@example.com'}});
 fireEvent.click(screen.getByRole('button',{name:'Send confirmation code'}));
 fireEvent.change(await screen.findByLabelText('Confirmation code'),{target:{value:'123456'}});
 expect(toggle).not.toBeChecked();
 fireEvent.click(screen.getByRole('button',{name:'Confirm notification email'}));
 await screen.findByText('Notification email confirmed.');
 expect(toggle).toBeChecked();expect(toggle).not.toBeDisabled();
 expect(api).toHaveBeenCalledWith('/support/advertising-alerts/confirm-email',{method:'POST',body:JSON.stringify({challenge_id:'challenge-1',email:'alerts@example.com',code:'123456'})});
});

it('keeps requests visible even when the email alert failed and lets the developer review them',async()=>{
 let status='new';
 api.mockImplementation(async(path,options)=>{
  if(path==='/support/advertising-requests')return {new_count:status==='new'?1:0,requests:[{id:7,name:'Alex',email:'alex@example.com',business_name:'Gift shop',message:'Please contact me about ads.',status,email_delivery:'failed',created_at:'2026-10-27T12:00:00Z'}]};
  if(path==='/support/advertising-requests/7'){status=JSON.parse(options.body).status;return {};}
 });
 render(<MemoryRouter initialEntries={['/support?advertising_request=7']}><AdvertisingRequestInbox/></MemoryRouter>);
 expect(await screen.findByText('Please contact me about ads.')).toBeInTheDocument();
 expect(screen.getByText('1 new advertising request')).toBeInTheDocument();
 expect(screen.getByText(/Email delivery failed/)).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Status for advertising request 7'),{target:{value:'reviewed'}});
 await waitFor(()=>expect(screen.getByText('0 new advertising requests')).toBeInTheDocument());
 expect(screen.getByText('Please contact me about ads.')).toBeInTheDocument();
});

it('explains missing server email configuration without claiming alerts are enabled',async()=>{
 api.mockResolvedValue({settings:{},mail_available:false});
 render(<AdvertisingAlertSettings/>);
 expect(await screen.findByText(/Email delivery is not configured on the server/)).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Send confirmation code'})).toBeDisabled();
});
