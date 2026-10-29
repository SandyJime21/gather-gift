import {expect,it,vi} from 'vitest';
import {render,screen,fireEvent} from '@testing-library/react';
import {GiftGuide,ProfileCompletion,ProfilePreferencesFields,preferencePayload,calculateProfileCompletion,DiscoverGiftProfile} from './ProfilePreferences.jsx';

it('does not request a photo already present, even with an old completion result',()=>{
 render(<ProfileCompletion profile={{display_name:'Mia',photo_path:'/mia.jpg',is_adult:false,completion:{percent:0,missing:['Photo','Birthday']}}}/>);
 expect(screen.getByText('Your profile picture is added. Remaining details:')).toBeInTheDocument();
 expect(screen.getByRole('list',{name:'Missing profile details'})).not.toHaveTextContent('Photo');
});

it('counts a custom avatar as a profile picture while leaving generic placeholders incomplete',()=>{
 expect(calculateProfileCompletion({avatar_key:'cat'}).missing).not.toContain('Photo');
 expect(calculateProfileCompletion({avatar_key:'a12'}).missing).not.toContain('Photo');
 expect(calculateProfileCompletion({avatar_key:'flower'}).missing).toContain('Photo');
 expect(calculateProfileCompletion({profile_type:'pet',avatar_key:'paw'}).missing).toContain('Photo');
});

it('separates adult top and bottom sizes while preserving existing sizes',()=>{
 const onChange=vi.fn();
 const profile={is_adult:true,clothing_sizes:{Shirt:'M',Pants:'8',Dress:'10'}};
 const {rerender}=render(<ProfilePreferencesFields profile={profile} onChange={onChange}/>);
 expect(screen.getByLabelText('Top size')).toHaveValue('M');
 expect(screen.getByLabelText('Bottom size')).toHaveValue('8');
 expect(screen.getByLabelText('Other clothing sizes')).toHaveValue('Dress: 10');
 fireEvent.change(screen.getByLabelText('Top size'),{target:{value:'L'}});
 const updated=onChange.mock.lastCall[0];
 expect(updated.clothing_sizes).toEqual({top:'L',Pants:'8',Dress:'10'});
 rerender(<ProfilePreferencesFields profile={updated} onChange={onChange}/>);
 fireEvent.change(screen.getByLabelText('Bottom size'),{target:{value:'12'}});
 expect(onChange.mock.lastCall[0].clothing_sizes).toEqual({top:'L',bottom:'12',Dress:'10'});
});

it('shows sizes, stores, favorites and allergies to gift shoppers without private parent notes',()=>{
 render(<GiftGuide name="Alex" profile={{clothing_sizes:{shirt:'M'},shoe_sizes:{US:'7'},favorite_colors:['Pink'],favorite_brands:['Favorite brand'],favorite_stores:['Favorite shop'],favorite_characters:['Minnie Mouse'],allergies:'Peanuts',parent_notes:'Secret parent note',items_to_avoid:'Private notes'}} compact/>);
 expect(screen.getByText('Gift guide for Alex')).toBeInTheDocument();
 for(const text of ['shirt: M','US: 7','Pink','Favorite brand','Favorite shop','Minnie Mouse','Peanuts'])expect(screen.getByText(text)).toBeInTheDocument();
 expect(screen.queryByText('Secret parent note')).not.toBeInTheDocument();expect(screen.queryByText('Private notes')).not.toBeInTheDocument();
});

it('distinguishes an unknown allergy status from none known',()=>{
 const view=render(<GiftGuide profile={{}}/>);
 expect(screen.getByText(/Not provided. Ask/)).toBeInTheDocument();
 view.rerender(<GiftGuide profile={{allergies:'None known'}}/>);
 expect(screen.getByText('None known')).toBeInTheDocument();
 expect(screen.queryByText(/Not provided. Ask/)).not.toBeInTheDocument();
});

