import {render,screen} from '@testing-library/react';
import {expect,it} from 'vitest';
import FavoriteBrands from './FavoriteBrands.jsx';
it('groups favorite brands with small owner names instead of profile cards',()=>{
 render(<FavoriteBrands profiles={[{id:1,display_name:'Sam',preferences:{favorite_brands:['Nike','None']}},{id:2,display_name:'Mia',preferences:{favorite_brands:['nike']}},{id:1,display_name:'Sam',preferences:{favorite_brands:['Nike']}}]}/>);
 expect(screen.getByText('Nike')).toBeInTheDocument();
 expect(screen.getByText('Sam, Mia love this')).toBeInTheDocument();
 expect(screen.queryByText('None')).not.toBeInTheDocument();
 expect(screen.getAllByRole('article')).toHaveLength(1);
});
