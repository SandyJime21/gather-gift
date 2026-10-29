import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within, waitFor } from "@testing-library/react";
import App from "./App.jsx";
import { clearCsrfToken } from "./lib/api.js";

vi.mock("./PhotoCropper.jsx", () => ({ usePhotoCrop: () => ({ crop: async (file) => file || null, cropper: null }) }));

const jsonResponse = (data, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => data,
});

let registered;
let reserved;

beforeEach(() => {
  registered = false;
  reserved = false;
  window.history.replaceState({}, "", "/register");
  clearCsrfToken();
  vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
    if (url === "/api/notifications") return jsonResponse({ notifications: [] });
    if (url === "/api/wishlist") return jsonResponse({ hearted: [], private_gifts: [], family_profiles: [] });
    if (url === "/api/my-shopping") return jsonResponse({ reservations: reserved ? [{id:5,status:"reserved",quantity:1,is_owner:true,item:{id:50,name:"Junior baking kit",availability:{available:0,reserved:1,purchased:0,held_by_you:true}}}] : [] });
    if (url === "/api/co-buy-invitations") return jsonResponse({ invitations: [] });
    if (url === "/api/auth/csrf") return jsonResponse({ csrf_token: "test-csrf" });
    if (url === "/api/auth/me" && !registered) return jsonResponse({ error: "Authentication required." }, 401);
    if (url === "/api/auth/register") {
      registered = true;
      return jsonResponse({
        user: { id: 1, name: "Taylor Example", email: "taylor@example.com" },
        csrf_token: "signed-in-csrf",
      }, 201);
    }
    if (url === "/api/auth/me") {
      return jsonResponse({
        user: { id: 1, name: "Taylor Example", email: "taylor@example.com" },
        households: [],
      });
    }
    if (url === "/api/households" && options.method === "POST") {
      return jsonResponse({ household: { id: 9, name: "The Example Family", role: "owner" } }, 201);
    }
    if (url === "/api/households/9") {
      return jsonResponse({
        household: { id: 9, name: "The Example Family", role: "owner" },
        profiles: [{ id: 21, display_name: "Mia", interests: [] }],
      });
    }
    if (url === "/api/households/9/invitations" && options.method === "POST") {
      return jsonResponse({ invitation: { token: "safe-test-invitation-token" } }, 201);
    }
    if (url.startsWith("/api/shopping")) {
      return jsonResponse({ items: [{
        id: 50,
        name: "Junior baking kit",
        description: "A cozy weekend activity.",
        recipient: "Mia",
        households: [{id:9,name:"The Example Family"}],
        request_type: "want",
        priority: 4,
        currency: "USD",
        estimated_price: "24.99",
        availability: { available: reserved ? 0 : 1, reserved: reserved ? 1 : 0, purchased: 0 },
      }] });
    }
    if (url === "/api/items/50/reservations" && options.method === "POST") {
      reserved = true;
      return jsonResponse({ reservation: { id: 5, status: "reserved" } }, 201);
    }
    return jsonResponse({ error: `Unexpected request: ${url}` }, 404);
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  clearCsrfToken();
});

describe("landing page", () => {
  it("introduces the family gift registry and offers account actions", async () => {
    window.history.replaceState({}, "", "/");
    render(<App />);
    expect(await screen.findByRole("heading", { name: /make giving feel like family/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create your family space/i })).toHaveAttribute("href", "/register");
    expect(screen.getByRole("button", { name: /i have an account/i })).toHaveAttribute("href", "/login");
    expect(screen.getByRole("heading", { name: "Your account is free." })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sign up for free" })).toHaveAttribute("href", "/register");
    expect(screen.getByText(/Our plan is to fund the app through ads and retailer referral fees/)).toBeInTheDocument();
  });

  it('adds pet profiles in Settings and lets the owner choose wishlist sharing', async () => {
    registered = true;
    window.history.replaceState({}, '', '/settings?tab=family');
    let profiles = [{ id: 21, display_name: 'Taylor', profile_type: 'person', is_you: true, can_edit: true }];
    let sharePetWishlist = false;
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/auth/me') return jsonResponse({ user: { id: 1, name: 'Taylor', email: 'taylor@example.com' }, households: [{ id: 9, name: 'Our family', owner_id: 1, role: 'owner' }] });
      if (url === '/api/household-session/switch') return jsonResponse({status:'household'});
      if (url === '/api/households/9') return jsonResponse({ household: { id: 9, name: 'Our family', owner_id: 1, role: 'owner' }, profiles });
      if (url === '/api/households/9/profiles' && options.method === 'POST') {
        expect(JSON.parse(options.body)).toEqual({ display_name: 'Mochi', profile_type: 'pet' });
        const pet = { id: 22, display_name: 'Mochi', profile_type: 'pet', can_edit: true, can_add: true, share_wishlist: false };
        profiles = [...profiles, pet];
        return jsonResponse({ profile: pet }, 201);
      }
      if (url === '/api/profiles/22') return jsonResponse({profile:{...profiles[1],can_remove_wishes:true}});
      if (url === '/api/wishlists/31/items') return jsonResponse({items:[]});
      if (url === '/api/profiles/22/wishlists') return jsonResponse({wishlists:[{id:31,title:'Mochi wishes',share_publicly:false}]});
      if (url === '/api/wishlists/31' && options.method === 'PATCH') {
        expect(JSON.parse(options.body)).toEqual({ share_publicly: true });
        sharePetWishlist = true;
        return jsonResponse({ profile: { ...profiles[1], share_wishlist: true } });
      }
      return fallback(url, options);
    });

    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Add pet' }));
    const dialog = await screen.findByRole('dialog');
    fireEvent.change(within(dialog).getByLabelText("Pet's name"), { target: { value: 'Mochi' } });
    fireEvent.click(within(dialog).getByRole('button', { name: 'Add pet' }));
    const petCard=await screen.findByRole('button',{name:/Mochi/});
    expect(screen.queryByRole('checkbox',{name:'Private'})).not.toBeInTheDocument();
    fireEvent.click(petCard);
    fireEvent.click(await screen.findByText('Lists & gifts')); 
    const sharing = await screen.findByRole('checkbox', { name: 'Private' });
    fireEvent.click(sharing);
    await waitFor(() => expect(sharePetWishlist).toBe(true));
    expect(sharing).toBeChecked();
  });
});

