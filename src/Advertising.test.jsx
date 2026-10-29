import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AdvertisePage, AdSlot } from './Advertising.jsx';
import { api } from './lib/api.js';
vi.mock('./lib/api.js', () => ({ api: vi.fn(), mediaUrl: value=>value }));
afterEach(() => vi.clearAllMocks());

describe('advertising', () => {
  it('submits creative and schedule for review before showing payment', async () => {
    api.mockImplementation(async (path, options) => {
      if (path === '/ads/config') return { daily_rate_cents:100, currency:'usd' };
      if (path === '/ads/campaigns') {
        const body=JSON.parse(options.body);
        expect(body.weekdays).toEqual([0,1,2,3,4,5,6]);
        expect(body.keywords).toEqual(['Christmas','toys']);
        expect(body.media_type).toBe('image');
        return {campaign:{id:1,...body,status:'pending_review',paid:false,amount_cents:300},token:'private-ad-token'};
      }
      if(path==='/ads/campaigns/1/status')return {campaign:{id:1,title:'Holiday sale',status:'pending_review',paid:false,amount_cents:300}};
      throw new Error('Unexpected request');
    });
    render(<MemoryRouter><AdvertisePage/></MemoryRouter>);
    for(const [label,value] of [['Business name','Toy store'],['Contact email','store@example.com'],['Business or store link (HTTPS)','https://example.com'],['Ad title','Holiday sale'],['Short description','Thoughtful toys'],['Hosted image or video URL (HTTPS)','https://example.com/ad.jpg'],['Start date','2027-12-01'],['End date','2027-12-03'],['Keywords (comma separated; optional)','Christmas, toys']]) fireEvent.change(screen.getByLabelText(label),{target:{value}});
    fireEvent.click(screen.getByRole('button',{name:'Submit campaign for review'}));
    expect(await screen.findByText('pending review')).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Pay with Stripe'})).not.toBeInTheDocument();
    expect(screen.getByText(/private campaign access link/)).toBeInTheDocument();
  });
  it('labels approved advertisements and links to the advertiser store', async () => {
    api.mockResolvedValue({ads:[{title:'Holiday sale',description:'New toys',business_name:'Toy store',business_url:'https://example.com',media_type:'image',media_url:'https://example.com/ad.jpg',display_seconds:15}]});
    render(<MemoryRouter><AdSlot placement="home" query="Christmas"/></MemoryRouter>);
    expect(await screen.findByRole('img',{name:'Holiday sale'})).toBeInTheDocument();
    expect(screen.getByRole('link',{name:'Visit Toy store'})).toHaveAttribute('rel','sponsored noopener noreferrer');
    expect(screen.getByText('ADVERTISEMENT')).toBeInTheDocument();
  });
});

it('shows a compact sponsored row with a label on every ad',async()=>{
 api.mockResolvedValue({ads:Array.from({length:5},(_,id)=>({id:id+1,title:'Offer '+id,business_name:'Shop',business_url:'https://example.com',media_type:'image',media_url:'https://example.com/ad.jpg',display_seconds:15}))});
 render(<MemoryRouter><AdSlot placement="discover" sponsoredRow hideEmpty/></MemoryRouter>);
 expect(await screen.findByRole('region',{name:'Sponsored gifts'})).toBeInTheDocument();
 expect(screen.getAllByRole('img')).toHaveLength(3);
 expect(screen.getAllByText('Sponsored')).toHaveLength(4);
});
