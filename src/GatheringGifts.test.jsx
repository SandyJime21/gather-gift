import {render,screen} from '@testing-library/react';
import {expect,it} from 'vitest';
import GatheringGifts from './GatheringGifts.jsx';
it('shows the playful loading message with decorative falling gifts',()=>{
 const {container}=render(<GatheringGifts/>);
 expect(screen.getByRole('heading',{name:'Stay tuned while we gather your gifts'})).toBeInTheDocument();
 expect(screen.getByRole('status')).toHaveTextContent('Gathering the good stuff');
 expect(container.querySelector('.gift-shower')).toHaveAttribute('aria-hidden','true');
 expect(screen.queryByRole('button')).not.toBeInTheDocument();
});