describe("family gift planning flow", () => {
  it("registers, creates a household, and reserves a gift privately", async () => {
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Your name"), { target: { value: "Taylor Example" } });
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "taylor@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "family-demo-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Create my account" }));

    expect(await screen.findByRole("heading", { name: "My wishes", level:1 }, {timeout:3000})).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Household name"), { target: { value: "The Example Family" } });
    expect(screen.queryByLabelText("Which family member are you?")).not.toBeInTheDocument();
    expect(screen.getByText("Taylor Example (you)")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Family member 1 name"), { target: { value: "Taylor" } });
    fireEvent.change(screen.getByLabelText("Family member 1 relationship"), { target: { value: "dad" } });
    fireEvent.click(screen.getByRole("button", { name: "+ Add another person or pet" }));
    fireEvent.change(screen.getByLabelText("Family member 2 name"), { target: { value: "Mochi" } });
    fireEvent.change(screen.getByLabelText("Family member 2 type"), { target: { value: "pet" } });
    fireEvent.click(screen.getByRole("button", { name: "Create household" }));
    expect(await screen.findByRole("link", { name: /the example family/i })).toBeInTheDocument();
    const createRequest = fetch.mock.calls.find(([url, options]) => url === "/api/households" && options?.method === "POST");
    expect(JSON.parse(createRequest[1].body).self_profile_index).toBe("new");
    expect(JSON.parse(createRequest[1].body).profiles).toEqual([
      { display_name: "Taylor", profile_type: "person", birthday: "", relationship: "dad" },
      { display_name: "Mochi", profile_type: "pet", birthday: "" },
    ]);

    fireEvent.click(screen.getByRole("link", { name: "My wishes" }));

    expect(await screen.findByRole("heading", { name: 'My family wishes' })).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Buying now" }));
    expect(await screen.findByText("On hold")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Buying now" })).not.toBeInTheDocument();
  }, 15000);
});

describe("separate support sign-in", () => {
  it("opens the dedicated support portal rather than the family dashboard", async () => {
    window.history.replaceState({}, "", "/support/login");
    let supportSignedIn = false;
    vi.stubGlobal("fetch", vi.fn(async (url) => {
      if (url === "/api/auth/csrf") return jsonResponse({ csrf_token: "support-csrf" });
      if (url === "/api/auth/support/login") {
        supportSignedIn = true;
        return jsonResponse({
          user: { id: 7, name: "Support Agent", email: "support@example.com", is_support: true },
          csrf_token: "support-auth-csrf",
        });
      }
      if (url === "/api/auth/me") {
        if (!supportSignedIn) return jsonResponse({ error: "Authentication required." }, 401);
        return jsonResponse({
          user: { id: 7, name: "Support Agent", email: "support@example.com", is_support: true },
          households: [],
        });
      }
      if (url === "/api/support/requests") return jsonResponse({ requests: [] });
      if (url === "/api/support/grants") return jsonResponse({ grants: [] });
      if (url === "/api/support/tickets") return jsonResponse({ tickets: [] });
      if (url === "/api/support/audit-logs") return jsonResponse({ logs: [] });
      return jsonResponse({ error: `Unexpected request: ${url}` }, 404);
    }));
    render(<App />);
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "support@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "a-separate-strong-support-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: /developer & support portal/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /request customer access/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Gift ideas" })).not.toBeInTheDocument();
  });

  it("lets support prepare a family and send its owner-claim invitation", async () => {
    window.history.replaceState({}, "", "/support");
    let setupPayload;
    vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
      if (url === "/api/auth/csrf") return jsonResponse({ csrf_token: "support-csrf" });
      if (url === "/api/auth/me") return jsonResponse({
        user: { id: 8, name: "Support Agent", email: "support@example.com", is_support: true },
        households: [],
      });
      if (url === "/api/support/requests") return jsonResponse({ requests: [] });
      if (url === "/api/support/grants") return jsonResponse({ grants: [] });
      if (url === "/api/support/tickets") return jsonResponse({ tickets: [] });
      if (url === "/api/support/audit-logs") return jsonResponse({ logs: [] });
      if (url === "/api/support/family-setup-invitations" && options.method === "POST") {
        setupPayload = options.body;
        return jsonResponse({
          household: { id: 41, name: "The Rivera Family" },
          profile: { id: 42, display_name: "Alex Rivera" },
          invitation: { email: "alex@example.com", expires_at: "2026-11-02T00:00:00+00:00" },
          email_message: {
            delivery: "sent",
            link: "https://app.example.com/accept-invitation/private-family-token",
            body: "Claim your family space.",
          },
        }, 201);
      }
      return jsonResponse({ error: `Unexpected request: ${url}` }, 404);
    }));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Family & invites" }));
    fireEvent.change(await screen.findByLabelText("Invitee email"), { target: { value: "alex@example.com" } });
    fireEvent.change(screen.getByLabelText("Family name"), { target: { value: "The Rivera Family" } });
    fireEvent.change(screen.getByLabelText("Primary adult profile name"), { target: { value: "Alex Rivera" } });
    fireEvent.change(screen.getByLabelText("Birthday (optional)"), { target: { value: "1990-07-23" } });
    fireEvent.click(screen.getByRole("button", { name: "Create family and invite" }));
    expect(await screen.findByRole("textbox", { name: "Private family invitation link" })).toHaveValue(
      "https://app.example.com/accept-invitation/private-family-token",
    );
    expect(setupPayload).toBeInstanceOf(FormData);
    expect(setupPayload.get("email")).toBe("alex@example.com");
    expect(setupPayload.get("household_name")).toBe("The Rivera Family");
    expect(setupPayload.get("profile_name")).toBe("Alex Rivera");
    expect(setupPayload.get("birthday")).toBe("1990-07-23");
  });

  it("lets only the master portal create and display a private staff invitation", async () => {
    window.history.replaceState({}, "", "/support");
    let created = false;
    vi.stubGlobal("fetch", vi.fn(async (url, options = {}) => {
      if (url === "/api/auth/csrf") return jsonResponse({ csrf_token: "master-csrf" });
      if (url === "/api/auth/me") return jsonResponse({
        user: { id: 7, name: "Master Agent", email: "master@example.com", is_support: true, is_superuser: true },
        households: [],
      });
      if (url === "/api/support/requests") return jsonResponse({ requests: [] });
      if (url === "/api/support/grants") return jsonResponse({ grants: [] });
      if (url === "/api/support/tickets") return jsonResponse({ tickets: [] });
      if (url === "/api/support/audit-logs") return jsonResponse({ logs: [] });
      if (url === "/api/support/staff-invitations" && options.method === "POST") {
        created = true;
        return jsonResponse({ invitation: { email: "new-staff@example.com", token: "private-invite-token" } }, 201);
      }
      if (url === "/api/support/staff-invitations") return jsonResponse({ invitations: [] });
      return jsonResponse({ error: `Unexpected request: ${url}` }, 404);
    }));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Family & invites" }));
    fireEvent.change(await screen.findByLabelText("Staff email address"), { target: { value: "new-staff@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Create private invitation" }));
    expect(await screen.findByRole("textbox", { name: "Private invitation link" })).toHaveValue(
      `${window.location.origin}/support/accept-invitation/private-invite-token`,
    );
    expect(created).toBe(true);
  });

  it('lets a child add and remove wishes on family pet lists', async () => {
    registered = true;
    window.history.replaceState({}, '', '/wishlist');
    let petItems = [{ id: 70, name: 'Treat puzzle', description: '' }];
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/auth/me') return jsonResponse({ user: { id: 7, name: 'Mia', is_child: true, is_support: false }, households: [] });
      if (url === '/api/child/me') return jsonResponse({
        name: 'Mia',
        controls: {manage_pets: true},
        wishlists: [{ id: 12, title: 'Birthday wishes', items: [] }],
        pets: [{ id: 30, name: 'Mochi', avatar_key: 'cat', photo_path: null, items: petItems }],
      });
      if (url === '/api/child/pets/30/items' && options.method === 'POST') {
        petItems = [...petItems, { id: 71, name: JSON.parse(options.body).name, description: '' }];
        return jsonResponse({ item: petItems[1] }, 201);
      }
      if (url === '/api/child/pets/30/items/70' && options.method === 'DELETE') {
        petItems = petItems.filter(item => item.id !== 70);
        return jsonResponse({ status: 'removed' });
      }
      return fallback(url, options);
    });

    render(<App />);
    expect(await screen.findByRole('heading', { name: 'Pet wishlists' })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Add a wish for Mochi'), { target: { value: 'New cat bed' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    expect(await screen.findByText("Added to Mochi's wishes.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: "Remove Treat puzzle from Mochi's wishlist" }));
    expect(await screen.findByText("Removed from Mochi's wishes.")).toBeInTheDocument();
    expect(screen.queryByText('Treat puzzle')).not.toBeInTheDocument();
  });
});

