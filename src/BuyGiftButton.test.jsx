import {ShoppingProvider} from './ShoppingState.jsx';
import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BuyGiftButton } from "./App.jsx";
import { api } from "./lib/api.js";
vi.mock("./lib/api.js", () => ({ api: vi.fn(), clearCsrfToken: vi.fn(), mediaUrl: (path) => path }));
const item = { id: 1, product_url: "https://example.com/gift", store_name: "Store" };
afterEach(() => { vi.restoreAllMocks(); vi.clearAllMocks(); });

describe("buy with a hold", () => {
  it("waits for the hold before opening the store and shows a return reminder", async () => {
    let finish;
    api.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const tab = { opener: {}, location: { replace: vi.fn() }, close: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(tab);
    render(<MemoryRouter><BuyGiftButton item={item} /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Buying now at Store" }));
    expect(tab.location.replace).not.toHaveBeenCalled();
    expect(api).toHaveBeenCalledWith("/items/1/reservations", expect.objectContaining({ method: "POST", body: JSON.stringify({ quantity: 1, reuse_existing: true }) }));
    finish({ reservation: { id: 5 } });
    await waitFor(() => expect(tab.location.replace).toHaveBeenCalledWith(item.product_url));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fireEvent.mouseOver(screen.getByRole("button", {name:"Continue shopping"}));
    expect(await screen.findByRole("tooltip")).toHaveTextContent("Reserved for up to 24 hours");
  });
  it("closes the waiting tab and does not open the store when a hold fails", async () => {
    api.mockRejectedValueOnce(new Error("Not enough units are available."));
    const tab = { location: { replace: vi.fn() }, close: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(tab);
    render(<MemoryRouter><BuyGiftButton item={item} /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Buying now at Store" }));
    expect(await screen.findByText("Not enough units are available.")).toBeInTheDocument();
    expect(tab.close).toHaveBeenCalled();
    expect(tab.location.replace).not.toHaveBeenCalled();
  });
  it("offers a store link when popups are blocked and reuses an existing hold", async () => {
    vi.spyOn(window, "open").mockReturnValue(null);
    render(<MemoryRouter><BuyGiftButton item={item} alreadyHeld /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Continue shopping" }));
    expect(await screen.findByRole("link", { name: "Open store if it did not open" })).toHaveAttribute("href", item.product_url);
    expect(api).not.toHaveBeenCalled();
    expect(screen.getByRole("button",{name:"Continue shopping"})).toHaveAttribute("aria-pressed","true");
  });
});

it('disables buying a gift held by another shopper',()=>{
 vi.spyOn(window,'open').mockReturnValue(null);
 render(<MemoryRouter><BuyGiftButton item={{...item,availability:{available:0,reserved:1,purchased:0,held_by_you:false}}}/></MemoryRouter>);
 const button=screen.getByRole('button',{name:'Buying now at Store'});
 expect(button).toBeDisabled();fireEvent.click(button);
 expect(api).not.toHaveBeenCalled();expect(window.open).not.toHaveBeenCalled();
});
it('lets the current holder continue buying',()=>{
 render(<MemoryRouter><BuyGiftButton item={{...item,availability:{available:0,reserved:1,held_by_you:true}}} alreadyHeld/></MemoryRouter>);
 expect(screen.getByRole('button',{name:'Continue shopping'})).not.toBeDisabled();
});

it('updates duplicate cards when saving an active hold for later',async()=>{
 const gift={...item,name:'Book',availability:{available:0,reserved:1,purchased:0,held_by_you:true}};
 let rows=[{id:5,item:gift,status:'reserved',quantity:1,is_owner:true}];
 api.mockImplementation(async(path,options)=>{
  if(path==='/my-shopping')return {reservations:rows};
  if(path==='/items/1/heart')return {};
  if(path==='/reservations/5'){expect(JSON.parse(options.body)).toEqual({status:'cancelled'});rows=[];return {};}
  throw Error(path);
 });
 render(<MemoryRouter><ShoppingProvider user={{id:7}}><section aria-label="Home"><BuyGiftButton item={gift}/></section><section aria-label="Following"><BuyGiftButton item={gift}/></section></ShoppingProvider></MemoryRouter>);
 const home=within(screen.getByRole('region',{name:'Home'})),following=within(screen.getByRole('region',{name:'Following'}));
 await waitFor(()=>expect(home.getByRole('button',{name:'Continue shopping'})).toHaveAttribute('aria-pressed','true'));
 expect(following.getByRole('button',{name:'Continue shopping'})).toHaveAttribute('aria-pressed','true');
 fireEvent.click(home.getByRole('button',{name:'Manage purchase'}));
 fireEvent.click(await screen.findByText('Save for later'));
 await waitFor(()=>expect(screen.getAllByRole('button',{name:'Buying now at Store'})).toHaveLength(2));
 expect(api).toHaveBeenCalledWith('/items/1/heart',{method:'PUT'});
});
it('confirms a secret purchase from a shared gift card',async()=>{
 let gift={...item,name:'Book',availability:{available:0,reserved:1,purchased:0,held_by_you:true}};
 let rows=[{id:8,item:gift,status:'reserved',quantity:1,is_owner:true}];
 api.mockImplementation(async(path,options)=>{
  if(path==='/my-shopping')return {reservations:rows};
  if(path==='/reservations/8'){expect(JSON.parse(options.body)).toEqual({status:'purchased',purchase_secret:true,delivery_method:'in_person'});gift={...gift,availability:{available:0,reserved:0,purchased:1,held_by_you:false}};rows=[{...rows[0],status:'purchased',item:gift}];return {};}
  throw Error(path);
 });
 render(<MemoryRouter><ShoppingProvider user={{id:7}}><BuyGiftButton item={gift}/></ShoppingProvider></MemoryRouter>);
 fireEvent.click(await screen.findByRole('button',{name:'Manage purchase'}));
 fireEvent.click(await screen.findByText('Mark purchased'));
 expect(await screen.findByLabelText('Hide who bought this gift')).toBeChecked();
 fireEvent.change(screen.getByLabelText('How will they receive it?'),{target:{value:'in_person'}});
 fireEvent.click(screen.getByRole('button',{name:'Confirm purchase'}));
 await waitFor(()=>expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
 expect(screen.getByRole('button',{name:'Buying now at Store'})).toBeDisabled();
});
