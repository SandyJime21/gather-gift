import {api} from './lib/api.js';
import {fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {expect,it,vi} from 'vitest';
import {ChildWishlistLetter,WishlistLetterManager} from './WishlistLetters.jsx';
vi.mock('./lib/api.js',()=>({api:vi.fn(),mediaUrl:path=>path}));
it('opens only the chosen child letter list and allows deferring another letter',()=>{
 const choose=vi.fn();
 render(<ChildWishlistLetter childName="Mia" letters={[{id:1,wishlist_id:12,title:'Santa wishes',sender_name:'Santa'},{id:2,wishlist_id:13,title:'Birthday wishes',sender_name:'Birthday Fairy'}]} onChoose={choose}/>);
 expect(screen.getByText('Dear Mia,')).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Write my wishlist'}));
 expect(choose).toHaveBeenCalledWith('12');
 expect(screen.getByRole('heading',{name:'Birthday wishes'})).toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Maybe later'}));
 expect(choose).toHaveBeenCalledTimes(1);
});

it('lets the parent choose sender, date, title and specific child recipients',async()=>{
 api.mockResolvedValue({letters:[]});
 render(<WishlistLetterManager householdId={1} profiles={[{id:7,display_name:'Mia',is_adult:false,can_edit:true},{id:8,display_name:'Sam',is_adult:false,can_edit:true},{id:9,display_name:'Adult',is_adult:true,can_edit:true},{id:10,display_name:'Pet',profile_type:'pet',is_adult:false,can_edit:true}]}/>);
 fireEvent.click(screen.getByRole('button',{name:'Create a wishlist letter'}));
 fireEvent.change(screen.getByLabelText('List name'),{target:{value:'Birthday wishes'}});
 fireEvent.change(screen.getByLabelText('Who is asking for their wishlist?'),{target:{value:'Grandma'}});
 fireEvent.change(screen.getByLabelText('Show invitation on'),{target:{value:'2099-12-01'}});
 fireEvent.click(screen.getByLabelText('Mia'));
 expect(screen.getByLabelText('Sam')).not.toBeChecked();
 expect(screen.queryByLabelText('Adult')).not.toBeInTheDocument();
 expect(screen.queryByLabelText('Pet')).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Create invitations'}));
 await waitFor(()=>expect(api).toHaveBeenCalledWith('/households/1/wishlist-letters',expect.objectContaining({method:'POST',body:JSON.stringify({title:'Birthday wishes',sender_name:'Grandma',send_on:'2099-12-01',profile_ids:[7],theme_id:null})})));
 expect(await screen.findByRole('alert')).toHaveTextContent('Invitations saved.');
});

it('shows the parent-selected artwork on the child letter',()=>{
 render(<ChildWishlistLetter childName="Mia" letters={[{id:1,wishlist_id:12,title:'Santa wishes',sender_name:'Santa',letter_art:{art:'/api/themes/4/art',background:'#fff5ee',foreground:'#332244',accent:'#775599'}}]} onChoose={()=>{}}/>);
 expect(document.querySelector('img.letter-art-banner')).toHaveAttribute('src','/api/themes/4/art');
});

it('previews the complete letter for each selected child without saving or charging',async()=>{
 api.mockReset();
 api.mockImplementation(async path=>path.endsWith('/letter-art')?{designs:[{id:4,name:'Winter magic',price_cents:300,unlocked:false,art:'/api/themes/4/art',background:'#fff5ee',foreground:'#332244',accent:'#775599'}],checkout_enabled:true}:{letters:[]});
 render(<WishlistLetterManager householdId={1} profiles={[{id:7,display_name:'Mia',is_adult:false,can_edit:true},{id:8,display_name:'Sam',is_adult:false,can_edit:true}]}/>);
 fireEvent.click(screen.getByRole('button',{name:'Create a wishlist letter'}));
 fireEvent.click(await screen.findByRole('button',{name:'Winter magic $3.00'}));
 fireEvent.change(screen.getByLabelText('List name'),{target:{value:'Birthday dreams'}});
 fireEvent.change(screen.getByLabelText('Who is asking for their wishlist?'),{target:{value:'Birthday Fairy'}});
 fireEvent.click(screen.getByLabelText('Mia'));fireEvent.click(screen.getByLabelText('Sam'));
 fireEvent.click(screen.getByRole('button',{name:'Preview letter'}));
 const preview=await screen.findByRole('dialog',{name:'Wishlist letter preview'});
 expect(within(preview).getByText('Dear Mia,')).toBeInTheDocument();
 expect(within(preview).getByRole('heading',{name:'Birthday dreams'})).toBeInTheDocument();
 expect(preview.querySelector('.letter-art-banner')).toHaveAttribute('src','/api/themes/4/art');
 expect(within(preview).getByRole('button',{name:'Write my wishlist'})).toBeDisabled();
 fireEvent.change(within(preview).getByLabelText('Preview for'),{target:{value:'8'}});
 expect(within(preview).getByText('Dear Sam,')).toBeInTheDocument();
 expect(within(preview).getByText('Birthday Fairy')).toBeInTheDocument();
 expect(preview.querySelector('.letter-signature')).toHaveTextContent('Birthday Fairy');
 expect(api.mock.calls.some(([,options])=>options?.method==='POST')).toBe(false);
 fireEvent.click(within(preview).getByRole('button',{name:'Back to editing'}));
 expect(await screen.findByLabelText('List name')).toHaveValue('Birthday dreams');
 expect(screen.getByLabelText('Who is asking for their wishlist?')).toHaveValue('Birthday Fairy');
 expect(screen.getByRole('button',{name:'Create invitations'})).toBeDisabled();
});