describe("profile-scoped invitations", () => {
  it("creates a family invite without choosing profiles", async () => {
    registered = true;
    window.history.replaceState({}, "", "/households/9");
    vi.stubGlobal("fetch", vi.fn(async (url) => {
      if (url === "/api/auth/csrf") return jsonResponse({ csrf_token: "family-csrf" });
      if (url === "/api/auth/me") return jsonResponse({
        user: { id: 1, name: "Taylor Example", email: "taylor@example.com", is_support: false },
        households: [{ id: 9, name: "The Example Family", role: "owner" }],
      });
      if (url === "/api/households/9") return jsonResponse({
        household: { id: 9, name: "The Example Family", role: "owner" },
        profiles: [{ id: 21, display_name: "Mia", interests: [] }],
      });
      if (url === "/api/households/9/invitations") {
        return jsonResponse({ invitation: { token: "safe-test-invitation-token" } }, 201);
      }
      return jsonResponse({ error: "Unexpected request." }, 404);
    }));
    render(<App />);
    fireEvent.click(await screen.findByRole("button", {name:"Family settings"}));
    expect(screen.queryByLabelText("Mia")).not.toBeInTheDocument();
    fireEvent.change(await screen.findByLabelText("Email address"), { target: { value: "shopper@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Create invitation" }));
    expect(await screen.findByRole("textbox", { name: "Invitation link" })).toHaveValue(
      `${window.location.origin}/accept-invitation/safe-test-invitation-token`,
    );
  });
});

describe("household special-day dialog", () => {
  it("keeps the occasion form off the page until requested", async () => {
    registered = true;
    window.history.replaceState({}, "", "/households/9");
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === "/api/auth/me") return jsonResponse({
        user: { id: 1, name: "Taylor Example", is_support: false },
        households: [{ id: 9, name: "The Example Family", role: "owner" }],
      });
      if (url === "/api/households/9") return jsonResponse({
        household: { id: 9, name: "The Example Family", role: "owner" },
        profiles: [{ id: 21, display_name: "Mia", birthday: "05-14", profile_type: "person" }],
        occasions: [],
      });
      return fallback(url, options);
    });
    render(<App />);
    const addButton = await screen.findByRole("button", { name: "Add a special day" });
    expect(screen.queryByLabelText("Occasion")).not.toBeInTheDocument();
    fireEvent.click(addButton);
    expect(await screen.findByLabelText("Occasion")).toBeInTheDocument();
  });
});

describe("family photo visibility", () => {
  it("shows the uploaded family photo immediately and when returning to the household card", async () => {
    registered = true;
    window.history.replaceState({}, "", "/households/9");
    let photo = null;
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === "/api/auth/me") return jsonResponse({ user: { id: 1, name: "Taylor" }, households: [{ id: 9, name: "Photo Family", role: "owner", photo_path: null }] });
      if (url === "/api/households/9") return jsonResponse({ household: { id: 9, name: "Photo Family", role: "owner", photo_path: photo }, profiles: [], occasions: [] });
      if (url === "/api/households/9/photo" && options.method === "POST") {
        photo = "/api/uploads/family.jpg";
        return jsonResponse({ photo_path: photo });
      }
      return fallback(url, options);
    });
    render(<App />);
    const settings = await screen.findByRole("button", { name: "Family settings" });
    expect(settings).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByLabelText("Family photo")).not.toBeInTheDocument();
    fireEvent.click(settings);
    expect(settings).toHaveAttribute("aria-expanded", "true");
    fireEvent.change(await screen.findByLabelText("Family photo"), { target: { files: [new File(["photo"], "family.jpg", { type: "image/jpeg" })] } });
    expect(await screen.findByRole("img", { name: "Photo Family family photo" })).toHaveAttribute("src", "/api/uploads/family.jpg");
    fireEvent.click(screen.getByRole("link", { name: /All households/ }));
    expect(await screen.findByRole("img", { name: "Photo Family family photo" })).toHaveAttribute("src", "/api/uploads/family.jpg");
  });
});

describe("invitation account flow", () => {
  it("preserves the invitation when switching auth screens and adds the family after account creation", async () => {
    window.history.replaceState({}, "", "/accept-invitation/private-invite");
    let accepted = false;
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === "/api/invitations/accept") {
        expect(JSON.parse(options.body)).toEqual({ token: "private-invite" });
        accepted = true;
        return jsonResponse({ status: "accepted", household_id: 9, profile_ids: [21] });
      }
      if (url === "/api/households/9") return jsonResponse({ household: { id: 9, name: "Invited Family", role: "shopper" }, profiles: [], occasions: [] });
      if (url === "/api/auth/me" && registered) return jsonResponse({ user: { id: 1, name: "Taylor", email: "taylor@example.com" }, households: accepted ? [{ id: 9, name: "Invited Family", role: "shopper" }] : [] });
      return fallback(url, options);
    });
    render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Create my account" }));
    fireEvent.click(screen.getByRole("link", { name: "Sign in" }));
    expect(window.location.search).toContain("next=");
    fireEvent.click(screen.getByRole("link", { name: "Create an account" }));
    fireEvent.change(screen.getByLabelText("Your name"), { target: { value: "Taylor" } });
    fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "taylor@example.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "long-enough-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Create my account" }));
    expect(await screen.findByRole("heading", { name: "Invited Family" })).toBeInTheDocument();
    expect(accepted).toBe(true);
    fireEvent.click(screen.getByRole("link", { name: /All households/ }));
    expect(await screen.findByRole("button", { name: /Invited Family/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /All families/ }));
    const familyDialog=await screen.findByRole("dialog");
    fireEvent.click(within(familyDialog).getByRole("button", {name:/Invited Family/}));
    expect(within(familyDialog).getByText("Invited Family", {selector:".modal-title"})).toBeInTheDocument();
  });
});