it('shows completion percentage and exactly what remains',()=>{
 render(<ProfileCompletion profile={{display_name:'Alex',completion:{percent:0,missing:['Photo','Birthday','Allergies or none known']}}}/>);
 expect(screen.getByText("Alex's gift profile: 0% complete")).toBeInTheDocument();
 expect(screen.getByText(/Still to add: Photo, Birthday, Allergies/)).toBeInTheDocument();
 expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','0');
});

it('lets a parent enter current favorites and sizes without losing typed commas',()=>{
 const onChange=vi.fn();render(<ProfilePreferencesFields profile={{is_adult:false}} onChange={onChange}/>);
 const interests=screen.getByLabelText('What are they into right now?');
 fireEvent.change(interests,{target:{value:'Minnie Mouse,'}});expect(interests).toHaveValue('Minnie Mouse,');
 fireEvent.change(interests,{target:{value:'Minnie Mouse, painting'}});
 expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({interests:['Minnie Mouse','painting']}));
 fireEvent.change(screen.getByLabelText('Clothing sizes'),{target:{value:'Shirt: 5T, Pants: 4T'}});
 expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({clothing_sizes:{Shirt:'5T',Pants:'4T'}}));
});

it('offers a shorter pet editor without human clothing and shoe sizes',()=>{
 render(<ProfilePreferencesFields profile={{profile_type:'pet'}} onChange={()=>{}}/>);
 expect(screen.getByLabelText('Favorite treats or toys')).toBeInTheDocument();
 expect(screen.queryByLabelText('Clothing sizes')).not.toBeInTheDocument();expect(screen.queryByLabelText('Shoe sizes')).not.toBeInTheDocument();
 expect(preferencePayload({allergies:'None known'})).toMatchObject({allergies:'None known',favorite_brands:[],clothing_sizes:{}});
});


it('updates completion while editing instead of showing a stale saved percentage',()=>{
 const view=render(<ProfileCompletion profile={{display_name:'Alex',is_adult:true,completion:{percent:90,missing:[]}}} live/>);
 expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','0');
 view.rerender(<ProfileCompletion profile={{display_name:'Alex',is_adult:true,photo_path:'/photo.jpg',allergies:'None known',completion:{percent:90,missing:[]}}} live/>);
 expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','20');
 expect(calculateProfileCompletion({is_adult:false}).total).toBeLessThan(calculateProfileCompletion({is_adult:true}).total);
 expect(calculateProfileCompletion({profile_type:'pet'}).missing).not.toContain('Clothing size');
});

it('keeps sizes and allergy notes visible on gift cards without expanding more favorites',()=>{
 render(<GiftGuide name="Mia" profile={{clothing_sizes:{shirt:'5T'},shoe_sizes:{US:'11'},favorite_colors:['Pink'],favorite_brands:['Favorite brand'],favorite_stores:['Favorite shop'],allergies:'Peanuts'}} compact/>);
 for(const text of ['shirt: 5T','US: 11','Pink','Favorite brand','Favorite shop','Peanuts'])expect(screen.getByText(text).closest('details')).toBeNull();
 expect(screen.getByText('More favorites & gift ideas').closest('details')).not.toHaveAttribute('open');
});

it('makes Discover profile cards show existing favorites and a completion action',()=>{
 render(<DiscoverGiftProfile profile={{display_name:'Mia',preferences:{favorite_characters:['Minnie Mouse'],favorite_colors:['Pink'],favorite_brands:['Favorite brand']},completion:{percent:0,completed:0,total:7,missing:['Photo','Birthday']}}}><button>Complete gift profile</button></DiscoverGiftProfile>);
 for(const text of ['Minnie Mouse','Pink','Favorite brand'])expect(screen.getByText(text)).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Complete gift profile'})).toBeInTheDocument();
 expect(screen.queryByText('0 of 7 details added')).not.toBeInTheDocument();
});
