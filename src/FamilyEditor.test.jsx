import { afterEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import FamilyEditor from './FamilyEditor.jsx';
import { api } from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:p=>p}));
vi.mock('./PhotoCropper.jsx',()=>({usePhotoCrop:()=>({crop:async file=>file || null,cropper:null})}));
afterEach(()=>vi.clearAllMocks());
it.each([false,true])('lets the family creator set or change a PIN inside a child profile, existing PIN: %s',async hasPin=>{
 const home={id:1,name:'Family',role:'owner',registry_type:'family'};
 const member={id:7,display_name:'Mia',profile_type:'person',is_adult:false,can_edit:true};
 api.mockImplementation(async(path)=>{
  if(path==='/household-session/switch')return {};
  if(path==='/households/1')return {household:home,profiles:[member]};
  if(path==='/profiles/7/child-controls')return {has_parent_pin:hasPin,enabled:false,controls:{},wishlists:[],wishlist_ids:[]};
  if(path==='/household-session/pin')return {status:'saved'};
  throw Error(path);
 });
 render(<FamilyEditor households={[home]} member={member} label="Mia" refresh={async()=>{}} BirthdayInput={()=>null} RelationshipSelect={()=>null}/>);
 fireEvent.click(screen.getByRole('button',{name:'Mia Parent managed'}));
 fireEvent.click(await screen.findByRole('button',{name:'Set parent PIN / child access'}));
 const pin=await screen.findByLabelText('Parent PIN');
 expect(screen.getAllByRole('dialog')).toHaveLength(1);
 expect(pin).toBeVisible();expect(pin).toBeEnabled();
 fireEvent.change(pin,{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Confirm parent PIN'),{target:{value:'123456'}});
 fireEvent.change(screen.getByLabelText('Your account password'),{target:{value:'parent-password'}});
 fireEvent.click(screen.getByRole('button',{name:'Save parent PIN'}));
 expect(await screen.findByText('Parent PIN saved.')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/household-session/pin',{method:'POST',body:JSON.stringify({pin:'123456',password:'parent-password'})});
 expect(api).not.toHaveBeenCalledWith('/profiles/7/child-controls',expect.objectContaining({method:'PATCH'}));
});
it.each([false,true])('adds a member with details open and a photo below, retrying without duplicate profiles: %s',async retry=>{
 const home={id:1,name:'Family',role:'owner'};let profile=null,created=0,uploads=0;
 api.mockImplementation(async(path,options)=>{
  if(path==='/household-session/switch')return {};
  if(path==='/households/1')return {household:home,profiles:profile?[profile]:[]};
  if(path==='/households/1/profiles'){created++;profile={id:9,...JSON.parse(options.body),can_edit:true};return {profile};}
  if(path==='/profiles/9'&&options?.method==='PATCH'){Object.assign(profile,JSON.parse(options.body));return {profile};}
  if(path==='/households/1/profiles/9/relationship')return {};
  if(path==='/profiles/9/photo'){
   uploads++;expect(options.body.get('image').name).toBe('member.png');
   if(retry && uploads===1)throw new Error('Store unavailable');
   profile.photo_path='/api/uploads/member.png';return {photo_path:profile.photo_path};
  }
  return {};
 });
 render(<FamilyEditor households={[home]} refresh={async()=>{}} BirthdayInput={()=>null} RelationshipSelect={()=>null} initialHome="1" initialPerson="new" label="Add member"/>);
 fireEvent.click(screen.getByRole('button',{name:'Add member'}));
 const name=await screen.findByLabelText('Member name');
 const details=name.closest('details');expect(details).toHaveAttribute('open');
 const photo=screen.getByLabelText('Add profile photo');
 expect(details.compareDocumentPosition(photo)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
 fireEvent.change(name,{target:{value:'Mia'}});
 expect(screen.getByRole('button',{name:'Photo'})).toBeInTheDocument();
 fireEvent.change(photo,{target:{files:[new File(['photo'],'member.png',{type:'image/png'})]}});
 await waitFor(()=>expect(photo).toHaveValue(''));
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Photo'})).not.toBeInTheDocument());
 fireEvent.click(screen.getByRole('button',{name:'Save changes'}));
 if(retry){await screen.findByText(/Profile saved, but the photo could not be uploaded/);fireEvent.click(screen.getByRole('button',{name:'Save changes'}));}
 await screen.findByText('Saved.');
 expect(created).toBe(1);expect(uploads).toBe(retry?2:1);
});
it('edits family and member names in the same dialog',async()=>{
 const home={id:1,name:'Old family',role:'owner'},person={id:7,display_name:'Alex',profile_type:'person',relationship:'dad',can_edit:true};
 api.mockImplementation(async(path,options)=>{
  if(path==='/household-session/switch')return {};
  if(path==='/households/1' && !options)return {household:home,profiles:[person]};
  if(path==='/households/1' && options){home.name=JSON.parse(options.body).name;return {};}
  if(path==='/profiles/7'){person.display_name=JSON.parse(options.body).display_name;return {};}
  if(path==='/households/1/profiles/7/relationship')return {};
  throw new Error(path);
 });
 render(<FamilyEditor households={[home]} refresh={async()=>{}} BirthdayInput={()=>null} RelationshipSelect={()=>null} ChildManager={()=>null}/>);
 fireEvent.click(screen.getByRole('button',{name:'Edit profiles & family'}));
 fireEvent.change(await screen.findByLabelText('Family name'),{target:{value:'New family'}});
 fireEvent.click(screen.getByRole('button',{name:'Save changes'}));
 await screen.findByText('Saved.');
 fireEvent.change(screen.getByLabelText('What would you like to edit?'),{target:{value:'7'}});
 fireEvent.change(screen.getByLabelText('Member name'),{target:{value:'Alex updated'}});
 fireEvent.click(screen.getByRole('button',{name:'Save changes'}));
 await screen.findByText('Saved.');
 expect(person.display_name).toBe('Alex updated');
 expect(screen.getAllByRole('dialog')).toHaveLength(1);
});

it('opens the selected member directly and explains locked adults',async()=>{
 const home={id:1,name:'Family',role:'owner'};
 const profile={id:7,display_name:'Alex',is_adult:true,can_edit:true};
 api.mockImplementation(async path=>path==='/households/1'?{household:home,profiles:[profile]}:{});
 const props={households:[home],refresh:async()=>{},BirthdayInput:()=>null,RelationshipSelect:()=>null,ChildManager:()=>null};
 const view=render(<FamilyEditor {...props} initialHome="1" initialPerson="7" label="Alex"/>);
 fireEvent.click(screen.getByRole('button',{name:'Alex'}));
 expect(await screen.findByLabelText('Member name')).toHaveValue('Alex');
 view.unmount();
 render(<FamilyEditor {...props} label="Alex" disabled disabledReason="Alex must edit their information."/>);
 expect(screen.getByRole('button',{name:'Alex'})).toBeDisabled();
 expect(screen.getByTitle('Alex must edit their information.')).toBeInTheDocument();
});

it('offers an email invitation in the selected adult editor without another person picker',async()=>{
 const home={id:1,name:'Family',role:'owner'};
 const profile={id:7,display_name:'Alex',is_adult:true,can_edit:true,has_login:false};
 api.mockImplementation(async path=>path==='/households/1'?{household:home,profiles:[profile]}:path==='/households/1/adult-invitations'?{email_message:{delivery:'sent'}}:{});
 render(<FamilyEditor households={[home]} refresh={async()=>{}} BirthdayInput={()=>null} RelationshipSelect={()=>null} ChildManager={()=>null} initialHome="1" initialPerson="7" label="Alex"/>);
 fireEvent.click(screen.getByRole('button',{name:'Alex'}));
 fireEvent.change(await screen.findByLabelText('Email address'),{target:{value:'alex@example.com'}});
 expect(screen.queryByLabelText('What would you like to edit?')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Invite to join family'}));
 expect(await screen.findByText('Invitation sent.')).toBeInTheDocument();
 expect(api).toHaveBeenCalledWith('/households/1/adult-invitations',expect.objectContaining({body:JSON.stringify({profile_id:7,email:'alex@example.com'})}));
});


it('shows the saved pet photo and lets the owner remove the pet without login controls',async()=>{
 const home={id:1,name:'Family',role:'owner'};
 const pet={id:8,display_name:'Mochi',profile_type:'pet',photo_path:'/api/uploads/mochi.jpg',can_edit:true,can_remove_from_family:true};
 api.mockImplementation(async path=>path==='/households/1'?{household:home,profiles:[pet]}:{});
 render(<FamilyEditor households={[home]} refresh={async()=>{}} BirthdayInput={()=>null} RelationshipSelect={()=>null} ChildManager={()=>null} initialHome="1" initialPerson="8" label="Mochi"/>);
 fireEvent.click(screen.getByRole('button',{name:'Mochi'}));
 await screen.findByLabelText('Member name');
 expect(document.querySelector('img[src="/api/uploads/mochi.jpg"]')).toBeInTheDocument();
 expect(screen.queryByLabelText('Adult (18+)')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Remove from family'}));
 fireEvent.click(screen.getByRole('button',{name:'Remove member'}));
 expect(api).toHaveBeenCalledWith('/households/1/profiles/8/member',{method:'DELETE'});
});


it('saves parent-managed child favorites, snacks, sizes and allergies together',async()=>{
 const home={id:1,name:'Family',role:'owner'};
 const child={id:8,display_name:'Mia',profile_type:'person',is_adult:false,can_edit:true};
 let payload;
 api.mockImplementation(async(path,options)=>{
  if(path==='/households/1')return {household:home,profiles:[child]};
  if(path==='/profiles/8'&&options?.method==='PATCH'){payload=JSON.parse(options.body);Object.assign(child,payload);return {profile:child};}
  return {};
 });
 render(<FamilyEditor households={[home]} refresh={async()=>{}} BirthdayInput={()=>null} RelationshipSelect={()=>null} initialHome="1" initialPerson="8" label="Mia"/>);
 fireEvent.click(screen.getByRole('button',{name:'Mia'}));
 fireEvent.change(await screen.findByLabelText('What are they into right now?'),{target:{value:'Minnie Mouse, painting'}});
 fireEvent.change(screen.getByLabelText('Favorite colors'),{target:{value:'Pink'}});
 fireEvent.change(screen.getByLabelText('Favorite snacks'),{target:{value:'Apples'}});
 fireEvent.change(screen.getByLabelText('Clothing sizes'),{target:{value:'Shirt: 5T'}});
 fireEvent.change(screen.getByLabelText('Shoe sizes'),{target:{value:'US: 11'}});
 fireEvent.change(screen.getByLabelText('Allergies & sensitivities'),{target:{value:'Peanuts'}});
 fireEvent.click(screen.getByRole('button',{name:'Save changes'}));
 await screen.findByText('Saved.');
 expect(payload).toMatchObject({interests:['Minnie Mouse','painting'],favorite_colors:['Pink'],favorite_snacks:['Apples'],clothing_sizes:{Shirt:'5T'},shoe_sizes:{US:'11'},allergies:'Peanuts'});
});

it('shows completion beside the profile image only on editable settings cards',()=>{
 const member={id:7,display_name:'Alex',can_edit:true,photo_path:'/photo.jpg',completion:{percent:40}};
 const props={households:[{id:1,role:'owner'}],refresh:async()=>{},member,showCompletion:true};
 const view=render(<FamilyEditor {...props}/>);
 expect(screen.getByText('40%')).toBeInTheDocument();
 expect(screen.getByRole('progressbar',{name:'Alex profile complete'})).toHaveAttribute('value','40');
 view.rerender(<FamilyEditor {...props} member={{...member,can_edit:false}}/>);
 expect(screen.queryByText('40%')).not.toBeInTheDocument();
});

it('opens a member directly and highlights missing details until they are filled',async()=>{
 const home={id:1,name:'Family',role:'owner'};
 const member={id:7,display_name:'Alex',can_edit:true,is_adult:true,profile_type:'person',photo_path:'/photo.jpg',birthday:'2000-01-01'};
 api.mockImplementation(async path=>path==='/household-session/switch'?{}:{household:home,profiles:[member]});
 render(<FamilyEditor households={[home]} member={member} label="Alex" refresh={async()=>{}} BirthdayInput={()=>null} RelationshipSelect={()=>null}/>);
 fireEvent.click(screen.getByRole('button',{name:'Alex'}));
 const allergy=await screen.findByLabelText('Allergies & sensitivities');
 const before=Number(screen.getByRole('progressbar',{name:'Alex profile complete'}).getAttribute('value'));
 expect(screen.getByRole('progressbar',{name:'Alex profile complete'}).closest('[title]')).toHaveAttribute('title',expect.stringContaining('Allergies or none known'));
 expect(screen.queryByLabelText('What would you like to edit?')).not.toBeInTheDocument();
 expect(allergy.closest('.mb-3')).toHaveClass('completion-field-missing');
 fireEvent.click(screen.getByRole('button',{name:'Allergies or none known'}));
 expect(allergy).toHaveFocus();
 fireEvent.change(allergy,{target:{value:'None known'}});
 expect(Number(screen.getByRole('progressbar',{name:'Alex profile complete'}).getAttribute('value'))).toBeGreaterThan(before);
 expect(screen.getByRole('progressbar',{name:'Alex profile complete'}).closest('[title]').title).not.toContain('Allergies or none known');
 expect(allergy.closest('.mb-3')).not.toHaveClass('completion-field-missing');
 expect(screen.queryByRole('button',{name:'Allergies or none known'})).not.toBeInTheDocument();
});