describe("wishlist hub", () => {
  it("keeps hearted gifts with recipient details and unhearts them without changing a hold", async () => {
    registered = true;
    window.history.replaceState({}, "", "/wishlist?section=browse");
    let hearted = false;
    const item = { id: 50, profile_id: 21, name: "Junior baking kit", recipient: "Mia", households: [{ id: 9, name: "Example family" }], occasions: ["Birthday"], added_by: "Taylor", availability: { available: 1, reserved: 0, purchased: 0 } };
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === "/api/wishlist") return jsonResponse({ hearted: hearted ? [{ ...item, is_hearted: true }] : [], private_gifts: [], family_profiles: [] });
      if (url.startsWith('/api/shopping')) return jsonResponse({ items: [{ ...item, is_hearted: hearted }] });
      if (url === '/api/items/50/heart') { hearted = options.method === 'PUT'; return jsonResponse({ is_hearted: hearted }); }
      return fallback(url, options);
    });
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Heart gift' }));
    fireEvent.click(screen.getByRole('link', {name:'My gifting'}));
    await screen.findByRole('heading', {name:'My gifting',level:1});
    fireEvent.click(await screen.findByText(/^Saved for later/));
    await waitFor(() => expect(within(document.getElementById('my-gifting')).getByRole('button', { name: 'Unheart' })).toBeInTheDocument());
    expect(screen.queryByRole('tablist', {name:'Wishlist areas'})).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Shop my circles' })).not.toBeInTheDocument();
    expect(await within(document.getElementById('my-gifting')).findByRole('heading', { name: 'Junior baking kit' })).toBeInTheDocument();
    expect(within(document.getElementById('my-gifting')).getByText('Birthday')).toBeInTheDocument();
    fireEvent.click(within(document.getElementById('my-gifting')).getByRole('button', { name: 'Unheart' }));
    expect(await screen.findByRole('heading', { name: 'No gift ideas yet' })).toBeInTheDocument();
    expect(fetch.mock.calls.some(([url]) => url === '/api/items/50/reservations')).toBe(false);
  });
});

describe("settings and notification bell", () => {
  it("opens the notification feed separately from settings and clears the unread badge", async () => {
    registered = true;
    window.history.replaceState({}, '', '/');
    let read = false;
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/notifications') return jsonResponse({ notifications: [{ id: 1, message: 'A gift was purchased.', household_name: 'Example family', profile_id: 21, created_at: '2026-10-20T12:00:00Z', read }] });
      if (url === '/api/notifications/1/read') { read = true; return jsonResponse({ status: 'read' }); }
      return fallback(url, options);
    });
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Notifications, 1 unread' }));
    fireEvent.click(await screen.findByRole('link', { name: 'See all notifications' }));
    expect(await screen.findByRole('heading',{name:'Notifications'})).toBeInTheDocument();
    expect(screen.queryByRole('combobox',{name:'Settings section'})).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: 'Mark read' }));
    expect(await screen.findByRole('button', { name: 'Notifications' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Notification settings'}));
    const settingsSection=await screen.findByRole('combobox',{name:'Settings section'});
    expect(settingsSection).toHaveValue('notifications');
    fireEvent.change(settingsSection, { target: { value: 'account' } });
    fireEvent.change(screen.getByLabelText('Main household email address'), { target: { value: 'new@example.com' } });
    expect(screen.getByLabelText('Current password to change email')).toBeRequired();
    expect(screen.queryByRole('link', { name: 'My shopping' })).not.toBeInTheDocument();
  });
});

describe('password recovery', () => {
  it('opens forgot password from sign-in and requests an email', async () => {
    window.history.replaceState({}, '', '/login');
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/auth/recovery-code') {
        expect(JSON.parse(options.body).email).toBe('taylor@example.com');
        return jsonResponse({ challenge_id: 'test-challenge', message: 'If an account uses that email, a code will be sent.' });
      }
      return fallback(url, options);
    });
    render(<App />);
    fireEvent.click(await screen.findByRole('link', { name: 'Forgot password?' }));
    fireEvent.change(screen.getByLabelText('Main email address'), { target: { value: 'taylor@example.com' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send one-time code' }));
    expect(await screen.findByText('If an account uses that email, a code will be sent.')).toBeInTheDocument();
  });
  it('confirms the new password before resetting and returns to the invitation sign-in', async () => {
    window.history.replaceState({}, '', '/reset-password?token=private-token&next=%2Faccept-invitation%2Fabc');
    const fallback = fetch.getMockImplementation();
    let reset = false;
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/auth/reset-password') {
        reset = true;
        expect(JSON.parse(options.body)).toEqual({ token: 'private-token', password: 'new-long-password' });
        return jsonResponse({ message: 'Your password has been reset.', login_path: '/login' });
      }
      return fallback(url, options);
    });
    render(<App />);
    fireEvent.change(await screen.findByLabelText('New password'), { target: { value: 'new-long-password' } });
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'does-not-match' } });
    fireEvent.click(screen.getByRole('button', { name: 'Reset password' }));
    expect(await screen.findByText('The passwords do not match.')).toBeInTheDocument();
    expect(reset).toBe(false);
    fireEvent.change(screen.getByLabelText('Confirm new password'), { target: { value: 'new-long-password' } });
    fireEvent.click(screen.getByRole('button', { name: 'Reset password' }));
    expect(await screen.findByRole('button', { name: 'Sign in with new password' })).toHaveAttribute('href', '/login?next=%2Faccept-invitation%2Fabc');
    expect(reset).toBe(true);
  });
});

describe('child wishlist session', () => {
  it('redirects adult pages to add-only wishes and hides shopping and account controls', async () => {
    registered = true;
    window.history.replaceState({}, '', '/wishlist?section=plans');
    let items = [];
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/auth/me') return jsonResponse({ user: { id: 7, name: 'Mia', is_child: true, is_support: false }, households: [] });
      if (url === '/api/child/me') return jsonResponse({ name: 'Mia', wishlists: [{ id: 12, title: 'Birthday wishes', items }] });
      if (url === '/api/child/wishlists/12/items') {
        expect(JSON.parse(options.body)).toEqual({ name: 'Dinosaur book', description: '' });
        items = [{ id: 50, name: 'Dinosaur book', description: '' }];
        return jsonResponse({ item: items[0] }, 201);
      }
      return fallback(url, options);
    });
    render(<App />);
    expect(await screen.findByRole('heading', { name: 'My wishes', level:1 })).toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Main navigation' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Settings' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Notifications' })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: /Dinosaur book/ }));
    expect(await screen.findByRole('heading', { name: 'Dinosaur book' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Delete|Remove|Buy|Invite/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Browse|View product/ })).not.toBeInTheDocument();
  });
});

describe('account appearance', () => {
  it('saves a Christmas theme and keeps it while browsing the wishlist', async () => {
    registered = true;
    window.history.replaceState({}, '', '/settings?tab=appearance');
    let theme = 'classic';
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/auth/me') return jsonResponse({ user: { id: 1, name: 'Taylor', email: 'taylor@example.com', theme_key: theme }, households: [] });
      if (url === '/api/auth/theme') { theme = JSON.parse(options.body).theme_key; return jsonResponse({ theme_key: theme }); }
      return fallback(url, options);
    });
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: /Christmas.*Use theme/ }));
    expect(await screen.findByText('Your theme has been updated.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Settings' }).closest('.app-shell')).toHaveClass('theme-christmas');
    fireEvent.click(screen.getByRole('link', { name: 'My wishes' }));
    expect(await screen.findByRole('heading', { name: 'My wishes' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'My wishes', level:1 }).closest('.app-shell')).toHaveClass('theme-christmas');
  });
});

