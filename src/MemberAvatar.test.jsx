import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import MemberAvatar,{AvatarPicker} from './MemberAvatar.jsx';
import FamilyEditor from './FamilyEditor.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:p=>p}));
afterEach(()=>{cleanup();vi.clearAllMocks();});
it('shows a member photo inside one clickable card',()=>{
 const {container}=render(<FamilyEditor households={[{id:1,role:'owner'}]} member={{display_name:'Alex',photo_path:'/api/uploads/alex.jpg'}} label="Alex"/>);
 const button=screen.getByRole('button',{name:'Alex'});
 expect(button.querySelector('img')).toHaveAttribute('src','/api/uploads/alex.jpg');
 expect(container.querySelector('.card .btn')).toBeNull();
});
it('offers built-in and published cartoons',async()=>{
 api.mockResolvedValue({avatars:[{key:'a1',name:'Happy fox',image:'/api/avatars/1/art'}]});const change=vi.fn();
 render(<AvatarPicker value="cat" onChange={change}/>);
 expect(screen.getByRole('button',{name:'Cat'})).toHaveAttribute('aria-pressed','true');
 fireEvent.click(await screen.findByRole('button',{name:'Happy fox'}));
 expect(change).toHaveBeenCalledWith('a1');
});
it('falls back gracefully when a profile photo fails',()=>{
 const {container}=render(<MemberAvatar photo="/missing.jpg" avatarKey="cat"/>);
 fireEvent.error(container.querySelector('img'));
 expect(container.querySelector('img')).toBeNull();
});

it('shows a child relationship and rainbow card',()=>{
 render(<FamilyEditor households={[{id:1,role:'owner'}]} member={{display_name:'Sam',relationship:'son',is_adult:false}} label="Sam"/>);
 expect(screen.getByText('Son')).toBeInTheDocument();expect(screen.getByText('Parent managed')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:/Sam/})).toHaveClass('child-profile-card');
});
it('opens joined adult details read-only with creator removal available',async()=>{
 const home={id:1,name:'Family',role:'owner'},member={id:7,display_name:'Alex',is_adult:true,has_login:true,can_edit:false,can_remove_from_family:true,member_email:'alex@example.com'};
 api.mockImplementation(async path=>path==='/households/1'?{household:home,profiles:[member]}:path==='/avatars'?{avatars:[]}:{});
 render(<FamilyEditor households={[home]} refresh={async()=>{}} BirthdayInput={()=>null} RelationshipSelect={()=>null} ChildManager={()=>null} initialHome="1" initialPerson="7" member={member} label="Alex" disabled disabledReason="Alex must edit their information."/>);
 fireEvent.click(screen.getByRole('button',{name:/Alex/}));
 expect(await screen.findByLabelText('Member name')).toBeDisabled();
 expect(screen.getByLabelText('Account email')).toHaveValue('alex@example.com');
 expect(screen.getByLabelText('Account email')).toBeDisabled();
 expect(screen.getByRole('button',{name:'Remove from family'})).toBeEnabled();
});
