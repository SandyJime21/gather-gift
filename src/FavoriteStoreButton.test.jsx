import {fireEvent,render,screen} from '@testing-library/react';
import {afterEach,expect,it,vi} from 'vitest';
import FavoriteStoreButton from './FavoriteStoreButton.jsx';
import {api} from './lib/api.js';
vi.mock('./lib/api.js',()=>({api:vi.fn()}));
afterEach(()=>vi.clearAllMocks());
it('adds a store to the person currently being shopped for',async()=>{
 api.mockResolvedValue({favorite_stores:['Target']});const refresh=vi.fn();
 render(<FavoriteStoreButton store="Target" profile={{id:7,display_name:'Mia',can_edit:true}} onSaved={refresh}/>);
 fireEvent.click(screen.getByRole('button',{name:"Add Target to Mia's favorite stores"}));
 expect(await screen.findByText('✓ Favorite store')).toBeInTheDocument();
 expect(api).toHaveBeenCalledExactlyOnceWith('/profiles/7/favorite-stores',{method:'POST',body:JSON.stringify({store:'Target'})});
 expect(refresh).toHaveBeenCalledOnce();
});
it('lets general browsing choose only a managed recipient',async()=>{
 api.mockResolvedValue({favorite_stores:['Target']});
 render(<FavoriteStoreButton store="Target" profiles={[{id:7,display_name:'Mia',can_edit:true},{id:8,display_name:'Other adult',can_edit:false}]}/>);
 fireEvent.click(screen.getByRole('button',{name:'Add Target to favorite stores'}));
 expect(screen.queryByRole('option',{name:'Other adult'})).not.toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Favorite store for'),{target:{value:'7'}});
 fireEvent.click(screen.getByRole('button',{name:'Save favorite store'}));
 expect(await screen.findByText('✓ Favorite store')).toBeInTheDocument();
 expect(api.mock.calls[0][0]).toBe('/profiles/7/favorite-stores');
});
it('does not offer edits to another adult and recognizes existing favorites',()=>{
 const view=render(<FavoriteStoreButton store="Target" profile={{id:8,display_name:'Other',can_edit:false}}/>);
 expect(screen.queryByRole('button')).not.toBeInTheDocument();
 view.rerender(<FavoriteStoreButton store="Target" profile={{id:7,display_name:'Mia',can_edit:true,favorite_stores:['target']}}/>);
 expect(screen.getByRole('button')).toBeDisabled();
});