describe('company registries', () => {
  it('creates a workplace registry with employee profiles', async () => {
    registered = true;
    window.history.replaceState({}, '', '/');
    const fallback = fetch.getMockImplementation();
    let created;
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/households' && options.method === 'POST') { created = JSON.parse(options.body); return jsonResponse({ household: { id: 25, name: created.name, registry_type: 'company', role: 'owner' } }, 201); }
      return fallback(url, options);
    });
    render(<App />);
    fireEvent.change(await screen.findByLabelText('Registry type'), { target: { value: 'company' } });
    fireEvent.change(screen.getByLabelText('Company name'), { target: { value: 'Example Co' } });
    fireEvent.change(screen.getByLabelText('Family member 1 name'), { target: { value: 'Alex' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create company registry' }));
    expect(await screen.findByRole('link', { name: /Example Co/ })).toBeInTheDocument();
    expect(created.registry_type).toBe('company');
    expect(created.profiles[0]).toEqual(expect.objectContaining({ display_name: 'Alex', profile_type: 'person', relationship: 'employee' }));
  });
});

describe('registry shopper preview', () => {
  it('shows selected shared wishes with disabled purchase actions', async () => {
    registered = true;
    window.history.replaceState({}, '', '/households/9');
    const fallback = fetch.getMockImplementation();
    fetch.mockImplementation(async (url, options = {}) => {
      if (url === '/api/households/9/shopper-preview') return jsonResponse({ household: { name: 'The Example Family' }, profiles: [{ id: 21, display_name: 'Mia', wishlists: [{ title: 'Birthday wishes', items: [{ name: 'A lovely puzzle', quantity: 1 }] }] }] });
      return fallback(url, options);
    });
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: 'Preview registry' }));
    expect(await screen.findByRole('heading', { name: 'A lovely puzzle' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Buy' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Heart gift' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Put on hold' })).toBeDisabled();
    fireEvent.click(within(screen.getByRole('dialog')).getByLabelText('Mia'));
    expect(screen.queryByRole('heading', { name: 'A lovely puzzle' })).not.toBeInTheDocument();
  });
});

describe('personal wishes with a selected family audience', () => {
  it('shares new wishes with invited family by default and allows a narrower audience', async () => {
    registered = true;
    window.history.replaceState({}, '', '/discover');
    const fallback = fetch.getMockImplementation();
    let saved;
    fetch.mockImplementation(async (url, options = {}) => {
      if (url.startsWith('/api/gift-discovery?')) return jsonResponse({ products: [{ name: 'Jewelry', product_url: 'https://store.example.com/jewelry', estimated_price: '25', currency: 'USD' }] });
      if (url === '/api/personal-wishes' && options.method === 'POST') { saved = JSON.parse(options.body); return jsonResponse({ wish: { id: 1 } }, 201); }
      if (url === '/api/personal-wishes') return jsonResponse({ mine: saved ? [{ id: 1, viewer_ids: saved.viewer_ids, item: { id: 50, name: saved.name, recipient: 'Taylor' } }] : [], shared: [], audience: [{ id: 2, name: 'My spouse', families: ['Our family'] }, { id: 3, name: 'My sister', families: ['Our family'] }] });
      return fallback(url, options);
    });
    render(<App />);
    expect(screen.queryByLabelText('Public to invited family members')).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button',{name:'Search gifts'}));
    await screen.findByLabelText('Search for a gift');
    fireEvent.change(screen.getByLabelText('Search for a gift'), { target: { value: 'Jewelry' } });
    fireEvent.click(screen.getByRole('button', { name: 'Find gifts' }));
    fireEvent.click(await screen.findByRole('button', { name: /Save to list/ }));
    await waitFor(() => expect(saved).toBeDefined());
    expect(saved.name).toBe('Jewelry');
    expect(saved.visibility).toBe('followers');
  });
});


describe('family shopping rows', () => {
  it('filters Christmas by budget and rotates through recipients in priority order', async () => {
    registered = true;
    window.history.replaceState({}, '', '/wishlist?section=browse');
    const fallback = fetch.getMockImplementation();
    const make = (id, name, profile_id, priority, price, family, occasion = 'Christmas') => ({ id, name, recipient: 'Person ' + profile_id, profile_id, priority, estimated_price: price, households: [{ id: family, name: 'Family ' + family }], occasions: [occasion], availability: { available: 1, reserved: 0, purchased: 0 } });
    fetch.mockImplementation((url, options) => url.startsWith('/api/shopping?') ? jsonResponse({ items: [make(1, 'Top puzzle', 1, 4, '25', 1), make(2, 'Second puzzle', 1, 3, '30', 1), make(3, 'Storybook', 2, 2, '15', 1), make(4, 'Expensive', 3, 4, '90', 2), make(5, 'Cozy socks', 4, 3, '20', 2), make(6, 'Birthday toy', 5, 4, '10', 2, 'Birthday')] }) : fallback(url, options));
    render(<App />);
    await screen.findByRole('heading', { name: 'Top puzzle' });
    fireEvent.click(screen.getByRole('button',{name:'Search gifts'}));
    fireEvent.change(screen.getByLabelText('Search gifts, people, or families'), { target: { value: 'Christmas' } });
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Filter'}));
    fireEvent.change(within(screen.getByRole('dialog')).getByLabelText('Maximum price'), {target:{value:'50'}});
    expect(screen.queryByRole('heading', { name: 'Expensive' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Birthday toy' })).not.toBeInTheDocument();
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button',{name:'Close'}));
    const names = within(screen.getByLabelText('Followed family / Family 1')).getAllByRole('heading').map(node => node.textContent);
    expect(names).toEqual(['Top puzzle', 'Storybook', 'Second puzzle']);
    expect(within(screen.getByLabelText('Followed family / Family 2')).getByRole('heading', { name: 'Cozy socks' })).toBeInTheDocument();
  });
});


describe('family profile settings', () => {
  it('lets an existing owner identify their adult profile from Settings', async () => {
    registered=true;
    window.history.replaceState({},'', '/settings?tab=family');
    const fallback=fetch.getMockImplementation();
    let identified=false;
    fetch.mockImplementation(async(url,options={})=>{
      if(url==='/api/auth/me')return jsonResponse({user:{id:1,name:'Taylor Example',email:'taylor@example.com'},households:[{id:9,name:'Our family',owner_id:1,role:'owner'}]});
      if(url==='/api/households/9')return jsonResponse({household:{id:9,name:'Our family',owner_id:1,role:'owner'},profiles:[{id:21,display_name:'Taylor',profile_type:'person',is_you:identified}]});
      if(url==='/api/households/9/identify-me'){identified=true;expect(JSON.parse(options.body)).toEqual({profile_id:21});return jsonResponse({profile_id:21,message:'This is your main adult profile.'});}
      return fallback(url,options);
    });
    render(<App/>);
    fireEvent.click(await screen.findByRole('button',{name:'This is me'}));
    expect(await screen.findByText('Taylor (you)')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Our family'})).toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Household management'})).not.toBeInTheDocument();
  });
});

describe('gifting status rows', () => {
  it('shows buying, later and purchased without repeating held or purchased cards', async () => {
    registered = true;
    window.history.replaceState({}, '', '/wishlist?section=plans');
    const fallback = fetch.getMockImplementation();
    const held = {id:81,name:'Held puzzle',recipient:'Mia',availability:{held_by_you:1,available:0}};
    const bought = {id:82,name:'Purchased book',recipient:'Sam',availability:{purchased:1,available:0}};
    fetch.mockImplementation(async (url, options = {}) => {
      if(url==='/api/my-shopping')return jsonResponse({reservations:[{id:1,item:held,status:'reserved',quantity:1},{id:2,item:bought,status:'purchased',quantity:1}]});
      if(url==='/api/co-buy-invitations')return jsonResponse({invitations:[]});
      if(url==='/api/wishlist')return jsonResponse({hearted:[{...held,is_hearted:true}],private_gifts:[{id:3,name:'Later idea',recipient:'Mia',status:'planned'},{id:4,name:'Completed private idea',recipient:'Sam',status:'purchased'}],family_profiles:[]});
      return fallback(url, options);
    });
    render(<App/>);
    expect(await screen.findByText(/^Saved for later/)).toBeInTheDocument();
    expect(screen.queryByRole('heading',{name:'Purchased'})).not.toBeInTheDocument();
    expect(await screen.findByText('Buying now',{selector:'.nav-link'})).toBeInTheDocument();
    expect(await screen.findByRole('heading',{name:'Held puzzle'})).toBeInTheDocument();
    expect(screen.getAllByRole('heading',{name:'Held puzzle'})).toHaveLength(1);
    expect(screen.queryByText('Purchased book')).not.toBeInTheDocument();
    expect(screen.queryByText('Completed private idea')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText(/^Saved for later/));
    expect(await screen.findByText('Later idea')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Past gifts'}));
    expect(await screen.findByText('Purchased book')).toBeInTheDocument();
    expect(screen.getByText('Completed private idea')).toBeInTheDocument();
    expect(screen.getByText('Later idea')).toBeInTheDocument();
  });
});

describe('saved gifts bought by someone else', () => {
  it('keeps the saved heart with a sold overlay and no buying button', async () => {
    registered=true;
    window.history.replaceState({}, '', '/wishlist?section=plans');
    const fallback=fetch.getMockImplementation();
    fetch.mockImplementation(async (url,options={})=>{
      if(url==='/api/wishlist')return jsonResponse({hearted:[{id:90,name:'Saved teddy',recipient:'Mia',is_hearted:true,product_url:'https://example.com/teddy',availability:{available:0,purchased:1,reserved:0}}],private_gifts:[],family_profiles:[]});
      if(url==='/api/my-shopping')return jsonResponse({reservations:[]});
      if(url==='/api/co-buy-invitations')return jsonResponse({invitations:[]});
      return fallback(url,options);
    });
    render(<App/>);
    fireEvent.click(await screen.findByText(/^Saved for later/));
    expect(await screen.findByRole('heading',{name:'Saved teddy'})).toBeInTheDocument();
    expect(screen.getByText('SOLD').closest('.gift-status-overlay')).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Unheart'})).toBeInTheDocument();
    expect(within(screen.getByRole('heading',{name:'Saved teddy'}).closest('.gift-card')).getByRole('button',{name:'Buying now'})).toBeDisabled();
  });
});

describe('incoming follow request alerts',()=>{
 it('refreshes automatically and offers accept and decline in the bell',async()=>{
  registered=true;window.history.replaceState({},'', '/gifting');
  let pending=false;const fallback=fetch.getMockImplementation();const refreshers=[];
  const interval=vi.spyOn(globalThis,'setInterval').mockImplementation((callback,delay)=>{if(delay===15000)refreshers.push(callback);return 12345;});
  fetch.mockImplementation(async(url,options={})=>{
   if(url==='/api/notifications')return jsonResponse({notifications:pending?[{id:'invite-7',invitation_id:7,household_name:'Inviting family',message:'A family follow request',read:false,created_at:'2026-10-23T12:00:00Z'}]:[]});
   if(url==='/api/invitations/accept'){expect(JSON.parse(options.body)).toEqual({invitation_id:7});pending=false;return jsonResponse({});}
   return fallback(url,options);
  });
  render(<App/>);
  await screen.findByRole('button',{name:'Notifications'});
  expect(refreshers.length).toBeGreaterThan(0);pending=true;
  for(const refresh of refreshers)refresh();
  fireEvent.click(await screen.findByRole('button',{name:'Notifications, 1 unread'}));
  expect(await screen.findByText('Sent you a follow request.')).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Decline'})).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button',{name:'Accept'}));
  await screen.findByRole('button',{name:'Notifications'});
  expect(screen.queryByText('Sent you a follow request.')).not.toBeInTheDocument();
  interval.mockRestore();
 });
});

it('keeps purchased gifts in searchable history instead of the gifting page', async()=>{
 registered=true;window.history.replaceState({},'', '/gifting');
 const fallback=fetch.getMockImplementation();
 fetch.mockImplementation((url,options)=>url==='/api/my-shopping'?jsonResponse({reservations:[{id:99,status:'purchased',quantity:1,item:{id:80,name:'Past puzzle',recipient:'Mia',occasions:['Birthday']}}]}):fallback(url,options));
 render(<App/>);
 const historyButton=await screen.findByRole('button',{name:'Past gifts'});
 expect(screen.queryByText('Past puzzle')).not.toBeInTheDocument();
 fireEvent.click(historyButton);
 const dialog=await screen.findByRole('dialog');
 expect(await within(dialog).findByText('Past puzzle')).toBeInTheDocument();
 fireEvent.change(within(dialog).getByLabelText('Search past gifts'),{target:{value:'no match'}});
 expect(within(dialog).queryByText('Past puzzle')).not.toBeInTheDocument();
 expect(within(dialog).getByText('No past gifts match.')).toBeInTheDocument();
 fireEvent.change(within(dialog).getByLabelText('Search past gifts'),{target:{value:'Mia'}});
 fireEvent.change(within(dialog).getByLabelText('Past gift occasion'),{target:{value:'Birthday'}});
 expect(within(dialog).getByText('Past puzzle')).toBeInTheDocument();
});

it('hides empty saved search and opens the shared gift finder from Add gift',async()=>{
 registered=true;window.history.replaceState({},'', '/gifting');
 render(<App/>);
 fireEvent.click(await screen.findByText('Saved for later'));
 const add=await screen.findByRole('button',{name:'Add gift'});
 expect(screen.queryByLabelText('Search saved gifts')).not.toBeInTheDocument();
 fireEvent.click(add);
 const dialog=await screen.findByRole('dialog');
 expect(within(dialog).getByLabelText('Search gifts, people, or families')).toBeInTheDocument();
 expect(await within(dialog).findByRole('heading',{name:'Junior baking kit'})).toBeInTheDocument();
});

it('renders family settings directly without a missing household reference',async()=>{
 registered=true;window.history.replaceState({},'', '/settings?tab=family');
 const fallback=fetch.getMockImplementation();
 fetch.mockImplementation((url,options)=>url==='/api/auth/me'?jsonResponse({user:{id:1,name:'Taylor',email:'taylor@example.com'},households:[{id:9,name:'Our family',role:'owner',owner_id:1}]}):fallback(url,options));
 render(<App/>);
 expect(await screen.findByRole('heading',{name:'Profiles & family'})).toBeInTheDocument();
 expect(screen.getAllByRole('button',{name:'Our family'}).length).toBeGreaterThan(0);
 expect(screen.queryByRole('button',{name:'Send request'})).not.toBeInTheDocument();
});

it('sends an adult family gift as a suggestion instead of adding it directly',async()=>{
 registered=true;window.history.replaceState({},'', '/discover');
 const fallback=fetch.getMockImplementation();let suggestion;
 fetch.mockImplementation((url,options={})=>{
  if(url==='/api/wishlist')return jsonResponse({hearted:[],private_gifts:[],family_profiles:[{id:7,display_name:'Joined adult',household_id:9,household_name:'Our family',can_edit:false,can_suggest:true}]});
  if(url==='/api/profiles/7/wishlists')return jsonResponse({wishlists:[{id:12,title:'Birthday'}]});
  if(url.startsWith('/api/gift-discovery?'))return jsonResponse({products:[{name:'Suggested puzzle',product_url:'https://example.com/puzzle'}]});
  if(url==='/api/profiles/7/suggestions'){suggestion=JSON.parse(options.body);return jsonResponse({message:'Suggestion sent.'},201);}
  return fallback(url,options);
 });
 render(<App/>);fireEvent.click(await screen.findByRole('button',{name:'Search gifts'}));
 fireEvent.change(screen.getByLabelText('Save to'),{target:{value:'family'}});
 fireEvent.change(screen.getByLabelText('For'),{target:{value:'7'}});
 expect(screen.getByText('They will approve this suggestion before it is added.')).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('Search for a gift'),{target:{value:'puzzle'}});
 fireEvent.click(screen.getByRole('button',{name:'Find gifts'}));
 fireEvent.click(await screen.findByRole('button',{name:'Save to list'}));
 expect(await screen.findByText('Suggestion sent.')).toBeInTheDocument();
 expect(suggestion.name).toBe('Suggested puzzle');
 expect(fetch.mock.calls.some(([url,options])=>url==='/api/wishlists/12/items' && options.method==='POST')).toBe(false);
});


