import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import ChildAccessControls from './ChildAccessControls.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
it('shows disabled-by-default activities and saves explicit parental approval',async()=>{
 api.mockReset();
 const controls={web_search:false,product_links:false,manage_pets:false,switch_siblings:false,game_invites:false};
 api.mockResolvedValueOnce({available:true,controls}).mockResolvedValueOnce({available:true,controls:{...controls,web_search:true}});
 render(<ChildAccessControls profileId={2}/>);
 fireEvent.click(screen.getByText('Child access · parent approval'));
 const search=await screen.findByLabelText('Search online for gifts');
 expect(search).not.toBeChecked();
 expect(screen.getAllByRole('switch')).toHaveLength(5);
 fireEvent.click(search);
 await waitFor(()=>expect(search).toBeChecked());
 expect(api).toHaveBeenLastCalledWith('/profiles/2/child-controls',{method:'PATCH',body:JSON.stringify({web_search:true})});
 expect(screen.getByLabelText('Add product links')).not.toBeChecked();
});
