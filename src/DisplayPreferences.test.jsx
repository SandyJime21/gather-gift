import {afterEach,expect,it} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import DisplayPreferences,{DisplayProvider} from './DisplayPreferences.jsx';
afterEach(()=>{cleanup();localStorage.clear();document.documentElement.removeAttribute('data-bs-theme');document.documentElement.removeAttribute('data-text-size');document.documentElement.style.fontSize='';});
it('changes dark mode and text size, persisting browser preferences',async()=>{
 const view=render(<DisplayProvider><DisplayPreferences/></DisplayProvider>);
 fireEvent.click(screen.getByLabelText('Dark mode'));
 fireEvent.change(screen.getByLabelText('Text size'),{target:{value:'150'}});
 await waitFor(()=>expect(document.documentElement.getAttribute('data-bs-theme')).toBe('dark'));
 expect(document.documentElement.style.fontSize).toBe('150%');
 expect(JSON.parse(localStorage.getItem('gather-gift-display'))).toEqual({dark:true,size:150});
 view.unmount();render(<DisplayProvider><DisplayPreferences/></DisplayProvider>);
 expect(screen.getByLabelText('Dark mode')).toBeChecked();expect(screen.getByLabelText('Text size')).toHaveValue('150');
});
it('recovers from invalid stored preferences',()=>{
 localStorage.setItem('gather-gift-display','bad json');
 render(<DisplayProvider><DisplayPreferences/></DisplayProvider>);
 expect(screen.getByLabelText('Dark mode')).not.toBeChecked();
 expect(screen.getByLabelText('Text size')).toHaveValue('100');
});