it('opens an existing list for editing wishes and keeps its name after renaming',async()=>{
 registered=true;
 window.history.replaceState({},'', '/wishlist');
 const fallback=fetch.getMockImplementation();
 let title='Birthday';
 fetch.mockImplementation(async(url,options={})=>{
  if(url==='/api/auth/me')return jsonResponse({user:{id:1,name:'Taylor',email:'taylor@example.com'},households:[{id:9,name:'Our family',role:'owner',owner_id:1}]});
  if(url==='/api/wishlist')return jsonResponse({hearted:[],private_gifts:[],family_profiles:[{id:7,display_name:'Child',household_id:9,household_name:'Our family',can_edit:true}]});
  if(url==='/api/profiles/7/wishlists')return jsonResponse({wishlists:[{id:31,title}]});
  if(url==='/api/wishlists/31/delivery')return jsonResponse({can_edit:true,address:'',shared:false});
  if(url==='/api/wishlists/31'&&options.method==='PATCH'){title=JSON.parse(options.body).title;return jsonResponse({wishlist:{id:31,title}});}
  return fallback(url,options);
 });
 render(<App/>);
 fireEvent.click(await screen.findByRole('button',{name:'Manage lists'}));
 const dialog=await screen.findByRole('dialog');
 const link=await within(dialog).findByRole('button',{name:'Open list to edit wishes'});
 expect(link).toHaveAttribute('href','/profiles/7?wishlist=31');
 fireEvent.change(within(dialog).getByLabelText('List name'),{target:{value:'Birthday wishes'}});
 fireEvent.click(within(dialog).getByRole('button',{name:'Save list name'}));
 expect(await within(dialog).findByText('List name saved.')).toBeInTheDocument();
 expect(within(dialog).getByLabelText('List name')).toHaveValue('Birthday wishes');
 expect(within(dialog).queryByText(/reset password/i)).not.toBeInTheDocument();
});


