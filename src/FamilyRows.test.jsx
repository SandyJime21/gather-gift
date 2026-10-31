import {expect,it} from 'vitest';
import {render,screen,within} from '@testing-library/react';
import FamilyRows from './FamilyRows.jsx';
it('keeps everyone together with you first and pets at the end',()=>{
 const profiles=[{id:1,display_name:'Mochi',profile_type:'pet'},{id:2,display_name:'Child',profile_type:'person'},{id:3,display_name:'Me',is_me:true,profile_type:'person'}];
 render(<FamilyRows profiles={profiles} renderMember={p=><a href={'/profiles/'+p.id}>{p.display_name}</a>}/>);
 const family=screen.getByRole('region',{name:'Family members'});
 expect(within(family).getAllByRole('link').map(a=>a.textContent)).toEqual(['Me','Child','Mochi']);
 expect(screen.queryByRole('region',{name:'Family pets'})).not.toBeInTheDocument();
});
