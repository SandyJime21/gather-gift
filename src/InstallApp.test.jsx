import {afterEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import InstallApp from './InstallApp.jsx';
afterEach(()=>{cleanup();vi.unstubAllGlobals();vi.restoreAllMocks();});

it('shows iPad Home Screen instructions when no automatic installer is available',()=>{
 vi.spyOn(navigator,'userAgent','get').mockReturnValue('iPad');
 render(<InstallApp/>);
 fireEvent.click(screen.getByRole('button',{name:'Download'}));
 expect(screen.getByText('On your iPad or iPhone')).toBeInTheDocument();
 expect(screen.getByText(/Keep Open as Web App on/)).toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Install Gather & Gift'})).not.toBeInTheDocument();
});

it('opens the browser installer and stays available after dismissal',async()=>{
 render(<InstallApp/>);
 const event=new Event('beforeinstallprompt',{cancelable:true});
 event.prompt=vi.fn().mockResolvedValue(undefined);event.userChoice=Promise.resolve({outcome:'dismissed'});
 act(()=>window.dispatchEvent(event));
 expect(event.defaultPrevented).toBe(true);
 fireEvent.click(screen.getByRole('button',{name:'Download'}));
 fireEvent.click(screen.getByRole('button',{name:'Install Gather & Gift'}));
 await waitFor(()=>expect(event.prompt).toHaveBeenCalledOnce());
 await waitFor(()=>expect(screen.queryByRole('button',{name:'Install Gather & Gift'})).not.toBeInTheDocument());
 expect(screen.getByRole('dialog')).toBeInTheDocument();
 expect(screen.getByText('On your laptop')).toBeInTheDocument();
});

it('hides the install button after installation',()=>{
 render(<InstallApp/>);
 act(()=>window.dispatchEvent(new Event('appinstalled')));
 expect(screen.queryByRole('button',{name:'Download'})).not.toBeInTheDocument();
});

it('does not offer installation when already running as an installed app',()=>{
 vi.stubGlobal('matchMedia',vi.fn(()=>({matches:true,addEventListener:vi.fn(),removeEventListener:vi.fn()})));
 render(<InstallApp/>);
 expect(screen.queryByRole('button',{name:'Download'})).not.toBeInTheDocument();
});