it.each([
 {ownPhoto:'/api/uploads/taylor.jpg',activeId:null,expected:'/api/uploads/taylor.jpg'},
 {ownPhoto:null,activeId:null,expected:null},
 {ownPhoto:'/api/uploads/taylor.jpg',activeId:22,expected:'/api/uploads/active.jpg'},
])('uses only the active identity photo in the header: %j',async({ownPhoto,activeId,expected})=>{
 registered=true;window.history.replaceState({},'', '/wishlist');
 const fallback=fetch.getMockImplementation();
 fetch.mockImplementation(async(url,options={})=>{
  if(url==='/api/auth/me')return jsonResponse({user:{id:1,name:'Taylor',browsing_as:activeId?'Alex':'Taylor',active_member_profile_id:activeId},households:[{id:9,name:'Family',role:'owner',photo_path:'/api/uploads/family.jpg'}]});
  if(url==='/api/household-session')return jsonResponse({active_profile_id:activeId,profiles:[{id:22,name:'Alex',is_adult:true,photo_path:'/api/uploads/active.jpg'},{id:21,name:'Taylor',is_you:true,is_adult:true,photo_path:ownPhoto}]});
  return fallback(url,options);
 });
 render(<App/>);
 const menu=await screen.findByRole('button',{name:'Family account menu'});
 fireEvent.click(menu);
 await screen.findByText('Taylor (you)');
 const avatar=menu.querySelector('.family-menu-avatar');
 if(expected){expect(avatar.querySelector('img')).toHaveAttribute('src',expected);fireEvent.error(avatar.querySelector('img'));expect(avatar.querySelector('img')).toBeNull();}
 else {expect(avatar.querySelector('img')).toBeNull();expect(avatar).toHaveTextContent('T');}
});


it('shows profile completion reminders and sends parents straight to the profile editor',async()=>{
 registered=true;window.history.replaceState({},'', '/notifications');
 const fallback=fetch.getMockImplementation();
 fetch.mockImplementation(async(url,options={})=>{
  if(url==='/api/notifications')return jsonResponse({notifications:[],profile_reminders:[{id:'profile-completion-7',profile_completion:true,profile_id:7,message:"Complete Mia's family profile",url:'/profiles/7?edit=1',read:false,created_at:'2026-10-27T12:00:00Z'}]});
  return fallback(url,options);
 });
 render(<App/>);
 expect(await screen.findByText("Complete Mia's family profile")).toBeInTheDocument();
 expect(screen.getByRole('link',{name:'Complete gift profile'})).toHaveAttribute('href','/profiles/7?edit=1');
 expect(screen.queryByRole('button',{name:'Mark read'})).not.toBeInTheDocument();
});


