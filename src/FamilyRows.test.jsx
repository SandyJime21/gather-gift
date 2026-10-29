import {expect,it} from 'vitest';
import {render,screen,within} from '@testing-library/react';
import FamilyRows from './FamilyRows.jsx';
it('puts you with all people first and pets in their own second row',()=>{
 const profiles=[{id:1,display_name:'Mochi',profile_type:'pet'},{id:2,display_name:'Child',profile_type:'person'},{id:3,display_name:'Me',is_me:true,profile_type:'person'}];
 render(<FamilyRows profiles={profiles} renderMember={p=><a href={'/profiles/'+p.id}>{p.display_name}</a>}/>);
 const people=screen.getByRole('region',{name:'Family members'}),pets=screen.getByRole('region',{name:'Family pets'});
 expect(within(people).getAllByRole('link').map(a=>a.textContent)).toEqual(['Me','Child']);
 expect(within(pets).getAllByRole('link').map(a=>a.textContent)).toEqual(['Mochi']);
 expect(people.compareDocumentPosition(pets)&Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});
