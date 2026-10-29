import {useState} from 'react';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {beforeEach,expect,it,vi} from 'vitest';
import PreferenceEntry from './PreferenceEntry.jsx';
import {ProfilePreferencesFields,ProfileCompletion} from './ProfilePreferences.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
beforeEach(()=>{api.mockReset();});
function ManualProfile(){const [profile,setProfile]=useState({display_name:'Alex',is_adult:true,photo_path:'/photo.jpg',birthday:'2000-01-01',allergies:'None known',clothing_sizes:{shirt:'M'},shoe_sizes:{US:'7'},favorite_colors:['Pink'],favorite_brands:['Local brand'],gift_preferences:'Books'});return <><ProfilePreferencesFields profile={profile} onChange={setProfile}/><ProfileCompletion profile={profile} live/></>;}
it('can complete the profile with manually entered stores and foods without any internet request',()=>{
 render(<ManualProfile/>);
 fireEvent.change(screen.getByLabelText('Favorite stores'),{target:{value:'My corner shop'}});
 fireEvent.change(screen.getByLabelText('Favorite snacks'),{target:{value:'Homemade cookies'}});
 expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow','100');
 expect(api).not.toHaveBeenCalled();
});
it('adds an online result without replacing manually entered favorites or adding duplicates',async()=>{
 api.mockResolvedValue({results:[{label:'Target',url:'https://en.wikipedia.org/wiki/Target_Corporation'}]});
 const changed=vi.fn();render(<PreferenceEntry field="favorite_stores" label="Favorite stores" id="stores" values={['My shop']} onChange={changed}/>);
 fireEvent.click(screen.getByRole('button',{name:'Search online for favorite stores'}));
 fireEvent.change(screen.getByLabelText('Search favorite stores'),{target:{value:'Target'}});
 fireEvent.click(screen.getByRole('button',{name:'Find options'}));
 const add=await screen.findByRole('button',{name:'Add Target'});
 expect(changed).not.toHaveBeenCalled();fireEvent.click(add);
 expect(changed).toHaveBeenLastCalledWith(['My shop','Target']);
 expect(screen.getByLabelText('Favorite stores')).toHaveValue('My shop, Target');
 expect(screen.getByRole('button',{name:'Added: Target'})).toBeDisabled();
 expect(api).toHaveBeenCalledWith('/preference-search?field=favorite_stores&q=Target');
});
it('keeps manual entry available after an online search fails',async()=>{
 api.mockRejectedValue(new Error('Online search is unavailable. Type your favorite manually; it still counts toward completion.'));
 const changed=vi.fn();render(<PreferenceEntry field="favorite_snacks" label="Favorite snacks" id="food" onChange={changed}/>);
 fireEvent.click(screen.getByRole('button',{name:'Search online for favorite snacks'}));
 fireEvent.change(screen.getByLabelText('Search favorite snacks'),{target:{value:'Cookies'}});
 fireEvent.click(screen.getByRole('button',{name:'Find options'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('still counts toward completion');
 fireEvent.change(screen.getByLabelText('Favorite snacks'),{target:{value:'Grandma cookies,'}});
 expect(screen.getByLabelText('Favorite snacks')).toHaveValue('Grandma cookies,');
 expect(changed).toHaveBeenLastCalledWith(['Grandma cookies']);
});