it('filters gifts from multiple followed people by budget and restores every price when cleared',async()=>{
 registered=true;window.history.replaceState({},'', '/gifting');
 const fallback=fetch.getMockImplementation();
 const gift=(id,name,price,family,currency='USD')=>({id,name,recipient:'Person '+id,profile_id:id,estimated_price:price,currency,households:[{id:family,name:'Family '+family}],availability:{available:1,reserved:0,purchased:0}});
 fetch.mockImplementation((url,options)=>url.startsWith('/api/shopping?')?jsonResponse({items:[gift(1,'Small puzzle',10,11),gift(2,'Story book',25,12),gift(3,'Expensive console',500,11),gift(4,'Unpriced wish',null,12),gift(5,'Euro gift',10,12,'EUR')]}):fallback(url,options));
 render(<App/>);
 fireEvent.click(await screen.findByText('Saved for later'));
 fireEvent.click(await screen.findByRole('button',{name:'Add gift'}));
 const dialog=await screen.findByRole('dialog');
 await within(dialog).findByRole('heading',{name:'Expensive console'});
 fireEvent.click(within(dialog).getByRole('button',{name:'Filter'}));
 fireEvent.change(within(dialog).getByLabelText('Maximum price'),{target:{value:'25'}});
 await within(dialog).findByRole('heading',{name:'Small puzzle'});
 expect(within(dialog).getByRole('heading',{name:'Story book'})).toBeInTheDocument();
 for(const name of ['Expensive console','Unpriced wish','Euro gift'])expect(within(dialog).queryByRole('heading',{name})).not.toBeInTheDocument();
 fireEvent.click(within(dialog).getByRole('button',{name:'No budget / show all prices'}));
 for(const name of ['Expensive console','Unpriced wish','Euro gift'])expect(await within(dialog).findByRole('heading',{name})).toBeInTheDocument();
});


it('opens the Advertising portal section from an advertising notification link',async()=>{
 registered=true;window.history.replaceState({},'', '/support?advertising_request=7');
 const fallback=fetch.getMockImplementation();
 fetch.mockImplementation((url,options)=>{
  if(url==='/api/auth/me')return jsonResponse({user:{id:1,name:'Developer',is_support:true,is_superuser:true},households:[]});
  if(url==='/api/support/ads')return jsonResponse({campaigns:[]});
  if(url==='/api/support/advertising-alerts')return jsonResponse({settings:{},mail_available:false});
  if(url==='/api/support/advertising-requests')return jsonResponse({new_count:1,requests:[{id:7,name:'Alex',email:'alex@example.com',message:'Advertising request opened from email',status:'new',email_delivery:'sent',created_at:'2026-10-27T12:00:00Z'}]});
  if(url==='/api/support/staff')return jsonResponse({staff:[]});
  return fallback(url,options);
 });
 render(<App/>);
 expect(await screen.findByText('Advertising request opened from email')).toBeInTheDocument();
 expect(screen.getByRole('region',{name:'Advertising request inbox'})).toBeInTheDocument();
});

it('preserves the advertising notification destination through staff sign-in',async()=>{
 window.history.replaceState({},'', '/support?advertising_request=7');
 render(<App/>);
 await screen.findByRole('heading',{name:'Support portal.'});
 expect(new URLSearchParams(window.location.search).get('next')).toBe('/support?advertising_request=7');
});


it('uses the canonical active user image even when the profile menu is unavailable',async()=>{
 registered=true;window.history.replaceState({},'', '/wishlist');
 const fallback=fetch.getMockImplementation();
 fetch.mockImplementation(async(url,options={})=>{
  if(url==='/api/auth/me')return jsonResponse({user:{id:1,name:'Taylor',browsing_as:'Taylor',active_member_profile_id:null,active_profile:{id:21,name:'Taylor',is_you:true,photo_path:'/api/uploads/my-photo.jpg',avatar_key:'flower'}},households:[]});
  if(url==='/api/household-session')return jsonResponse({error:'Unavailable'},500);
  return fallback(url,options);
 });
 render(<App/>);
 const menu=await screen.findByRole('button',{name:'Family account menu'});
 expect(menu.querySelector('img')).toHaveAttribute('src','/api/uploads/my-photo.jpg');
});

it('keeps the active user signed in when session refresh temporarily fails',async()=>{
 registered=true;window.history.replaceState({},'', '/wishlist');
 const fallback=fetch.getMockImplementation();let failing=false;
 fetch.mockImplementation(async(url,options={})=>url==='/api/auth/me'&&failing?jsonResponse({error:'Temporary outage'},500):fallback(url,options));
 render(<App/>);
 await screen.findByRole('button',{name:'Family account menu'});
 const previousPath=window.location.pathname;
 failing=true;fireEvent.focus(window);
 expect(await screen.findByText('Temporary outage')).toBeInTheDocument();
 expect(screen.getByRole('button',{name:'Family account menu'})).toBeInTheDocument();
 expect(window.location.pathname).toBe(previousPath);
 failing=false;fireEvent.click(screen.getByRole('button',{name:'Try again'}));
 await waitFor(()=>expect(screen.queryByText('Temporary outage')).not.toBeInTheDocument());
});

it('opens a child letter and saves a handwritten wish to that exact list',async()=>{
 registered=true;window.history.replaceState({},'', '/child');
 const fallback=fetch.getMockImplementation();
 let added=null;
 fetch.mockImplementation(async(url,options={})=>{
  if(url==='/api/auth/me')return jsonResponse({user:{id:20,name:'Mia',is_child:true},households:[]});
  if(url==='/api/child/game-notifications')return jsonResponse({notifications:[]});
  if(url==='/api/child/me')return jsonResponse({name:'Mia',pets:[],letters:[{id:5,wishlist_id:42,title:'Santa wishes',sender_name:'Santa'}],wishlists:[{id:10,title:'Everyday',items:[]},{id:42,title:'Santa wishes',items:added?[{id:99,...added}]:[]}]});
  if(url==='/api/child/wishlists/42/items'&&options.method==='POST'){added=JSON.parse(options.body);return jsonResponse({item:{id:99,...added}},201);}
  return fallback(url,options);
 });
 render(<App/>);
 const dialog=await screen.findByRole('dialog');
 expect(within(dialog).getByText('Dear Mia,')).toBeInTheDocument();
 fireEvent.click(within(dialog).getByRole('button',{name:'Write my wishlist'}));
 await waitFor(()=>expect(screen.getByLabelText('My wishlist')).toHaveValue('42'));
 const name=screen.getByLabelText('My wish');
 name.closest('details').open=true;
 fireEvent.change(name,{target:{value:'Bake cookies with Grandma'}});
 fireEvent.change(screen.getByLabelText('Tell us about it'),{target:{value:'Chocolate chip cookies'}});
 fireEvent.submit(name.closest('form'));
 expect(await screen.findByRole('heading',{name:'Bake cookies with Grandma'})).toBeInTheDocument();
 expect(added).toEqual({name:'Bake cookies with Grandma',description:'Chocolate chip cookies'});
});
