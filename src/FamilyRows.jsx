export default function FamilyRows({profiles=[],renderMember}) {
 const people=profiles.filter(p=>p.profile_type!=='pet').sort((a,b)=>Number(Boolean(b.is_you || b.is_me))-Number(Boolean(a.is_you || a.is_me)));
 const pets=profiles.filter(p=>p.profile_type==='pet');
 return <div className="family-member-rows">{people.length>0 && <section aria-label="Family members" className="mb-4"><h3 className="fs-6">Family members</h3><div className="family-people-row">{people.map(p=><div className="family-member-cell" key={p.household_id+':'+p.id}>{renderMember(p)}</div>)}</div></section>}{pets.length>0 && <section aria-label="Family pets" className="mb-4"><h3 className="fs-6">Pets</h3><div className="family-pets-row">{pets.map(p=><div className="family-member-cell" key={p.household_id+':'+p.id}>{renderMember(p)}</div>)}</div></section>}</div>;
}
