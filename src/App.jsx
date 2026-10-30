import {PublicInfo,DemoRegistry,InformationLinks} from './PublicInfo.jsx';
import CommerceAdmin from './CommerceAdmin.jsx';
import AffiliateDisclosure from './AffiliateDisclosure.jsx';
import UniversalGift from './UniversalGift.jsx';
import GiftDetails from './GiftDetails.jsx';
import {storeCatalog,orderProducts} from './lib/storeCatalog.js';
import StoreLogo from './StoreLogo.jsx';
import GiftSummaryRow from './GiftSummaryRow.jsx';
import EditGiftDialog from './EditGiftDialog.jsx';
import WishlistActions from './WishlistActions.jsx';
import MyWishlistLists from './MyWishlistLists.jsx';
import EmailControl,{EmailPreferencesPage} from './EmailControl.jsx';
import FavoriteStoreButton from './FavoriteStoreButton.jsx';
import CreateWishlist from './CreateWishlist.jsx';
export {CreateWishlist};
import ProductActions from './ProductActions.jsx';
import {readNotification,dismissNotification} from './lib/notificationActions.js';
import {GameInvitationPage} from './GameInvitations.jsx';
import ParentPinSettings from './ParentPinSettings.jsx';
import DeleteAccount,{AccountDeletedPage} from './DeleteAccount.jsx';
import FollowedFamilyBrowser from './FollowedFamilyBrowser.jsx';
import ManualGiftEntry from './ManualGiftEntry.jsx';
import {WishlistLetterManager,ChildWishlistLetter} from './WishlistLetters.jsx';
import {BudgetFilters,inBudget,WishlistBudgetSuggestions,WishlistBudgetPreference} from './BudgetTools.jsx';
import {GiftGuide,GiftGuideButton,ProfileCompletion,ProfilePreferencesFields,preferencePayload,DiscoverGiftProfile} from './ProfilePreferences.jsx';
import FamilyRows from './FamilyRows.jsx';
import InstallApp from './InstallApp.jsx';
import {ShoppingProvider,useShoppingState} from './ShoppingState.jsx';
import PurchaseConfirmation from './PurchaseConfirmation.jsx';
import MemberAvatar, {AvatarPicker} from './MemberAvatar.jsx';
import AvatarStudio from './AvatarStudio.jsx';
import DisplayPreferences, {DisplayProvider} from './DisplayPreferences.jsx';
import TreatIdeas from './TreatIdeas.jsx';
import {ListDelivery, GiftDelivery} from './ListDelivery.jsx';
import ChildGameNotifications from './ChildGameNotifications.jsx';
import WishOrganize from './WishOrganize.jsx';
import { createContext, useContext, useEffect, useMemo, useRef, useState, useId } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Container,
  Dropdown,
  Form,
  Modal,
  Nav,
  Navbar,
  OverlayTrigger,
  Tooltip,
  Row,
  Spinner,
} from "react-bootstrap";
import { api, clearCsrfToken, mediaUrl } from "./lib/api.js";

import { AdSlot, AdvertisePage, AdvertisingReview, AdvertisingInquiryForm } from "./Advertising.jsx";

import { SharedThemePicker, ThemeStudio } from "./SharedThemes.jsx";
import WishAudiencePicker from "./WishAudiencePicker.jsx";
import AppNavigation from "./AppNavigation.jsx";
import {GiftSuggestions} from "./FamilyAccountTools.jsx";
import FamilyEditor from "./FamilyEditor.jsx";
import { usePhotoCrop } from "./PhotoCropper.jsx";
import FollowRequestActions from "./FollowRequestActions.jsx";
import FamilyInvites, { InviteRequestComposer, InvitationInbox } from "./FamilyInvites.jsx";
import GiftGamesPage from "./GiftGames.jsx";
import HelpAssistant, { HelpChatLogs } from "./HelpAssistant.jsx";
import { MoneyPanel, AccountsPanel } from "./MoneyPanel.jsx";

const SessionContext = createContext(null);
const useSession = () => useContext(SessionContext);

function RequestFamilyPreview({notification}) {
 const [open,setOpen]=useState(false);
 const name=notification.household_name || 'Family';
 return <><button type="button" className="request-family-preview" aria-label={'View '+name} onClick={()=>setOpen(true)}><span className="request-family-avatar">{notification.family_photo?<img src={mediaUrl(notification.family_photo)} alt=""/>:name.slice(0,1)}</span><strong>{name}</strong></button><Modal show={open} onHide={()=>setOpen(false)} centered><Modal.Header closeButton><Modal.Title>{name}</Modal.Title></Modal.Header><Modal.Body className="text-center">{notification.family_photo?<img className="request-family-large" src={mediaUrl(notification.family_photo)} alt={name+' family photo'}/>:<div className="request-family-large request-family-placeholder" aria-hidden="true">{name.slice(0,1)}</div>}</Modal.Body></Modal></>;
}

function ShoppingBagIcon({filled=false}) {return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M5 7h14l1 14H4L5 7Z" fill={filled?"currentColor":"none"} fillOpacity={filled?"1":undefined}/><path d="M8 8V6a4 4 0 0 1 8 0v2"/></svg>;}

function HeaderShoppingBag() {
 const [open,setOpen]=useState(false),[privateCount,setPrivateCount]=useState(0);const shopping=useShoppingState();const count=(shopping?.rows.filter(r=>r.status==='reserved').length||0)+privateCount;
 useEffect(()=>{let active=true;const load=()=>api('/wishlist').then(data=>{if(active)setPrivateCount((data.private_gifts||[]).filter(item=>item.buying_now).length);}).catch(()=>{});load();window.addEventListener('wishlist-updated',load);window.addEventListener('shopping-updated',load);return()=>{active=false;window.removeEventListener('wishlist-updated',load);window.removeEventListener('shopping-updated',load);};},[]);
 return <><Button variant="link" className="header-shopping-bag" aria-label={'Buying now, '+count+' gifts'} title="Buying now" onClick={()=>setOpen(true)}><ShoppingBagIcon filled={count>0}/>{count>0 && <Badge pill bg="danger">{count}</Badge>}</Button><Modal show={open} onHide={()=>setOpen(false)} centered size="lg" scrollable><Modal.Header closeButton><Modal.Title>Your bag &amp; saved items</Modal.Title></Modal.Header><Modal.Body><WishlistPage area="gifting" embedded initialTab="buying"/><Button as={Link} to="/gifting" variant="link" onClick={()=>setOpen(false)}>View saved items and past gifts</Button></Modal.Body></Modal></>;
}

function NotificationBell({onUnreadChange}) {
  const { user, refresh: refreshSession } = useSession();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const load = async () => { try { const result=await api('/notifications');setRows([...(result.notifications || []),...(result.profile_reminders || [])]); setError(''); } catch (err) { setError(err.message); } };
  useEffect(() => {
    const refresh = () => { if(document.visibilityState !== 'hidden') load(); };
    refresh(); const timer=setInterval(refresh,15000);
    window.addEventListener('notifications-updated',refresh);window.addEventListener('wishlist-updated',refresh);window.addEventListener('focus',refresh);document.addEventListener('visibilitychange',refresh);
    return ()=>{clearInterval(timer);window.removeEventListener('notifications-updated',refresh);window.removeEventListener('wishlist-updated',refresh);window.removeEventListener('focus',refresh);document.removeEventListener('visibilitychange',refresh);};
  }, [user.id]);
  const unread = rows.filter((row) => !row.read).length;
  useEffect(()=>{onUnreadChange?.(unread);},[unread,onUnreadChange]);
  return <Dropdown align="end" onToggle={(open) => { if (open) load(); }}><Dropdown.Toggle variant="link" className="notification-bell" aria-label={unread ? 'Notifications, ' + unread + ' unread' : 'Notifications'}><svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></svg>{unread > 0 && <Badge pill bg="danger" className="notification-count">{unread > 99 ? '99+' : unread}</Badge>}</Dropdown.Toggle><Dropdown.Menu className="notification-menu"><div className="d-flex justify-content-between align-items-center px-3 py-2"><strong>Notifications</strong><Link to="/settings?tab=notifications" aria-label="Notification settings" title="Notification settings">?</Link></div>{error ? <p className="px-3 small">Could not load notifications. Try See all.</p> : rows.length ? rows.slice(0, 4).map((row) => row.invitation_id ? <div key={row.id} className="px-3 py-2 notification-request" onClick={()=>readNotification(row).then(()=>setRows(current=>current.map(item=>item.id===row.id?{...item,read:true}:item))).catch(err=>setError(err.message))}><RequestFamilyPreview notification={row}/><p className="small mb-1">{row.join_family?'Invited you to join their family.':'Sent you a follow request.'}</p><FollowRequestActions invitationId={row.invitation_id} onChanged={async()=>{await load();await refreshSession();}}/></div> : <div key={row.id} className="d-flex align-items-center"><Dropdown.Item as={Link} to={row.url || "/notifications"} className="notification-preview" onClick={()=>readNotification(row).then(()=>setRows(current=>current.map(item=>item.id===row.id?{...item,read:true}:item))).catch(err=>setError(err.message))}><strong>{row.message}</strong><small>{row.household_name}{!row.read ? ' / Unread' : ' / Read'}</small></Dropdown.Item>{(row.profile_completion||row.price_request)&&<Button type="button" size="sm" variant="link" onClick={()=>dismissNotification(row).then(()=>setRows(current=>current.filter(item=>item.id!==row.id))).catch(err=>setError(err.message))}>Ignore</Button>}</div>) : <p className="px-3 small text-secondary">You are all caught up.</p>}<Dropdown.Divider /><Dropdown.Item as={Link} to="/notifications">See all notifications</Dropdown.Item><Dropdown.Item disabled={!rows.length} onClick={async()=>{try{await api("/notifications/clear",{method:"POST"});setRows([]);await refreshSession();window.dispatchEvent(new Event("notifications-updated"));}catch(err){setError(err.message);}}}>Clear all notifications</Dropdown.Item></Dropdown.Menu></Dropdown>;
}

function HouseholdModeControl({ onSignOut, notificationCount=0 }) {
  const { user, refresh, households } = useSession();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [pin, setPin] = useState('');
  const [pinChallenge,setPinChallenge]=useState(''),[pinNotice,setPinNotice]=useState('');
  const recoverPin=async()=>{setBusy(true);setError('');try{const r=await api('/household-session/pin/reset',{method:'POST',body:JSON.stringify({})});setPinChallenge(r.challenge_id);setPinNotice(r.message);}catch(err){setError(err.message);}finally{setBusy(false);}};

  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async () => { setOpen(true); setError(''); setPin(''); setPassword(''); try { setData(await api(user.is_child ? '/child/profiles' : '/household-session')); } catch(err) { setError(err.message); } };
  const run = async (path, body) => { setBusy(true); setError(''); try { const result = await api(path, { method: 'POST', body: JSON.stringify(body) }); await refresh(); setOpen(false); setPin(''); setPassword(''); navigate(result.status === 'child' ? '/child' : result.profile_id ? '/profiles/' + result.profile_id : '/'); } catch(err) { setError(err.message); } finally { setBusy(false); } };
  const [menuProfiles, setMenuProfiles] = useState(null);
  const canListProfiles = !user.is_child && !user.is_support;
  const menuRequest = useRef(0);
  const identityKey = user.id + ':' + (user.active_member_profile_id || 'self');
  const loadMenuProfiles = () => {
    const requestId = ++menuRequest.current;
    if (canListProfiles) api('/household-session').then(result => {
      if (requestId === menuRequest.current) setMenuProfiles({...result, identityKey});
    }).catch(() => { if (requestId === menuRequest.current) setMenuProfiles(null); });
  };
  useEffect(() => { setMenuProfiles(null); loadMenuProfiles(); return () => { menuRequest.current++; }; }, [user.id, user.active_member_profile_id, user.browsing_as, households]);
  const activeProfile = user.active_profile !== undefined ? user.active_profile : menuProfiles?.identityKey === identityKey
    ? menuProfiles.profiles?.find(profile => user.active_member_profile_id
      ? String(profile.id) === String(user.active_member_profile_id)
      : profile.is_you === true)
    : null;
  const photo = activeProfile?.photo_path || (!user.active_member_profile_id ? user.photo_path : null);
  const [failedPhoto, setFailedPhoto] = useState(null);
  return <><Dropdown align="end" onToggle={open => { if (open) loadMenuProfiles(); }}><Dropdown.Toggle variant="link" className="family-menu-toggle" aria-label="Family account menu"><span className="family-menu-avatar">{!user.is_child && (photo || (activeProfile?.avatar_key && activeProfile.avatar_key !== 'flower')) ? <MemberAvatar name={activeProfile?.name || user.name} photo={photo && photo !== failedPhoto ? photo : undefined} avatarKey={activeProfile?.avatar_key} className="family-menu-avatar-art" /> : <span aria-hidden="true">{(user.browsing_as || user.name || 'G').slice(0, 1)}</span>}</span>{!user.is_child&&!user.is_support&&notificationCount>0&&<Badge pill bg="danger" className="mobile-notification-count">{notificationCount>99?'99+':notificationCount}</Badge>}<span>{user.is_child ? user.name : (user.browsing_as || user.name)}</span></Dropdown.Toggle><Dropdown.Menu className="profile-account-menu">{!user.is_child&&!user.is_support&&<Dropdown.Item as={Link} to="/notifications" className="mobile-notifications-link"><span>Notifications</span>{notificationCount>0&&<Badge pill bg="danger">{notificationCount>99?'99+':notificationCount}</Badge>}</Dropdown.Item>}{canListProfiles && menuProfiles?.profiles?.length > 0 && <div className="menu-profile-list" role="group" aria-label="Profiles">{menuProfiles.profiles.map(profile => <Dropdown.Item key={profile.id} className="menu-profile" active={profile.id === menuProfiles.active_profile_id} disabled={busy || profile.uses_separate_login} onClick={() => profile.is_adult ? run('/household-session/switch', { profile_id: profile.id }) : load()}><MemberAvatar name={profile.name} photo={profile.photo_path} avatarKey={profile.avatar_key}/><span><strong>{profile.name}{profile.is_you ? ' (you)' : ''}</strong><small>{profile.uses_separate_login ? 'Has their own login' : profile.is_adult ? 'Adult' : 'Child mode'}</small></span></Dropdown.Item>)}<Dropdown.Divider /></div>}{!user.is_support && (!user.is_child || user.child_mode_locked) && <Dropdown.Item onClick={load}>{user.is_child ? 'Choose a child / exit child mode' : 'Switch profile'}</Dropdown.Item>}{!user.is_child && !user.is_support && <><Dropdown.Item as={Link} to="/settings">Settings</Dropdown.Item></>}<Dropdown.Divider /><Dropdown.Item onClick={onSignOut}>Sign out</Dropdown.Item></Dropdown.Menu></Dropdown><Modal show={open} onHide={() => setOpen(false)} centered><Modal.Header closeButton><Modal.Title>{user.is_child ? 'Parent PIN' : 'Choose a family profile'}</Modal.Title></Modal.Header><Modal.Body><ErrorAlert message={error} />{user.is_child ? <><div className="member-switch-grid mb-4">{data?.profiles?.map(profile => <Button key={profile.id} variant="outline-success" disabled={busy || profile.active} onClick={() => run('/child/profiles/switch', { child_id: profile.id })}><MemberAvatar name={profile.name} photo={profile.photo_path} avatarKey={profile.avatar_key}/><strong>{profile.name}</strong>{profile.active && <small>That's me!</small>}</Button>)}</div><Form onSubmit={e => { e.preventDefault(); (async()=>{if(pinChallenge){try{await api('/household-session/pin/reset/confirm',{method:'POST',body:JSON.stringify({challenge_id:pinChallenge,code:pin})});setPinChallenge('');}catch(err){setError(err.message);return;}}run('/household-session/exit-child',{pin});})(); }}>{pinNotice && <Alert variant="info">{pinNotice}</Alert>}<Form.Group controlId="exit-parent-pin"><Form.Label>Parent PIN to leave child mode</Form.Label><Form.Control type="password" inputMode="numeric" autoComplete="off" required value={pin} onChange={e => setPin(e.target.value)} /></Form.Group><Button type="submit" disabled={busy} className="mt-3">Return to household</Button><Button type="button" variant="link" disabled={busy} onClick={recoverPin}>Forgot PIN?</Button></Form></> : data && <><p className="small text-secondary">Adults use their own login after joining. Family connections are shared.</p><div className="member-switch-grid">{data.profiles.map(profile => <Button key={profile.id} variant="outline-success" disabled={busy || profile.uses_separate_login} onClick={() => run('/household-session/switch', { profile_id: profile.id })}><MemberAvatar name={profile.name} photo={profile.photo_path} avatarKey={profile.avatar_key}/><strong>{profile.name}{profile.is_you ? " (you)" : ""}</strong><small>{profile.is_adult ? profile.is_guardian ? "Adult / parent" : "Adult" : "Child mode"}</small></Button>)}</div><p className="small mt-3 mb-0"><Link to="/settings?tab=account&section=parent-pin" onClick={() => setOpen(false)}>Set / change parent PIN in Settings</Link></p></>}</Modal.Body></Modal></>;
}

function BuyingNotice() {
  const { user } = useSession();
  const [show, setShow] = useState(false);
  const location = useLocation();
  useEffect(() => { const notify = () => setShow(true); window.addEventListener('gift-held', notify); return () => window.removeEventListener('gift-held', notify); }, []);
  useEffect(() => setShow(false), [location.pathname, location.search]);
  if (!show || !user || user.is_child || user.is_support) return null;
  return <Container className="pt-3"><Alert variant="info" dismissible onClose={() => setShow(false)}><strong>Reserved for up to 24 hours.</strong> <Link to="/buying-now">Buying now</Link>: mark purchased or remove it. Unpurchased holds expire automatically. Heart to save for later.</Alert></Container>;
}

function SiteHeader() {
  const {pathname}=useLocation();
  const supportArea=/^\/support(?:\/|$)/.test(pathname);
  const { user, signOut } = useSession();
  const navigate = useNavigate();
  const [notificationCount,setNotificationCount]=useState(0);
  const [error, setError] = useState("");
  const handleSignOut = async () => {
    setError("");
    try {
      await signOut();
    } catch (err) {
      setError(err.message);
    } finally {
      navigate(user?.is_support ? "/support/login" : "/login", { replace: true });
    }
  };
  return (
    <>
      <Navbar expand="md" className="site-navbar">
      <Container>
        <Navbar.Brand as={Link} to="/" className="brand">
          <span aria-hidden="true">✿</span> Gather &amp; Gift
        </Navbar.Brand>
        <InstallApp key={supportArea?'support':'family'} support={supportArea} hidden={supportArea && pathname!=='/support/login'}/>
        {user && (
          <>
            
            <div id="main-navigation" className="header-actions">
              <Nav className="ms-auto align-items-md-center gap-md-2">
                {user.is_child ? <Nav.Link as={Link} to="/child">My wishes</Nav.Link> : user.is_support ? (
                  <Nav.Link as={Link} to="/support">Support portal</Nav.Link>
                ) : (
                  <>
                    
                    <HeaderShoppingBag />
                    <div className="header-notification-bell"><NotificationBell onUnreadChange={setNotificationCount}/></div>
                  </>
                )}
                <HouseholdModeControl onSignOut={handleSignOut} notificationCount={notificationCount}/>
              </Nav>
            </div>
          </>
        )}
      </Container>
      </Navbar>
      {user && !user.is_child && !user.is_support && <AppNavigation/>}
      {error && <Container className="pt-3"><Alert variant="danger" role="alert">{error}</Alert></Container>}
    </>
  );
}

function Loading({ label = "Just a moment…" }) {
  return <div className="loading-state" role="status"><Spinner animation="border" size="sm" /> <span>{label}</span></div>;
}

function ErrorAlert({ message, onDismiss }) {
  return message ? <Alert variant="danger" dismissible={Boolean(onDismiss)} onClose={onDismiss}>{message}</Alert> : null;
}

function PageHelpAssistant({user}) {
  const {pathname}=useLocation();
  if ((!user && ['/', '/demo', '/about', '/contact', '/privacy', '/terms', '/affiliate-disclosure'].includes(pathname)) || user?.is_child || user?.is_support) return null;
  return <HelpAssistant signedIn={Boolean(user)}/>;
}

function App() {
  const [user, setUser] = useState(null);
  const [households, setHouseholds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [bootError, setBootError] = useState("");

  const refreshRequest = useRef(0);
  const currentUser = useRef(user);
  currentUser.current = user;
  const refresh = async () => {
    const requestId = ++refreshRequest.current;
    try {
      const result = await api("/auth/me");
      if (requestId !== refreshRequest.current) return;
      setUser(result.user);
      setHouseholds(result.households || []);
      setBootError("");
    } catch (error) {
      if (requestId !== refreshRequest.current) return;
      if (error.status === 401) {
        if (currentUser.current) setBootError("Please sign in again.");
        setUser(null);
        setHouseholds([]);
        clearCsrfToken();
        return;
      }
      throw error;
    }
  };

  const initialize = () => {
    setLoading(true);
    setBootError("");
    refresh().catch((error) => setBootError(error.message)).finally(() => setLoading(false));
  };
  useEffect(() => { initialize(); }, []);

  useEffect(() => {
    if (!user) return;
    let active = true;
    const sync = () => {
      if (document.visibilityState === 'hidden') return;
      refresh().catch(error => { if (active) setBootError(error.message); });
    };
    window.addEventListener('focus', sync);
    document.addEventListener('visibilitychange', sync);
    return () => { active = false; window.removeEventListener('focus', sync); document.removeEventListener('visibilitychange', sync); };
  }, [user?.id]);

  const signOut = async () => {
    refreshRequest.current++;
    try { await api("/auth/logout", { method: "POST" }); }
    finally { refreshRequest.current++; clearCsrfToken(); setUser(null); setHouseholds([]); }
  };

  const context = useMemo(() => ({ user, households, setHouseholds, setUser, refresh, signOut }), [user, households]);
  if (loading) return <main className="app-main"><Loading label="Loading your family space…" /></main>;

  return (
    <SessionContext.Provider value={context}><ShoppingProvider key={user?.id || 'guest'} user={user}><DisplayProvider>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <div className={"app-shell theme-" + (user?.is_child ? "kids" : ["christmas", "halloween", "custom"].includes(user?.theme_key) ? user.theme_key : "classic")} style={user?.shared_theme ? { '--shared-bg':user.shared_theme.background, '--shared-fg':user.shared_theme.foreground, '--shared-accent':user.shared_theme.accent } : undefined} data-shared-theme={Boolean(user?.shared_theme)}>
        <SiteHeader />{user?.shared_theme?.art && <div className="shared-theme-art" aria-hidden="true"><img src={mediaUrl(user.shared_theme.art)} alt="" /></div>}<BuyingNotice />
        <main className="app-main">
          {bootError === "Please sign in again." ? <SignInRedirect /> : bootError && <Container className="pt-3"><Alert variant="warning" role="alert">{bootError} <Button variant="outline-success" size="sm" onClick={initialize}>Try again</Button></Alert></Container>}
          {user?.is_child ? <Routes><Route path="/child" element={<ChildWishlistPage key={user.id} />} /><Route path="*" element={<Navigate to="/child" replace />} /></Routes> : <Routes>
            <Route path="/email-preferences/:token" element={<EmailPreferencesPage/>}/><Route path="/game-invitations/:gameId/:token" element={<GameInvitationPage user={user}/>}/><Route path="/child/login" element={user ? <Navigate to="/" replace /> : <ChildLoginPage />} />
            <Route path="/login" element={<FamilyAuthRoute mode="login" />} />
            <Route path="/register" element={<FamilyAuthRoute mode="register" />} />
            <Route path="/approve-change" element={<ChangeApprovalPage />} />
            <Route path="/advertise" element={<AdvertisePage />} /><Route path="/demo" element={<DemoRegistry/>}/>{[['/about','about'],['/contact','contact'],['/privacy','privacy'],['/terms','terms'],['/affiliate-disclosure','disclosure']].map(([path,page])=><Route key={path} path={path} element={<PublicInfo page={page}/>} />)}
            <Route path="/forgot-password" element={<PasswordRecoveryPage />} />
            <Route path="/account-deleted" element={<AccountDeletedPage />} />
            <Route path="/reset-password" element={<PasswordRecoveryPage reset />} />
            <Route path="/support/login" element={user?.is_support ? <Navigate to="/support" replace /> : <AuthPage mode="support" />} />
            <Route path="/support" element={user?.is_support ? <SupportPortal /> : <Navigate to={"/support/login?next="+encodeURIComponent("/support"+window.location.search)} replace />} />
            <Route path="/support/accept-invitation/:token" element={<AcceptStaffInvitationPage />} />
            <Route path="/" element={user?.is_support ? <Navigate to="/support" replace /> : user ? <WishlistPage /> : <LandingPage />} />
            <Route path="/households/:householdId" element={user && !user.is_support ? <HouseholdPage /> : <Navigate to="/login" replace />} />
            <Route path="/profiles/:profileId" element={user && !user.is_support ? <ProfilePage /> : <Navigate to="/login" replace />} />
            <Route path="/shopping" element={<Navigate to="/wishlist?section=browse" replace />} />
            <Route path="/wishlist" element={user && !user.is_support ? <Navigate to={new URLSearchParams(window.location.search).get('section')==='plans'?'/gifting':new URLSearchParams(window.location.search).get('section')==='browse'?'/following':'/'} replace/> : <Navigate to="/login" replace/>}/>
            <Route path="/games" element={user && !user.is_support ? <FollowingPage games /> : <Navigate to="/login" replace />} />
            <Route path="/following" element={user && !user.is_support ? <FollowingPage /> : <Navigate to="/login" replace />} />
            <Route path="/discover" element={user && !user.is_support ? <DiscoverPage /> : <Navigate to="/login" replace />} />
            <Route path="/gifting" element={user && !user.is_support ? <WishlistPage area="gifting" /> : <Navigate to="/login" replace />} />
            <Route path="/buying-now" element={user && !user.is_child && !user.is_support ? <Navigate to="/gifting" replace /> : <Navigate to="/login" replace />} />
            <Route path="/my-shopping" element={<Navigate to="/gifting" replace />} />
            <Route path="/notifications" element={user && !user.is_support ? <NotificationsPage /> : <Navigate to="/login" replace />} />
            <Route path="/settings" element={user && !user.is_support ? <SettingsPage /> : <Navigate to="/login" replace />} />
            <Route path="/accept-invitation/:token" element={<AcceptInvitationPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>}
        </main>
        <footer className="site-footer"><span>&copy; {new Date().getFullYear()} Gather &amp; Gift. All rights reserved.</span><span>Made for thoughtful giving.</span>{!user?.is_child && <Link to={user ? '/settings?tab=help' : '/advertise'}>{user ? 'Help & support' : 'Advertise with us'}</Link>}{!user?.is_child&&!user?.is_support && <a href="/support/login" title="Sign in to the staff support and developer portal.">Developer / support login</a>}{user?.is_support && <Link to="/support">Support portal</Link>}{!user?.is_child&&<InformationLinks/>}</footer>
        <PageHelpAssistant user={user}/>
        </div>
      </BrowserRouter>
    </DisplayProvider></ShoppingProvider></SessionContext.Provider>
  );
}

const LANDING_TITLE = "Gather & Gift | Free Family Gift Registry & Wishlists";
const LANDING_DESCRIPTION = "Save wishes from different stores, share lists with family and friends, and find gifts they actually want. Your family gift registry, all in one place.";

function setMeta(selector, attr, value) {
  const el = document.head.querySelector(selector);
  if (el) el.setAttribute(attr, value);
}

function useLandingSeo() {
  useEffect(() => {
    const previous = document.title;
    document.title = LANDING_TITLE;
    setMeta('meta[name="description"]', "content", LANDING_DESCRIPTION);
    return () => { document.title = previous; };
  }, []);
}

function GiftBox() {
  return (
    <div className="gift-box" aria-hidden="true">
      <span className="gift-sparkle s1">✦</span><span className="gift-sparkle s2">✿</span><span className="gift-sparkle s3">✦</span>
      <div className="gift-bow"><i /><i /></div>
      <div className="gift-lid" />
      <div className="gift-body" />
    </div>
  );
}

function LandingPage() {
  useLandingSeo();
  return (
    <Container className="hero-wrap landing-gift">
      <div className="confetti" aria-hidden="true">{Array.from({ length: 14 }, (_, i) => <i key={i} />)}</div>
      <Row className="align-items-center g-5">
        <Col lg={7}>
          <Badge bg="light" text="success" className="eyebrow">🎀 Free family gift registry &amp; wishlists</Badge>
          <h1 className="hero-title">Make giving feel like <em>family.</em></h1>
          <p className="hero-copy">Save wishes from different stores for yourself and your loved ones. Share lists, check their favorites, and give gifts they actually want.</p>
          <ul className="landing-chips" aria-label="What you can do">
            <li>🎁 Gift registry</li><li>🎄 Holiday wish list</li><li>🔀 Gift exchange</li><li>🎂 Birthday lists</li>
          </ul>
          <div className="d-flex flex-wrap gap-3 mt-4">
            <Button as={Link} to="/register" variant="success" size="lg">Create your family space - free</Button>
            <Button as={Link} to="/login" variant="outline-success" size="lg">I have an account</Button>
          </div>
          <p className="hero-note mt-4">Free signup &middot; You choose who sees your wishes</p>
        </Col>
        <Col lg={5}>
          <GiftBox />
          <Card className="hero-card">
            <Card.Body>
              <div className="hero-card-sparkle" aria-hidden="true">✦</div>
              <p className="small-label">From their wishlist</p>
              <h2>A little wish.<br /><span>A gift they really want.</span></h2>
              <div className="sample-gift"><span className="gift-icon" aria-hidden="true">🎁</span><div><strong>Saturday baking set</strong><small>For Mia · Birthday list</small></div><span className="sample-heart">♥</span></div>
              <div className="sample-gift"><span className="gift-icon" aria-hidden="true">📚</span><div><strong>One more storybook</strong><small>For Grandpa · Everyday</small></div><span className="sample-heart">♥</span></div>
              <div className="hero-doodle" aria-hidden="true">a little wish, a lot of love</div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
      <section className="landing-benefits" aria-labelledby="landing-benefits-title">
        <p className="small-label">Less guessing. More happy surprises.</p>
        <h2 id="landing-benefits-title">One place for every thoughtful gift.</h2>
        <Row className="g-4 mt-2">
          {[
            ["01", "Wishes worth remembering", "Save gift ideas from different stores for yourself and your loved ones."],
            ["02", "Bring your family together", "Invite loved ones to help manage your registry. Adults can use their own sign-in while staying connected to the same family."],
            ["03", "Shop their list, skip the guesswork", "Follow family and friends, check their sizes and favorites, and pick something they want or need. Reserve gifts to avoid duplicates."],
          ].map(([number, title, copy]) => <Col md={4} key={number}><div className="landing-benefit"><span className="landing-step" aria-hidden="true">{number}</span><h3>{title}</h3><p>{copy}</p></div></Col>)}
        </Row>
      </section>
      <section className="landing-uses" aria-labelledby="landing-uses-title">
        <h2 id="landing-uses-title">Wishlists for every celebration</h2>
        <Row className="g-4 mt-1">
          {[
            ["🎁", "Gift registry", "One gift registry for birthdays, weddings, showers and everyday wishes. Share what you actually want with family and friends."],
            ["🎄", "Holiday wish list", "Save Christmas and holiday gift ideas from different stores, then share one wishlist."],
            ["🔀", "Gift exchange", "Plan Secret Santa or a family gift exchange. Keep wishes together and avoid duplicate gifts."],
            ["⭐", "Everyday wishlist", "Keep a little list of wants and needs, ready for the next thoughtful gift."],
          ].map(([icon, title, copy]) => <Col sm={6} lg={3} key={title}><article className="landing-use"><span aria-hidden="true">{icon}</span><h3>{title}</h3><p>{copy}</p></article></Col>)}
        </Row>
      </section>
      <section className="landing-free" aria-labelledby="landing-free-title">
        <div><p className="small-label">A little about how we keep it free</p><h2 id="landing-free-title">Your account is free.</h2><p>Our plan is to fund the app through ads and retailer referral fees. Stores may pay us when you shop through our links. Your account stays free.</p></div>
        <Button as={Link} to="/register" variant="success" size="lg">Sign up for free</Button>
      </section>
      <ContactArea />
      <AdvertisingSpace />
    </Container>
  );
}

function SignInRedirect() {
  const location = useLocation();
  if (["/", "/login", "/register", "/support/login", "/child/login"].includes(location.pathname)) return null;
  return <Navigate to="/login" replace state={{ message: "Please sign in again." }} />;
}

function FamilyAuthRoute({ mode }) {
  const { user } = useSession();
  const location = useLocation();
  const next = new URLSearchParams(location.search).get("next");
  const destination = next?.startsWith("/") && !next.startsWith("//") && !next.includes("\\") ? next : "/";
  return user ? <Navigate to={user.is_support ? "/support" : destination} replace /> : <AuthPage mode={mode} />;
}

function AuthPage({ mode }) {
  const [showPassword, setShowPassword] = useState(false);
  const isRegister = mode === "register";
  const isSupport = mode === "support";
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { refresh } = useSession();
  const navigate = useNavigate();
  const location = useLocation();

  const submitting = useRef(false);
  const submit = async (event) => {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    const submitted = new FormData(event.currentTarget);
    setError("");
    setBusy(true);
    try {
      await api(isRegister ? "/auth/register" : isSupport ? "/auth/support/login" : "/auth/login", {
        method: "POST",
        body: JSON.stringify({...form, email: submitted.get("email") ?? form.email, password: submitted.get("password") ?? form.password}),
      });
      await refresh();
      const requestedPath = new URLSearchParams(location.search).get("next");
      if (isSupport) navigate(requestedPath?.startsWith("/") && !requestedPath.startsWith("//") ? requestedPath : "/support", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      submitting.current = false;
      setBusy(false);
    }
  };

  return (
    <Container className="auth-wrap">
      <Card className="auth-card">
        <Card.Body>
          <p className="small-label">{isSupport ? "Dedicated support staff sign-in" : isRegister ? "Start your family space" : "Welcome back"}</p>
          <h1>{isSupport ? "Support portal." : isRegister ? "A little more together." : "Come on in."}</h1>
          <p className="text-secondary">{isSupport ? "This separate staff account cannot sign in to a family registry." : isRegister ? "Create a free account to gather your family's gift ideas." : "Your family's thoughtful little corner is waiting."}</p>
          {location.state?.message && <Alert variant="info">{location.state.message}</Alert>}
          <ErrorAlert message={error} onDismiss={() => setError("")} />
          <Form onSubmit={submit}>
            {isRegister && <Form.Group controlId="register-name" className="mb-3"><Form.Label>Your name</Form.Label><Form.Control autoComplete="name" required maxLength={120} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Form.Group>}
            <Form.Group controlId="account-email" className="mb-3"><Form.Label>Email address</Form.Label><Form.Control name="email" type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Form.Group>
            <Form.Group controlId="account-password" className="mb-3"><div className="d-flex justify-content-between align-items-center gap-2"><Form.Label>Password</Form.Label>{!isRegister && <Link className="small" to={"/forgot-password" + location.search + (isSupport ? (location.search ? "&" : "?") + "portal=support" : "")}>Forgot password?</Link>}</div><div className="input-group"><Form.Control type={showPassword ? "text" : "password"} name="password" autoComplete={isRegister ? "new-password" : "current-password"} minLength={isRegister ? 10 : undefined} required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /><Button type="button" variant="outline-secondary" aria-label={showPassword ? "Hide password" : "Show password"} aria-pressed={showPassword} aria-controls="account-password" title={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(value => !value)}><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>{showPassword && <path d="m3 3 18 18"/>}</svg></Button></div><Form.Text className="text-muted">{isRegister ? "At least 10 characters." : "Your password is kept private."}</Form.Text></Form.Group>
            <Button type="submit" variant="success" className="w-100 mt-2" disabled={busy}>{busy ? "One moment…" : isRegister ? "Create my account" : "Sign in"}</Button>
          </Form>
          {!isSupport && <p className="text-center mt-4 mb-0">{isRegister ? "Already have an account?" : "New to Gather & Gift?"} <Link to={(isRegister ? "/login" : "/register") + location.search}>{isRegister ? "Sign in" : "Create an account"}</Link></p>}
        </Card.Body>
      </Card>
    </Container>
  );
}

function PasswordRecoveryPage({ reset = false }) {
  return reset ? <LegacyPasswordRecoveryPage reset /> : <RecoveryCodePage />;
}

function RecoveryCodePage() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [challenge, setChallenge] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const submit = async e => { e.preventDefault(); setBusy(true); setError(''); try { if (!challenge) { const result = await api('/auth/recovery-code', { method: 'POST', body: JSON.stringify({ email }) }); setChallenge(result.challenge_id); setMessage(result.message); } else { const result = await api('/auth/recovery-code/verify', { method: 'POST', body: JSON.stringify({ email, code, challenge_id: challenge }) }); const next = params.get('next'); navigate('/reset-password?token=' + encodeURIComponent(result.token) + (next ? '&next=' + encodeURIComponent(next) : '')); } } catch(err) { setError(err.message); } finally { setBusy(false); } };
  return <Container className="auth-wrap"><Card className="auth-card"><Card.Body><p className="small-label">Household account recovery</p><h1>Forgot your password?</h1><p>Use the main household email. We will send a one-time, six-digit code that expires in 10 minutes.</p><ErrorAlert message={error} />{message && <Alert variant="info">{message}</Alert>}<Form onSubmit={submit}><Form.Group controlId="recovery-email" className="mb-3"><Form.Label>Main email address</Form.Label><Form.Control type="email" required readOnly={Boolean(challenge)} autoComplete="email" value={email} onChange={e => setEmail(e.target.value)} /></Form.Group>{challenge && <Form.Group controlId="recovery-code" className="mb-3"><Form.Label>One-time code</Form.Label><Form.Control required inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e => setCode(e.target.value)} /></Form.Group>}<Button type="submit" disabled={busy}>{busy ? 'Please wait...' : challenge ? 'Verify code' : 'Send one-time code'}</Button>{challenge && <Button title="Start a new email verification request for this account change." type="button" variant="link" onClick={() => { setChallenge(''); setCode(''); setMessage(''); }}>Request a new code</Button>}</Form><Link to="/login" className="d-block mt-3">Back to sign in</Link></Card.Body></Card></Container>;
}

function ChangeApprovalPage() {
  const [params] = useSearchParams();
  const { refresh } = useSession();
  const [details, setDetails] = useState(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const id = params.get('id'), token = params.get('token');
  useEffect(() => { if (!id || !token) { setError('Approval link is missing. Open the link in the main email.'); return; } api('/auth/change-approval/details', { method: 'POST', body: JSON.stringify({ id, token }) }).then(setDetails).catch(err => setError(err.message)); }, [id, token]);
  const decide = async approve => { setBusy(true); setError(''); try { const result = await api('/auth/change-approval', { method: 'POST', body: JSON.stringify({ id, token, approve }) }); setMessage(result.message); await refresh(); } catch(err) { setError(err.message); } finally { setBusy(false); } };
  return <Container className="auth-wrap"><Card className="auth-card"><Card.Body><p className="small-label">Main email approval</p><h1>Approve this change?</h1>{error && <Alert variant="danger">{error}</Alert>}{message ? <><Alert variant="success">{message}</Alert><Link to="/login">Return to sign in</Link></> : details && <><p>{details.purpose === 'password_change' ? 'A household password change was requested. Your current password remains active until you approve.' : 'A family photo change was requested. Review the new photo before approving.'}</p>{details.purpose === 'family_photo_change' && <img className="approval-photo mb-3" alt="Proposed family photo" referrerPolicy="no-referrer" src={mediaUrl('/api/auth/change-approval/photo?' + new URLSearchParams({ id, token }))} />}<div className="d-flex flex-wrap gap-2"><Button disabled={busy} onClick={() => decide(true)}>Yes, approve</Button><Button disabled={busy} variant="outline-danger" onClick={() => decide(false)}>No, cancel</Button></div><p className="small mt-3 mb-0">This approval expires in 30 minutes and works once. Ignoring it leaves the current password or photo unchanged.</p></>}</Card.Body></Card></Container>;
}

function LegacyPasswordRecoveryPage({ reset = false }) {
  const [params] = useSearchParams();
  const { refresh } = useSession();
  const token = params.get('token') || '';
  const requestedNext = params.get('next') || '';
  const next = requestedNext.startsWith('/accept-invitation/') && !requestedNext.includes('\\') ? requestedNext : '';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loginPath, setLoginPath] = useState(params.get('portal') === 'support' ? '/support/login' : '/login');
  const submit = async (event) => {
    event.preventDefault(); setError('');
    if (reset && password !== confirmation) { setError('The passwords do not match.'); return; }
    setBusy(true);
    try {
      const result = await api(reset ? '/auth/reset-password' : '/auth/forgot-password', { method: 'POST', body: JSON.stringify(reset ? { token, password } : { email, next }) });
      setMessage(result.message);
      if (reset) { setPassword(''); setConfirmation(''); setLoginPath(result.login_path || '/login'); await refresh(); }
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  return <Container className="auth-wrap"><Card className="auth-card"><Card.Body><p className="small-label">Account recovery</p><h1>{reset ? 'Choose a new password.' : 'Forgot your password?'}</h1><p className="text-secondary">{reset ? 'Use at least 10 characters. After resetting, sign in again on your devices.' : 'Enter your account email and we will send a private reset link that expires in 30 minutes.'}</p><ErrorAlert message={error || (reset && !token ? 'This reset link is missing or invalid. Request a new one.' : '')} />{message ? <><Alert variant="success">{message}</Alert>{reset ? <Button as={Link} to={loginPath + (next ? '?next=' + encodeURIComponent(next) : '')} variant="success" className="w-100">Sign in with new password</Button> : <Button variant="outline-success" onClick={() => setMessage('')}>Request another link</Button>}</> : (!reset || token) && <Form onSubmit={submit}>{reset ? <><Form.Group controlId="reset-password" className="mb-3"><Form.Label>New password</Form.Label><Form.Control type="password" autoComplete="new-password" required minLength={10} maxLength={1024} value={password} onChange={(e) => setPassword(e.target.value)} /></Form.Group><Form.Group controlId="reset-confirmation" className="mb-3"><Form.Label>Confirm new password</Form.Label><Form.Control type="password" autoComplete="new-password" required minLength={10} maxLength={1024} value={confirmation} onChange={(e) => setConfirmation(e.target.value)} /></Form.Group></> : <Form.Group controlId="recovery-email" className="mb-3"><Form.Label>Email address</Form.Label><Form.Control type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></Form.Group>}<Button type="submit" variant="success" className="w-100" disabled={busy}>{busy ? 'Please wait...' : reset ? 'Reset password' : 'Send reset link'}</Button></Form>}<p className="mt-3 mb-0 text-center"><Link to={reset ? '/forgot-password' + (next ? '?next=' + encodeURIComponent(next) : '') : loginPath + (next ? '?next=' + encodeURIComponent(next) : '')}>{reset ? 'Request a new reset link' : 'Back to sign in'}</Link></p></Card.Body></Card></Container>;
}

function ChildLoginPage() {
  const { refresh } = useSession();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    try { await api('/child/login', { method: 'POST', body: JSON.stringify(form) }); await refresh(); navigate('/child', { replace: true }); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  return <Container className="auth-wrap"><Card className="auth-card"><Card.Body><p className="small-label">Your own wish corner</p><h1>Child sign-in</h1><p>Use the username and password your parent gave you.</p><ErrorAlert message={error} /><Form onSubmit={submit}><Form.Group controlId="child-username" className="mb-3"><Form.Label>Username</Form.Label><Form.Control required autoComplete="username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Form.Group><Form.Group controlId="child-password" className="mb-3"><Form.Label>Password</Form.Label><Form.Control required type="password" autoComplete="current-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Form.Group><Button type="submit" className="w-100" disabled={busy}>{busy ? 'Signing in...' : 'Open my wishes'}</Button></Form><p className="small mt-3">Forgot your password? Ask your parent to reset it.</p><Link to="/login">Parent sign-in</Link></Card.Body></Card></Container>;
}

function ChildProfileStrip() {
  const { user, refresh } = useSession();
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (user.child_mode_locked) api('/child/profiles').then(data => setProfiles(data.profiles)).catch(err => setError(err.message)); }, [user.id]);
  const choose = async child_id => { setBusy(true); setError(''); try { await api('/child/profiles/switch', { method:'POST', body:JSON.stringify({ child_id }) }); await refresh(); } catch(err) { setError(err.message); } finally { setBusy(false); } };
  return <><div className="kids-profile-strip" aria-label="Choose a child profile">{profiles.map(p => <button key={p.id} disabled={busy} aria-pressed={p.active} onClick={() => choose(p.id)}><MemberAvatar name={p.name} photo={p.photo_path} avatarKey={p.avatar_key}/>{p.name}</button>)}</div><ErrorAlert message={error} /></>;
}

function ChildWishlistPage() {
  const { user, refresh } = useSession();
  const [data, setData] = useState({ wishlists: [] });
  const [selected, setSelected] = useState('');
  const [gift, setGift] = useState({ name: '', description: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [petGifts, setPetGifts] = useState({});
  const [search,setSearch]=useState(''),[products,setProducts]=useState([]),[saved,setSaved]=useState([]);
  const searchGifts=async e=>{e.preventDefault();setBusy(true);setError('');setProducts([]);setSaved([]);try{setProducts((await api('/child/gift-search?q='+encodeURIComponent(search))).products);}catch(err){setError(err.message);}finally{setBusy(false);}};
  const saveProduct=async index=>{setBusy(true);setError('');try{await api('/child/wishlists/'+selected+'/items',{method:'POST',body:JSON.stringify({product_index:index})});setSaved(prev=>[...prev,selected+':'+index]);await load();setNotice('Your wish has been added!');}catch(err){setError(err.message);}finally{setBusy(false);}};
  const [link, setLink] = useState('');
  const addLink = async e => { e.preventDefault(); setBusy(true); setError(''); setNotice(''); try { await api('/child/wishlists/' + selected + '/links', { method: 'POST', body: JSON.stringify({ url: link.trim() }) }); setLink(''); await load(); setNotice('Your wish has been added!'); } catch(err) { setError(err.message); } finally { setBusy(false); } };
  const [busy, setBusy] = useState(false);
  const load = async () => { const result = await api('/child/me'); setData(result); setSelected((id) => result.wishlists.some((row) => String(row.id) === id) ? id : String(result.wishlists[0]?.id || '')); };
  useEffect(() => { setSelected('');setNotice('');load().catch((err) => setError(err.message)); }, [user.id]);
  const add = async (name, description='') => { setBusy(true); setError(''); setNotice('');
    try { await api('/child/wishlists/' + selected + '/items', { method: 'POST', body: JSON.stringify({ name, description }) }); setGift({ name: '', description: '' }); await load(); setNotice('Your wish has been added!'); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const addPetGift = async (event, pet) => {
    event.preventDefault();
    const name = petGifts[pet.id] || '';
    if (!name.trim()) return;
    setBusy(true); setError(''); setNotice('');
    try {
      await api('/child/pets/' + pet.id + '/items', { method: 'POST', body: JSON.stringify({ name: name.trim(), description: '' }) });
      setPetGifts(current => ({ ...current, [pet.id]: '' }));
      await load();
      setNotice('Added to ' + pet.name + "'s wishes.");
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const removePetGift = async (pet, item) => {
    setBusy(true); setError(''); setNotice('');
    try {
      await api('/child/pets/' + pet.id + '/items/' + item.id, { method: 'DELETE' });
      await load();
      setNotice('Removed from ' + pet.name + "'s wishes.");
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const wishlist = data.wishlists.find((row) => String(row.id) === selected);
  const activeLetter=(data.letters||[]).find(letter=>String(letter.wishlist_id)===selected);
  return <Container className="page-wrap child-wishes"><p className="small-label">Ideas to make you smile</p><h1 className="page-title">My wishes</h1><ChildProfileStrip /><ChildWishlistLetter key={user.id} letters={data.letters||[]} childName={data.name||user.name} onChoose={setSelected}/>{data.controls?.game_invites && <ChildGameNotifications key={user.id}/>}<p>Write your wishes here. Your parent chooses which extra activities you can use.</p><ErrorAlert message={error} />{notice && <Alert variant="success">{notice}</Alert>}{data.wishlists.length ? <>{data.wishlists.length>1 && <Form.Group controlId="child-approved-list" className="mb-4"><Form.Label>My wishlist</Form.Label><Form.Select value={selected} onChange={(e) => setSelected(e.target.value)}>{data.wishlists.map((row) => <option key={row.id} value={row.id}>{row.title}</option>)}</Form.Select></Form.Group>}<Card className={"create-card mb-4"+(activeLetter?" wishlist-letter":"")}><Card.Body>{activeLetter&&<div className="mb-4"><p className="letter-dear">Dear {activeLetter.sender_name},</p><h2>{activeLetter.title}</h2><p>Here are the things I am wishing for! Every wish you add is saved to this letter.</p></div>}<h2>Find a wish</h2>{data.controls?.web_search && <><Form onSubmit={searchGifts} className="d-flex gap-2 mb-3"><Form.Control aria-label="Search kids gifts" type="search" required maxLength={120} placeholder="Try teddy bears or building sets" value={search} onChange={e=>setSearch(e.target.value)}/><Button type="submit" disabled={busy || !search.trim()}>Search</Button></Form><Row className="g-3 mb-4">{products.map(p=><Col xs={6} md={4} key={p.index}><Card className="gift-card"><Card.Body>{p.thumbnail && <img src={p.thumbnail} alt="" loading="lazy" className="wishlist-gift-image"/>}<h3 className="item-title" title={p.name}>{p.name}</h3><Button aria-label={"Save "+p.name} aria-pressed={saved.includes(selected+':'+p.index)} disabled={busy || saved.includes(selected+':'+p.index)} onClick={()=>saveProduct(p.index)}><HeartIcon filled={saved.includes(selected+':'+p.index)}/></Button></Card.Body></Card></Col>)}</Row></>}{data.controls?.product_links && <Form onSubmit={addLink} className="mb-4"><Form.Group controlId="child-product-link"><Form.Label>Paste or drop a product link</Form.Label><Form.Control type="url" required value={link} placeholder="https://..." onChange={e => setLink(e.target.value)} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); setLink((e.dataTransfer.getData('text/uri-list').split('\n').find(line => line && !line.startsWith('#')) || e.dataTransfer.getData('text/plain')).trim()); }} /><Form.Text>The gift details are filled in automatically. Ask your parent if a link does not work.</Form.Text></Form.Group><Button type="submit" aria-label="Save product link" title="Save gift" className="mt-2" disabled={busy || !link.trim().startsWith('https://')}><HeartIcon/></Button></Form>}<details className="child-manual-wish my-4"><summary>Can't find it? Write your own wish</summary><Form className="mt-3" onSubmit={e=>{e.preventDefault();if(gift.name.trim())add(gift.name.trim(),gift.description);}}><Form.Group controlId="child-manual-name" className="mb-3"><Form.Label>My wish</Form.Label><Form.Control required maxLength={200} placeholder="I wish for..." value={gift.name} onChange={e=>setGift({...gift,name:e.target.value})}/></Form.Group><Form.Group controlId="child-manual-description" className="mb-3"><Form.Label>Tell us about it</Form.Label><Form.Control as="textarea" maxLength={2000} value={gift.description} onChange={e=>setGift({...gift,description:e.target.value})}/></Form.Group><Button type="submit" disabled={busy||!gift.name.trim()}>Add my wish</Button></Form></details><p>Pick something you love!</p><div className="d-flex flex-wrap gap-2">{['Dinosaur book', 'Building set', 'Art supplies', 'Board game', 'Puzzle', 'Storybook', 'Stuffed animal', 'Sports ball'].map(name => <Button key={name} type="button" variant="outline-success" disabled={busy || wishlist?.items.some(item => item.name === name)} aria-pressed={Boolean(wishlist?.items.some(item => item.name === name))} onClick={() => add(name)}><HeartIcon filled={Boolean(wishlist?.items.some(item=>item.name===name))}/> {name}</Button>)}</div></Card.Body></Card><h2>{wishlist?.title}</h2><Row className="g-3">{wishlist?.items.map((item) => <Col md={6} key={item.id}><Card className="gift-card"><Card.Body><h3 className="item-title" title={item.name}>{item.name}</h3><p>{item.description}</p></Card.Body></Card></Col>)}</Row>{wishlist?.items.length === 0 && <p>Your first wish can go here.</p>}</> : <p>Your wish space is loading. Please try again.</p>}{data.controls?.manage_pets && data.pets?.length > 0 && <section className="mt-5"><p className="small-label">Family pets</p><h2>Pet wishlists</h2><Row className="g-3">{data.pets.map(pet => <Col md={6} key={pet.id}><Card className="create-card h-100"><Card.Body><div className="d-flex align-items-center gap-3 mb-3"><MemberAvatar name={pet.name} photo={pet.photo_path} avatarKey={pet.avatar_key}/><h3 className="mb-0">{pet.name}</h3></div><Form onSubmit={event => addPetGift(event, pet)} className="d-flex gap-2"><Form.Control aria-label={"Add a wish for " + pet.name} maxLength={200} required value={petGifts[pet.id] || ''} onChange={event => setPetGifts(current => ({ ...current, [pet.id]: event.target.value }))}/><Button type="submit" disabled={busy}>Add</Button></Form><ul className="list-unstyled mt-3 mb-0">{pet.items.map(item => <li className="d-flex justify-content-between align-items-center gap-2 py-2 border-bottom" key={item.id}><span>{item.name}</span><Button variant="outline-danger" size="sm" disabled={busy} aria-label={"Remove " + item.name + " from " + pet.name + "'s wishlist"} onClick={() => removePetGift(pet, item)}>Remove</Button></li>)}</ul>{pet.items.length === 0 && <p className="small text-secondary mt-3 mb-0">No wishes for {pet.name} yet.</p>}</Card.Body></Card></Col>)}</Row></section>}<p className="small text-secondary mt-4">Ask your parent for help with sharing, changing wishes, or allowing extra activities.</p></Container>;
}


function FamilyEmailSearch() {
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setMatches([]);
    setError("");
    if (query.trim().length < 3) return;
    const timer = setTimeout(() => {
      api('/households/search?q=' + encodeURIComponent(query.trim())).then((data) => {
        if (active) setMatches(data.households);
      }).catch((err) => { if (active) setError(err.message); });
    }, 250);
    return () => { active = false; clearTimeout(timer); };
  }, [query]);
  return <Form.Group className="mb-4" controlId="family-email-search"><Form.Label>Find a family by a parent's email</Form.Label><Form.Control type="search" autoComplete="off" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Start typing a parent or household head email" aria-describedby="family-search-help" /><Form.Text id="family-search-help">Search families you have access to. Enter at least 3 characters.</Form.Text><div aria-live="polite">{matches.map((home) => <div key={home.id + home.email}><Link to={'/households/' + home.id}>{home.name} ? {home.email}</Link></div>)}{/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(query.trim()) && !matches.length && <div className="mt-2"><Link to={"/settings?tab=family&invite_email=" + encodeURIComponent(query.trim())}>No shared family found. Invite by email</Link></div>}{error && <ErrorAlert message={error} />}</div></Form.Group>;
}

export const FAMILY_RELATIONSHIPS = [
  ["employee", "Employee"], ["colleague", "Colleague"], ["manager", "Manager"], ["team_member", "Team member"],
  ["family_member", "Family member"], ["dad", "Dad"], ["mom", "Mom"], ["parent", "Parent"],
  ["son", "Son"], ["daughter", "Daughter"], ["child", "Child"], ["brother", "Brother"],
  ["sister", "Sister"], ["sibling", "Sibling"], ["cousin", "Cousin"], ["grandpa", "Grandpa"],
  ["grandma", "Grandma"], ["grandparent", "Grandparent"], ["grandchild", "Grandchild"],
  ["aunt", "Aunt"], ["uncle", "Uncle"], ["niece", "Niece"], ["nephew", "Nephew"],
  ["partner", "Partner"], ["friend", "Friend"], ["other", "Other"],
];
export function BirthdayInput({ value, onChange, label = "Birthday" }) {
  const parts = (value || "").split("-");
  const month = parts.length >= 2 ? parts[parts.length - 2] : "";
  const day = parts.length >= 2 ? parts[parts.length - 1] : "";
  const maxDay = month ? new Date(2000, Number(month), 0).getDate() : 31;
  return <fieldset className="birthday-input"><legend>{label} <span className="text-secondary fw-normal small">(month and day only)</span></legend><div className="d-flex gap-2"><Form.Select aria-label={label + " month"} value={month} onChange={(e) => { const selected = e.target.value; const max = selected ? new Date(2000, Number(selected), 0).getDate() : 31; onChange(selected || day ? selected + '-' + (day && Number(day) > max ? String(max) : day) : ''); }}><option value="">Month</option>{Array.from({ length: 12 }, (_, i) => <option key={i} value={String(i + 1).padStart(2, '0')}>{new Date(2000, i, 1).toLocaleDateString(undefined, { month: 'long' })}</option>)}</Form.Select><Form.Select aria-label={label + " day"} value={day} onChange={(e) => onChange(month || e.target.value ? month + '-' + e.target.value : '')}><option value="">Day</option>{Array.from({ length: maxDay }, (_, i) => <option key={i} value={String(i + 1).padStart(2, '0')}>{i + 1}</option>)}</Form.Select></div><Button type="button" variant="link" size="sm" className="p-0 mt-1" onClick={() => onChange('')}>Clear birthday</Button></fieldset>;
}

function completeBirthday(value) {
  if (!value) return null;
  if (!/^\d{2}-\d{2}$/.test(value)) throw new Error("Choose both a birthday month and day, or clear the birthday.");
  return value;
}
function birthdayLabel(value) {
  const parts = value.split('-');
  return new Date(2000, Number(parts[parts.length - 2]) - 1, Number(parts[parts.length - 1])).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function RelationshipSelect({ value, onChange, label, disabled, company = false }) {
  const workplace = ["employee", "colleague", "manager", "team_member", "other"];
  const options = FAMILY_RELATIONSHIPS.filter(([key]) => company ? workplace.includes(key) : !workplace.slice(0, 4).includes(key));
  return <Form.Select aria-label={label} disabled={disabled} value={value || (company ? "employee" : "family_member")} onChange={(e) => onChange(e.target.value)}>{options.map(([key, name]) => <option key={key} value={key}>{name}</option>)}</Form.Select>;
}


function AdvertisingSpace({ query = '' }) {
  const location = useLocation();
  if (location.pathname !== '/') return null;
  return <AdSlot placement="wishlist" query={query} compact hideEmpty />;
}

function ContactArea() {
 return <section id="contact" className="landing-free"><div><p className="small-label">Get in touch</p><h2>Have a question about advertising?</h2><p>Tell us about your business. Our team will get back to you by email.</p><Button as={Link} to="/advertise" className="my-3">Create an advertising campaign</Button><AdvertisingInquiryForm/></div></section>;
}

function GiftRail({ title, children }) {
  const rail = useRef(null);
  const move = direction => { const element = rail.current; if (element) element.scrollBy({ left: direction * element.clientWidth * .8, behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }); };
  return <><div className="gift-rail-controls"><span>Swipe or scroll for more</span><Button type="button" variant="outline-secondary" size="sm" aria-label={'Previous gifts in ' + title} onClick={() => move(-1)}>&larr;</Button><Button type="button" variant="outline-secondary" size="sm" aria-label={'Next gifts in ' + title} onClick={() => move(1)}>&rarr;</Button></div><div ref={rail} className="gift-rail compact-gift-rail" tabIndex={0} aria-label={title}>{children}</div></>;
}

function GiftDashboardRows({ showFamilies = false, excludePersonal = false, scope = "all", householdId = null, groupByOccasion = false, searchOnly = false, buttonLabel = "Search gifts", triggerId = null, hideTrigger = false, budgetFilter = null, onBudgetChange = null }) {
  const { households } = useSession();
  const [searchOpen,setSearchOpen]=useState(false);
  const [items, setItems] = useState([]);
  const [mine, setMine] = useState([]);
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState('priority');
  const [filter, setFilter] = useState('all');
  const [localBudget,setLocalBudget]=useState(''),[localMinimum,setLocalMinimum]=useState(''),[localCurrency,setLocalCurrency]=useState('USD');
  const budget=budgetFilter?.maximum??localBudget,minimumBudget=budgetFilter?.minimum??localMinimum,budgetCurrency=budgetFilter?.currency??localCurrency;
  const setBudget=value=>onBudgetChange?onBudgetChange(current=>({...current,maximum:value})):setLocalBudget(value);
  const setMinimumBudget=value=>onBudgetChange?onBudgetChange(current=>({...current,minimum:value})):setLocalMinimum(value);
  const setBudgetCurrency=value=>onBudgetChange?onBudgetChange(current=>({...current,currency:value})):setLocalCurrency(value);
  const searchRequest=useRef(0);
  const [occasionFilter, setOccasionFilter] = useState('');
  const [onePerPerson, setOnePerPerson] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const load = async () => {
    const requestId=++searchRequest.current;
    const params=new URLSearchParams({sort:'priority',q:query});
    if(scope==='following')params.set('scope','following');
    if(budget!=='')params.set('max_price',budget);
    if(minimumBudget!=='')params.set('min_price',minimumBudget);
    if(budget!==''||minimumBudget!=='')params.set('currency',budgetCurrency);
    try{const result=await api('/shopping?'+params);if(requestId===searchRequest.current){setItems(result.items||[]);setError('');}}catch(e){if(requestId===searchRequest.current)setError(e.message);}finally{if(requestId===searchRequest.current)setLoading(false);}
  };
  const loadRef=useRef(load);loadRef.current=load;
  useEffect(() => { if(showFamilies)api('/personal-wishes').then(data=>setMine((data.mine||[]).map(w=>w.item))).catch(()=>{});const refresh=()=>loadRef.current();refresh();window.addEventListener('wishlist-updated',refresh);window.addEventListener('shopping-updated',refresh);window.addEventListener('focus',refresh);return()=>{window.removeEventListener('wishlist-updated',refresh);window.removeEventListener('shopping-updated',refresh);window.removeEventListener('focus',refresh);searchRequest.current++;};},[households.map(h=>h.id+':'+h.role).join(',')]);
  useEffect(()=>{const timer=setTimeout(()=>loadRef.current(),250);return()=>clearTimeout(timer);},[query,budget,minimumBudget,budgetCurrency]);
  const searchWords=query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  const matches = (item) => { const text = [item.name, item.recipient, item.store_name, ...(item.households || []).map(h => h.name), ...(item.occasions || [])].join(' ').toLowerCase(); return searchWords.every(word => text.includes(word)); };
  const visible = items.filter(item => householdId == null || (item.households || []).some(h=>String(h.id)===String(householdId))).filter(item => scope==='all' || (scope==='following' && item.followed_by_you) || (item.households || []).some(home=>{const own=households.some(h=>String(h.id)===String(home.id) && ['owner','admin','family_member'].includes(h.role));return scope==='own'?own:!own;})).filter(item => !excludePersonal || !item.personal_wish).filter(matches).filter(i => !occasionFilter || (i.occasions || []).some(o => o.toLowerCase().includes(occasionFilter))).filter(i => filter === 'held' ? i.availability?.held_by_you : filter === 'hearted' ? i.is_hearted : true).filter(i=>inBudget(i,{minimum:minimumBudget,maximum:budget,currency:budgetCurrency})).sort((a,b) => sort === 'price' ? (Number(a.estimated_price ?? Infinity) - Number(b.estimated_price ?? Infinity)) : sort === 'recent' ? String(b.created_at).localeCompare(String(a.created_at)) : (b.priority || 0) - (a.priority || 0));
  const groups = new Map();
  visible.filter(item => groupByOccasion || !item.is_hearted).forEach(item => {
    const homes = groupByOccasion ? (item.occasions?.length ? item.occasions : ['Everyday']).map(name=>({id:name,name})) : item.households?.length ? item.households : [{ id: 'personal', name: 'Wishes shared privately with us' }];
    homes.forEach(home => { const key = String(home.id); if (!groups.has(key)) groups.set(key, { name: home.name, items: [] }); groups.get(key).items.push(item); });
  });
  const arrange = (gifts) => {
    if (!onePerPerson) return gifts;
    const people = new Map(); gifts.forEach(item => { const key = item.profile_id || item.recipient; if (!people.has(key)) people.set(key, []); people.get(key).push(item); });
    const result = []; while ([...people.values()].some(list => list.length)) people.forEach(list => { if (list.length) result.push(list.shift()); }); return result;
  };
  const row = (title, gifts, key) => <section className="dashboard-section" key={key || title}><div className="section-heading"><h2>{title}</h2><small>{gifts.length} wishes</small></div><GiftRail title={title}>{gifts.map(item => <Card className="gift-card" key={item.id}><Card.Body><GiftCardContent item={item} onReserve={async () => { try { await api('/items/' + item.id + '/reservations', { method: 'POST', body: JSON.stringify({ quantity: 1, reuse_existing: true }) }); await load(); } catch(e) { setError(e.message); } }} onReserveRefresh={load} /><div className="mt-3"><PriorityGifts value={item.priority}/></div></Card.Body></Card>)}</GiftRail></section>;
  return <>{scope==='following'&&!searchOnly&&<BudgetFilters minimum={minimumBudget} maximum={budget} currency={budgetCurrency} onMinimum={setMinimumBudget} onMaximum={setBudget} onCurrency={setBudgetCurrency} onClear={()=>{setMinimumBudget('');setBudget('');}} prefix="following-inline-budget"><Form.Group controlId="following-inline-search" className="mb-3"><Form.Label>Search followed wishes</Form.Label><Form.Control type="search" value={query} onChange={e=>setQuery(e.target.value)}/></Form.Group></BudgetFilters>}<Button hidden={hideTrigger} id={triggerId || undefined} className={hideTrigger?"d-none":"mb-3"} onClick={()=>setSearchOpen(true)}>{buttonLabel}</Button><Modal show={searchOpen} onHide={()=>setSearchOpen(false)} size="xl" centered scrollable><Modal.Header closeButton><Modal.Title>Search gifts</Modal.Title></Modal.Header><Modal.Body><Form className="dashboard-filters" onSubmit={e => e.preventDefault()}><Form.Group controlId="dashboard-search"><Form.Label>Search gifts, people, or families</Form.Label><Form.Control type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Try Christmas, a gift, or a family name" /></Form.Group><Form.Group controlId="dashboard-occasion"><Form.Label>Occasion</Form.Label><Form.Select value={occasionFilter} onChange={e => setOccasionFilter(e.target.value)}><option value="">All occasions</option>{["Christmas", "Birthday", "Anniversary", "Halloween", "Easter", "Hanukkah", "Diwali", "Eid", "Wedding", "Graduation"].map(name => <option key={name} value={name.toLowerCase()}>{name}</option>)}</Form.Select></Form.Group><Form.Group controlId="dashboard-sort"><Form.Label>Sort gifts</Form.Label><Form.Select value={sort} onChange={e => setSort(e.target.value)}><option value="priority">Highest priority</option><option value="price">Lowest price</option><option value="recent">Newest first</option></Form.Select></Form.Group><Form.Group controlId="dashboard-filter"><Form.Label>Show</Form.Label><Form.Select value={filter} onChange={e => setFilter(e.target.value)}><option value="all">All shared gifts</option><option value="hearted">Hearted for later</option><option value="held">On hold by me</option></Form.Select></Form.Group><BudgetFilters minimum={minimumBudget} maximum={budget} currency={budgetCurrency} onMinimum={setMinimumBudget} onMaximum={setBudget} onCurrency={setBudgetCurrency} onClear={()=>{setMinimumBudget('');setBudget('');}} prefix="dashboard-budget"/><p className="small">{scope==='following'?'Search across everyone you follow.':'Search across shared wishes you can view.'}</p><Form.Check id="one-gift-per-person" label="Show each person?s top choice first" checked={onePerPerson} onChange={e => setOnePerPerson(e.target.checked)} /><p className="small mb-0">Heart to save for later. Choose Buying now when you are ready.</p></Form><ErrorAlert message={error}/>{loading?<Loading label="Finding gifts..."/>:row("Results",visible)}{!loading && !visible.length && <p>No matching gifts.</p>}</Modal.Body></Modal>{!searchOnly && <><ErrorAlert message={error} />{loading && <Loading label="Gathering your gift lists..." />}{!groupByOccasion && visible.some(i => i.is_hearted) && row('Your favorites', visible.filter(i => i.is_hearted))}{showFamilies && <section className="dashboard-section"><div className="section-heading"><h2>My wishlist</h2><Link to="/wishlist?section=personal">View / edit my wishes</Link></div><div className="gift-rail">{mine.filter(matches).map(item => <Card className="gift-card" key={item.id}><Card.Body><GiftIdentity item={item} /><h3 className="item-title" title={item.name}>{item.name}</h3><Button as={Link} to="/wishlist?section=personal" variant="outline-success">View / edit wish</Button></Card.Body></Card>)}{!mine.length && <p>Add your first wish to start your list.</p>}</div></section>}{showFamilies && <div className="dashboard-shortcuts"><Button as={Link} to="/wishlist?section=personal" variant="success">My wishes</Button><Button as={Link} to="/wishlist?section=plans" variant="outline-success">Saved items</Button><Button as={Link} to="/settings?tab=family" variant="outline-success">Invite or find families</Button></div>}{showFamilies && <section className="dashboard-section"><h2>My families & companies</h2><div className="family-rail">{households.filter(h => h.name.toLowerCase().includes(query.toLowerCase())).map(h => <HouseholdCard key={h.id} household={h} />)}</div></section>}{[...groups.entries()].sort(([a],[b])=>Number(households.some(h=>String(h.id)===b && ['owner','admin','family_member'].includes(h.role)))-Number(households.some(h=>String(h.id)===a && ['owner','admin','family_member'].includes(h.role)))).map(([key,g]) => row(groupByOccasion ? g.name : (households.some(h=>String(h.id)===key && ['owner','admin','family_member'].includes(h.role))?'My family / ':'Followed family / ')+g.name, arrange(g.items), key))}{!loading && !error && !visible.length && <p className="empty-state">No matching shared wishes. Try another search or invite your family to share their lists.</p>}<AdvertisingSpace query={[query, occasionFilter].filter(Boolean).join(" ")} /></>}</>;
}

function DashboardPage({ manageOnly = false }) {
  const [registryType, setRegistryType] = useState("family");
  const { user, households, setHouseholds, refresh } = useSession();
  const [name, setName] = useState("");
  const [profiles, setProfiles] = useState([{ display_name: "", profile_type: "person", birthday: "" }]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const create = async (event) => {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await api("/households", {
        method: "POST",
        body: JSON.stringify({
          name,
          registry_type: registryType,
          ...(registryType === "family" ? { self_profile_index: "new" } : {}),
          profiles: profiles.filter((profile) => profile.display_name.trim()).map((profile) => ({ ...profile, birthday: completeBirthday(profile.birthday) || "" })),
        }),
      });
      setHouseholds([...households, result.household]);
      if (result.self_profile_id) await refresh();
      setName("");
      setProfiles([{ display_name: "", profile_type: "person", birthday: "" }]);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Container className={manageOnly ? "p-0" : "page-wrap"}>
{!manageOnly && (<div className="welcome-line"><div><p className="small-label">Your family, all in one place</p><h1>Good to see you, {user?.name?.split(" ")[0]} <span aria-hidden="true">✿</span></h1><p className="text-secondary mb-0">A thoughtful little space for the people you love.</p></div><Button as={Link} to="/wishlist?section=browse" variant="outline-success">Browse gift ideas <span aria-hidden="true">→</span></Button></div>)}
      {!manageOnly && <><FamilyInvites households={households} /><GiftDashboardRows showFamilies /></>}{(manageOnly || !households.length) && <details open={!households.length} className="section-block"><summary className="fw-semibold mb-3">Manage circles or create a registry</summary><section>
        <div className="section-heading"><div><p className="small-label">Your circles</p><h2>Households &amp; companies</h2></div><Badge bg="light" text="success" pill>{households.length} {households.length === 1 ? "registry" : "registries"}</Badge></div>
        <ErrorAlert message={error} onDismiss={() => setError("")} />
        <FamilyEmailSearch />{!households.length && <div className="empty-state"><span aria-hidden="true">🏡</span><h3>Your family space starts here</h3><p>Create a household to start sharing wishlists and planning thoughtful surprises.</p></div>}
        <Card className="create-card"><Card.Body><h3>{registryType === "company" ? "Create a company registry" : "Create a household"}</h3><p className="text-secondary">Organize private gift ideas for a family or a workplace.</p><Form onSubmit={create}><Form.Group controlId="registry-type" className="mb-3"><Form.Label>Registry type</Form.Label><Form.Select value={registryType} onChange={(e) => { setRegistryType(e.target.value); setProfiles(profiles.map((profile) => ({ ...profile, profile_type: "person", relationship: e.target.value === "company" ? "employee" : "family_member" }))); }}><option value="family">Family household</option><option value="company">Company / workplace</option></Form.Select></Form.Group><Form.Control className="mb-3" aria-label={registryType === "company" ? "Company name" : "Household name"} placeholder={registryType === "company" ? "e.g. Acme Studio" : "e.g. The Parkers"} required maxLength={160} value={name} onChange={(e) => setName(e.target.value)} />{registryType === "family" && <p className="small text-secondary mt-3">You?re already included as <strong>{user.name} (you)</strong>, the family creator.</p>}<h4 className="fs-6">{registryType === "company" ? "Add employees (optional)" : "Add other family members or pets (optional)"}</h4>{profiles.map((profile, index) => <Row key={index} className="g-2 mb-2"><Col md={5}><Form.Control aria-label={`Family member ${index + 1} name`} placeholder="Name" autoComplete="off" maxLength={120} value={profile.display_name} onChange={(event) => setProfiles(profiles.map((row, rowIndex) => rowIndex === index ? { ...row, display_name: event.target.value } : row))} /></Col><Col md={3}><Form.Select aria-label={`Family member ${index + 1} type`} value={profile.profile_type} onChange={(event) => setProfiles(profiles.map((row, rowIndex) => rowIndex === index ? { ...row, profile_type: event.target.value, ...(event.target.value === 'pet' ? { relationship: undefined } : {}) } : row))}><option value="person">Person</option>{registryType !== "company" && <option value="pet">Pet</option>}</Form.Select></Col>{profile.profile_type !== 'pet' && <Col md={3}><RelationshipSelect label={`Family member ${index + 1} relationship`} company={registryType === "company"} value={profile.relationship} onChange={(relationship) => setProfiles(profiles.map((row, rowIndex) => rowIndex === index ? { ...row, relationship } : row))} /></Col>}<Col md={4}><BirthdayInput label={`Family member ${index + 1} birthday`} value={profile.birthday} onChange={(birthday) => setProfiles(profiles.map((row, rowIndex) => rowIndex === index ? { ...row, birthday } : row))} /></Col></Row>)}<div className="d-flex flex-wrap gap-2 mt-3"><Button type="button" variant="outline-success" onClick={() => setProfiles([...profiles, { display_name: "", profile_type: "person", birthday: "" }])}>{registryType === "company" ? "+ Add another employee" : "+ Add another person or pet"}</Button><Button type="submit" variant="success" disabled={busy}>{busy ? "Creating..." : registryType === "company" ? "Create company registry" : "Create household"}</Button></div></Form></Card.Body></Card>
      </section></details>}
      <div className="quick-links"><Link to="/wishlist?section=plans">Your reserved &amp; purchased gifts</Link><span>Private to you—your gift recipient won’t see them.</span></div>
    </Container>
  );
}

function HouseholdCard({ household, onOpen }) {
  return <Card as={onOpen ? "button" : Link} {...(onOpen ? {type:"button",onClick:onOpen} : {to:`/households/${household.id}`})} className="household-card text-start"><Card.Body>{household.photo_path && <img src={mediaUrl(household.photo_path)} alt={household.name + " profile photo"} className="household-card-photo" />}{!household.photo_path && <div className="household-flower" aria-hidden="true">❋</div>}{household.registry_type === "company" && <Badge bg="light" text="dark" className="me-2">Company</Badge>}<Badge bg="light" text="success">{household.role?.replace("_", " ")}</Badge><h3>{household.name}</h3><span>{household.registry_type === "company" ? "Open employee wishes" : onOpen ? "View shared wishes" : "Open your family space"} <span aria-hidden="true">→</span></span></Card.Body></Card>;
}

function AcceptInvitationPage() {
  const { token } = useParams();
  const { user, refresh } = useSession();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const attempted = useRef("");
  const next = '/accept-invitation/' + encodeURIComponent(token);
  const accept = async () => {
    setError(""); setBusy(true);
    try {
      const result = await api("/invitations/accept", { method: "POST", body: JSON.stringify({ token }) });
      await refresh();
      navigate('/households/' + result.household_id, { replace: true });
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    const key = token + ':' + user?.id;
    if (user && !user.is_support && attempted.current !== key) { attempted.current = key; accept(); }
  }, [token, user?.id]);
  return <Container className="auth-wrap"><Card className="auth-card"><Card.Body><p className="small-label">A private family invitation</p><h1>A thoughtful little welcome.</h1><ErrorAlert message={error} />
    {!user ? <><p className="text-secondary">Already have an account? Sign in. New here? Create a free account using the email address this invitation was sent to. The shared family lists will be added to your account automatically.</p><div className="d-grid gap-2"><Button as={Link} to={'/login?next=' + encodeURIComponent(next)} variant="success">Sign in to accept</Button><Button as={Link} to={'/register?next=' + encodeURIComponent(next)} variant="outline-success">Create my account</Button></div></> : user.is_support ? <p>Sign out and use a family account to accept this invitation.</p> : <><p>{busy ? "Adding the shared family lists to your account..." : "Use the email address that received this invitation. Only the selected profiles will be shared with you."}</p>{error && <Button onClick={accept} disabled={busy} variant="success">Try invitation again</Button>}</>}
    <p className="small text-secondary mt-3 mb-0">Family photos and lists are private to authorized family members and invited shoppers. Other shoppers cannot see the household's membership list or family relationship labels.</p>
  </Card.Body></Card></Container>;
}

function AcceptStaffInvitationPage() {
  const { token } = useParams();
  const { refresh } = useSession();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", password: "", confirmation: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const accept = async (event) => {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirmation) {
      setError("The passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await api("/auth/support/accept-invitation", {
        method: "POST",
        body: JSON.stringify({ token, name: form.name, password: form.password }),
      });
      await refresh();
      navigate("/support", { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return <Container className="auth-wrap"><Card className="auth-card"><Card.Body>
    <p className="small-label">Private staff invitation</p>
    <h1>Join the support team.</h1>
    <p className="text-secondary">Create a separate support account using the email address this invitation was sent to. Staff accounts cannot sign in to family registries.</p>
    <ErrorAlert message={error} />
    <Form onSubmit={accept}>
      <Form.Group controlId="staff-invite-name" className="mb-3"><Form.Label>Your name</Form.Label><Form.Control required maxLength={120} autoComplete="name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></Form.Group>
      <Form.Group controlId="staff-invite-password" className="mb-3"><Form.Label>Password</Form.Label><Form.Control type="password" required minLength={16} autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /><Form.Text>Use at least 16 characters.</Form.Text></Form.Group>
      <Form.Group controlId="staff-invite-confirmation" className="mb-3"><Form.Label>Confirm password</Form.Label><Form.Control type="password" required minLength={16} autoComplete="new-password" value={form.confirmation} onChange={(event) => setForm({ ...form, confirmation: event.target.value })} /></Form.Group>
      <Button type="submit" variant="success" disabled={busy}>{busy ? "Creating account…" : "Accept staff invitation"}</Button>
    </Form>
  </Card.Body></Card></Container>;
}

function HoldManager({ path }) {
  const [holds, setHolds] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = async () => { setError(""); try { setHolds((await api(path)).holds); } catch (err) { setError(err.message); } };
  const release = async (id) => {
    setBusy(true); setError("");
    try { await api(path + '/' + id, { method: "DELETE" }); await load(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  useEffect(() => { setHolds(null); setError(""); }, [path]);
  return <Card className="create-card my-3"><Card.Body><h3>Manage gift holds</h3><p className="text-secondary">Holds expire after 24 hours. Clear a stuck hold to make the gift available again.</p><Button size="sm" variant="outline-success" disabled={busy} onClick={load}>{holds === null ? 'View active holds' : 'Refresh holds'}</Button><ErrorAlert message={error} />{holds?.length === 0 && <p className="mt-3 mb-0">No active holds.</p>}{holds?.map((hold) => <div className="ticket-row" key={hold.id}><strong>{hold.item_name}</strong><p className="mb-1">For {hold.recipient} ? Quantity: {hold.quantity}</p><small>Expires {new Date(hold.expires_at).toLocaleString()}</small><div><Button size="sm" className="mt-2" variant="outline-danger" disabled={busy} onClick={() => release(hold.id)}>Remove from Buying now</Button></div></div>)}</Card.Body></Card>;
}

export function SpecialDayForm({ profiles, occasion, onChange, onSubmit, busy, company = false }) {
  const birthdayDate = (profile) => {
    if (!profile?.birthday) return "";
    const [month, day] = profile.birthday.split('-').slice(-2).map(Number);
    const today = new Date();
    let year = today.getFullYear();
    let next = new Date(year, month - 1, Math.min(day, new Date(year, month, 0).getDate()), 12);
    if (next < new Date(year, today.getMonth(), today.getDate(), 12)) {
      year += 1;
      next = new Date(year, month - 1, Math.min(day, new Date(year, month, 0).getDate()), 12);
    }
    return year + '-' + String(month).padStart(2, '0') + '-' + String(next.getDate()).padStart(2, '0');
  };
  const changeType = (type) => {
    if (type === "christmas") {
      const today = new Date();
      const year = today.getFullYear() + (today.getMonth() === 11 && today.getDate() > 25 ? 1 : 0);
      onChange({ ...occasion, type, profile_id: "all", name: "Christmas", date: year + '-12-25' });
    } else if (type === "birthday") {
      const profile = profiles.find((person) => String(person.id) === occasion.profile_id);
      onChange({ ...occasion, type, profile_id: profile ? String(profile.id) : "", name: profile ? profile.display_name + "'s Birthday" : "", date: birthdayDate(profile) });
    } else onChange({ ...occasion, type });
  };
  return <Form onSubmit={onSubmit}><Row className="g-2 align-items-end"><Col md={3}><Form.Group controlId="special-day-type"><Form.Label>Occasion</Form.Label><Form.Select value={occasion.type} onChange={(e) => changeType(e.target.value)}>{["birthday", "christmas", "halloween", "easter", "hanukkah", "diwali", "eid", "anniversary", "baby_shower", "wedding", "graduation", "communion", "other"].map((type) => <option key={type} value={type}>{type.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())}</option>)}</Form.Select></Form.Group></Col><Col md={3}><Form.Group controlId="special-day-member"><Form.Label>For</Form.Label><Form.Select required value={occasion.profile_id} onChange={(e) => {
    const id = e.target.value;
    const profile = profiles.find((person) => String(person.id) === id);
    onChange({ ...occasion, profile_id: id, ...(occasion.type === "birthday" ? { name: profile ? profile.display_name + "'s Birthday" : "", date: birthdayDate(profile) } : {}) });
  }}><option value="" disabled>Choose a family member</option><option value="all" disabled={occasion.type === "birthday"}>{company ? "Whole company" : "All family"}</option>{profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.display_name}</option>)}</Form.Select></Form.Group></Col><Col md={3}><Form.Group controlId="special-day-name"><Form.Label>Name</Form.Label><Form.Control required maxLength={160} value={occasion.name} onChange={(e) => onChange({ ...occasion, name: e.target.value })} placeholder="e.g. Mia's Birthday" /></Form.Group></Col><Col md={2}><Form.Group controlId="special-day-date"><Form.Label>Date</Form.Label><Form.Control required type="date" value={occasion.date} onChange={(e) => onChange({ ...occasion, date: e.target.value })} /></Form.Group></Col><Col md={1}><Button type="submit" variant="success" disabled={busy}>Add</Button></Col></Row></Form>;
}

export function ManualGiftExtras({ gift, onChange, recipient = '' }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const current = useRef(gift);
  current.current = gift;
  const preview = async () => {
    const url = gift.product_url; setBusy(true); setError(''); setMessage('');
    try {
      const data = (await api('/link-preview', { method: 'POST', body: JSON.stringify({ url }) })).preview;
      if (current.current.product_url !== url) return;
      onChange({ ...current.current, name: current.current.name || data.title || '', store_name: current.current.store_name || data.store_name || '', image_url: data.image_url || current.current.image_url || '' });
      setMessage(data.image_url ? 'Link image added to your gift preview.' : 'This link has no preview image. Add an image URL below or save without an image.');
    } catch (err) { if (current.current.product_url === url) setError(err.message); }
    finally { setBusy(false); }
  };
  return <section className="manual-gift-preview my-3"><div className="d-flex flex-wrap gap-2 align-items-center mb-3"><Button type="button" size="sm" variant="outline-success" disabled={busy || !gift.product_url?.startsWith('https://')} onClick={preview}>{busy ? 'Loading image...' : 'Preview link image'}</Button><small className="text-secondary">Use a public HTTPS product link.</small></div><ErrorAlert message={error} />{message && <p className="small" role="status">{message}</p>}<Form.Group controlId={'gift-image-' + (recipient ? 'shared' : 'private')} className="mb-3"><Form.Label>Image URL (optional)</Form.Label><Form.Control type="url" value={gift.image_url || ''} onChange={(e) => onChange({ ...gift, image_url: e.target.value })} placeholder="https://.../gift-image.jpg" /></Form.Group><p className="small-label">Gift card preview</p><Card className="gift-card draft-gift-card"><Card.Body><GiftIdentity item={{ ...gift, recipient: recipient || gift.recipient || 'Your recipient' }} /><h3>{gift.name || 'Your gift title'}</h3>{gift.description && <p>{gift.description}</p>}<div className="gift-meta"><span>{gift.store_name || 'Store'}</span>{gift.estimated_price && <strong>{gift.currency || 'USD'} {gift.estimated_price}</strong>}</div><Button type="button" size="sm" disabled className="mt-3">Buy</Button><p className="small text-secondary mb-0 mt-2">Preview only. Save the gift to add it to the list.</p></Card.Body></Card></section>;
}

function RegistryPreview({ householdId }) {
  const [show, setShow] = useState(false);
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState([]);
  const [error, setError] = useState('');
  const open = async () => {
    setShow(true); setData(null); setError('');
    try { const result = await api('/households/' + householdId + '/shopper-preview'); setData(result); setSelected(result.profiles.map((profile) => profile.id)); }
    catch (err) { setError(err.message); }
  };
  return <><Button type="button" variant="outline-success" size="sm" onClick={open}>Preview registry</Button><Modal show={show} onHide={() => setShow(false)} size="xl" centered><Modal.Header closeButton><Modal.Title>Invited-shopper preview</Modal.Title></Modal.Header><Modal.Body><Alert variant="info">Choose the people included in an invitation to preview their shared lists. Buttons are disabled, availability is illustrative, and private gift plans are excluded.</Alert><ErrorAlert message={error} />{!data && !error && <p>Loading preview...</p>}{data && <><fieldset className="mb-4"><legend className="fs-6">Preview these people</legend>{data.profiles.map((profile) => <Form.Check inline key={profile.id} id={'preview-person-' + profile.id} label={profile.display_name} checked={selected.includes(profile.id)} onChange={(e) => setSelected(e.target.checked ? [...selected, profile.id] : selected.filter((id) => id !== profile.id))} />)}</fieldset><div className="d-flex align-items-center gap-3 mb-4">{data.household.photo_path && <img className="household-photo" src={mediaUrl(data.household.photo_path)} alt="Registry photo" />}<h2>{data.household.name}</h2></div>{data.profiles.filter((profile) => selected.includes(profile.id)).map((profile) => <section className="mb-5" key={profile.id}><div className="d-flex align-items-center gap-3 mb-3">{profile.photo_path && <img className="profile-photo" src={mediaUrl(profile.photo_path)} alt="" />}<div><h3>{profile.display_name}</h3>{profile.birthday && <p className="small">Birthday: {birthdayLabel(profile.birthday)}</p>}</div></div>{profile.wishlists.map((list, index) => <div key={index} className="mb-4"><h4 className="fs-5">{list.title}</h4>{list.items.length ? <Row className="g-3">{list.items.map((item, index) => <Col md={6} lg={4} key={index}><Card className="gift-card"><Card.Body><GiftIdentity item={{ ...item, recipient: profile.display_name, household_name: data.household.name, occasion: list.title }} /><h3 className="item-title" title={item.name}>{item.name}</h3>{item.description && <p>{item.description}</p>}<p>{item.store_name}{item.estimated_price ? ' / ' + item.currency + ' ' + item.estimated_price : ''}</p><p className="small">Sample availability: {item.quantity}</p><div className="d-flex flex-wrap gap-2"><Button size="sm" disabled>Buy</Button><Button size="sm" variant="outline-success" disabled aria-label="Heart gift"><HeartIcon/></Button><Button size="sm" variant="outline-secondary" disabled>Put on hold</Button></div></Card.Body></Card></Col>)}</Row> : <p className="text-secondary">No wishes in this list yet.</p>}</div>)}</section>)}{!selected.length && <p>Select at least one person to preview their wishes.</p>}</>}</Modal.Body><Modal.Footer><Button variant="outline-secondary" onClick={() => setShow(false)}>Close preview</Button></Modal.Footer></Modal></>;
}

function HouseholdPage() {
  const { crop: cropPhoto, cropper: householdPhotoCropper } = usePhotoCrop();
  const { householdId } = useParams();
  const { setHouseholds } = useSession();
  const [data, setData] = useState(null);
  const [photoNotice, setPhotoNotice] = useState("");
  const isCompany = data?.household.registry_type === "company";
  const [error, setError] = useState("");
  const [householdName, setHouseholdName] = useState("");
  const [showFamilySettings, setShowFamilySettings] = useState(() => new URLSearchParams(window.location.search).get("settings") === "1");
  const [showSpecialDayDialog, setShowSpecialDayDialog] = useState(false);
  const [newProfile, setNewProfile] = useState({ display_name: "", profile_type: "person", birthday: "" });
  const [occasion, setOccasion] = useState({ profile_id: "", name: "", type: "birthday", date: "" });
  const [inviteEmail, setInviteEmail] = useState(new URLSearchParams(window.location.search).get("invite_email") || "");
  const [selectedProfiles, setSelectedProfiles] = useState([]);
  const [inviteLink, setInviteLink] = useState("");
  const [inviteNotice, setInviteNotice] = useState("");
  const [inviteMail, setInviteMail] = useState(null);
  const [busy, setBusy] = useState(false);
  const [inviteBusy, setInviteBusy] = useState(false);
  const upcomingBirthdays = (data?.profiles || []).map((profile) => {
    if (!profile.birthday) return null;
    const today = new Date();
    const parts = profile.birthday.split("-").map(Number);
    const [month, day] = parts.slice(-2);
    const next = new Date(today.getFullYear(), month - 1, day, 12);
    today.setHours(12, 0, 0, 0);
    if (next < today) next.setFullYear(next.getFullYear() + 1);
    const daysUntil = Math.round((next - today) / 86400000);
    return daysUntil <= 30 ? { profile, next, daysUntil } : null;
  }).filter(Boolean).sort((a, b) => a.daysUntil - b.daysUntil);

  const load = async () => {
    try {
      const result = await api(`/households/${householdId}`);
      setData(result);
      setHouseholdName(result.household.name);
      setHouseholds((homes) => homes.map((home) => String(home.id) === String(result.household.id) ? { ...home, ...result.household } : home));
    } catch (err) {
      setError(err.message);
    }
  };
  useEffect(() => { load(); }, [householdId]);

  const addProfile = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api(`/households/${householdId}/profiles`, { method: "POST", body: JSON.stringify({ ...newProfile, profile_type: isCompany ? "person" : newProfile.profile_type, relationship: newProfile.relationship || (isCompany ? "employee" : "family_member"), birthday: completeBirthday(newProfile.birthday) }) });
      setNewProfile({ display_name: "", profile_type: "person", birthday: "" });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const createOccasion = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api(`/households/${householdId}/occasions`, {
        method: "POST",
        body: JSON.stringify({
          ...occasion,
          profile_id: occasion.profile_id && occasion.profile_id !== "all" ? Number(occasion.profile_id) : null,
        }),
      });
      setOccasion({ profile_id: "", name: "", type: "birthday", date: "" });
      setShowSpecialDayDialog(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const uploadHouseholdPhoto = async (event) => {
    const image = await cropPhoto(event.target.files?.[0]);
    if (!image) { event.target.value = ""; return; }
    setError("");
    try {
      const form = new FormData();
      form.append("image", image);
      const result = await api(`/households/${householdId}/photo`, { method: "POST", body: form });
      if (result.status === 'pending_approval') { setPhotoNotice(result.message); return; }
      setData((current) => ({ ...current, household: { ...current.household, photo_path: result.photo_path } }));
      setHouseholds((homes) => homes.map((home) => String(home.id) === String(householdId) ? { ...home, photo_path: result.photo_path } : home));
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      event.target.value = "";
    }
  };

  const saveHouseholdName = async (event) => {
    event.preventDefault();
    setError("");
    try {
      await api(`/households/${householdId}`, {
        method: "PATCH",
        body: JSON.stringify({ name: householdName }),
      });
      await load();
    } catch (err) {
      setError(err.message);
    }
  };

  const sendInvitation = async (event) => {
    event.preventDefault();
    setError("");
    setInviteLink("");
    setInviteNotice("");
    setInviteBusy(true);
    try {
      const result = await api(`/households/${householdId}/invitations`, {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail,
          role: "shopper",
          share_all_profiles: !isCompany,
          profile_ids: isCompany ? selectedProfiles : [],
        }),
      });
      setInviteLink(`${window.location.origin}/accept-invitation/${encodeURIComponent(result.invitation.token)}`);
      const link = result.email_message?.link || window.location.origin + '/accept-invitation/' + encodeURIComponent(result.invitation.token);
      setInviteMail({ email: inviteEmail, delivery: result.email_message?.delivery || "not_configured", subject: result.email_message?.subject || "You're invited to a private family gift list", body: result.email_message?.body || "You are invited to shop for our family on Gather & Gift. Already have an account? Sign in. Otherwise, create a free account using this email address. Your shared lists will be added automatically after sign-in. Open your private invitation: " + link });
      setInviteEmail("");
      setSelectedProfiles([]);
    } catch (err) {
      setError(err.message);
    } finally {
      setInviteBusy(false);
    }
  };
  const copyInvitation = async () => {
    try {
      await navigator.clipboard.writeText(inviteLink);
      setInviteNotice("Invitation link copied.");
    } catch {
      setInviteNotice("Copy was unavailable. Select the invitation link above and copy it manually.");
    }
  };

  if (!data && !error) return <Loading label="Opening your family space…" />;
  if (!data) return <Container className="page-wrap"><ErrorAlert message={error} /></Container>;
  return (
    <Container className="page-wrap">
      <Link to={["owner","admin"].includes(data.household.role)?"/":"/following"} className="back-link">← All households</Link>
      <p className="small-label mt-4">{isCompany ? "Your company registry" : "Your family space"}</p>
      <div className="d-flex align-items-center gap-3">{data.household.photo_path && <img src={mediaUrl(data.household.photo_path)} alt={data.household.name + " family photo"} className="household-photo" />}<h1 className="page-title mb-0">{data.household.name}</h1>{["owner", "admin"].includes(data.household.role) && <RegistryPreview householdId={householdId} />}{["owner", "admin"].includes(data.household.role) && <Button type="button" variant="outline-success" className="family-settings-button ms-auto" aria-label={isCompany ? "Company settings" : "Family settings"} title={isCompany ? "Edit company name and logo" : "Edit family name and photo"} aria-expanded={showFamilySettings} aria-controls="family-settings-panel" onClick={() => setShowFamilySettings(!showFamilySettings)}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="m9 3-.6 2.3-2 .9-2.2-.6-2 3.4 1.6 1.7v2.6l-1.6 1.7 2 3.4 2.2-.6 2 .9L9 21h4l.6-2.3 2-.9 2.2.6 2-3.4-1.6-1.7v-2.6L19.8 9l-2-3.4-2.2.6-2-.9L13 3Z" /><circle cx="11" cy="12" r="3" /></svg></Button>}</div>
      <p className="text-secondary">{isCompany ? "Employee gift ideas and shared lists." : "Your family and shared wishlists."}</p>
      <ErrorAlert message={error} onDismiss={() => setError("")} />
      {showFamilySettings && ["owner", "admin"].includes(data.household.role) && <Card id="family-settings-panel" className="create-card mb-4"><Card.Body><h3>{isCompany ? "Company settings" : "Family settings"}</h3><p className="text-secondary">Update the registry name or image. Changes appear here and on Home.</p>
      {["owner", "admin"].includes(data.household.role) && <Form className="d-flex flex-wrap gap-2 align-items-end mb-3" onSubmit={saveHouseholdName}><Form.Group controlId="household-edit-name"><Form.Label>{isCompany ? "Company name" : "Family name"}</Form.Label><Form.Control required maxLength={160} value={householdName} onChange={(event) => setHouseholdName(event.target.value)} /></Form.Group><Button type="submit" variant="outline-success">{isCompany ? "Save company name" : "Save family name"}</Button></Form>}
      {["owner", "admin"].includes(data.household.role) && <Form.Group className="mb-4" controlId="household-photo"><Form.Label>{isCompany ? "Company logo or photo" : "Family photo"}</Form.Label><Form.Control type="file" accept="image/jpeg,image/png,image/gif,image/webp,.jpg,.jpeg" onChange={uploadHouseholdPhoto} />{householdPhotoCropper}<Form.Text>JPG, JPEG, PNG, GIF, or WebP; up to 5 MB.</Form.Text>{photoNotice && <Alert variant="info" className="mt-2">{photoNotice}</Alert>}</Form.Group>}
      <Button type="button" variant="outline-secondary" size="sm" onClick={() => setShowFamilySettings(false)}>Done</Button></Card.Body></Card>}
      {["owner", "admin"].includes(data.household.role) && <HoldManager path={"/households/" + householdId + "/holds"} />}<div className="section-heading mt-5"><div><p className="small-label">Meet your people</p><h2>{isCompany ? "Employee directory" : "Family directory"}</h2></div></div>
      {data.profiles.length ? <FamilyRows profiles={data.profiles} renderMember={profile=><><MemberCard profile={profile} company={isCompany} />{["owner", "admin"].includes(data.household.role) && profile.profile_type !== "pet" && <div className="mt-2"><RelationshipSelect label={'Relationship for ' + profile.display_name} company={isCompany} value={profile.relationship} disabled={busy} onChange={async (relationship) => { setBusy(true); setError(""); try { await api('/households/' + householdId + '/profiles/' + profile.id + '/relationship', { method: "PATCH", body: JSON.stringify({ relationship }) }); await load(); } catch (err) { setError(err.message); } finally { setBusy(false); } }} /></div>}</>}/> : <div className="empty-state"><span aria-hidden="true">🌷</span><h3>Your directory is ready</h3><p>Add family members and start keeping their gift ideas in one place.</p></div>}
      {["owner", "admin"].includes(data.household.role) && <Card className="create-card mb-3"><Card.Body><h3>{isCompany ? "Invite someone to view employee gift ideas" : "Invite someone to shop for your family"}</h3><p className="text-secondary">Invite by email. Non-private family wishlists are shared after acceptance.</p><Form onSubmit={sendInvitation}><Row className="g-2 align-items-end"><Col md={8}><Form.Group controlId="invite-shopper-email"><Form.Label>Email address</Form.Label><Form.Control type="email" autoComplete="email" required value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="someone@example.com" /></Form.Group></Col><Col md={4}><Button type="submit" variant="success" className="w-100" disabled={inviteBusy || (isCompany && !selectedProfiles.length)}>{inviteBusy ? "Preparing invite…" : "Create invitation"}</Button></Col></Row>{isCompany && <fieldset className="mt-3"><legend className="fs-6 fw-semibold">Share these gift lists only</legend>{data.profiles.map((profile) => <Form.Check key={profile.id} id={`invite-profile-${profile.id}`} type="checkbox" label={profile.display_name} checked={selectedProfiles.includes(profile.id)} onChange={(event) => setSelectedProfiles(event.target.checked ? [...selectedProfiles, profile.id] : selectedProfiles.filter((id) => id !== profile.id))} />)}</fieldset>}</Form>{inviteLink && <Alert variant="success" className="mt-3 mb-0"><strong>Invitation link ready.</strong> {inviteMail?.delivery === "sent" ? "Invitation email sent. They can sign in or create an account to add your shared lists automatically." : inviteMail?.delivery === "failed" ? "Email delivery failed. Use the email draft below or copy the private link." : "Email delivery is not configured. Open the ready-to-send email draft below or copy this private link."}<Form.Control className="mt-2" readOnly aria-label="Invitation link" value={inviteLink} onFocus={(event) => event.target.select()} /><Button className="mt-2" size="sm" variant="outline-success" onClick={copyInvitation}>Copy invitation link</Button>{inviteMail && <><Button as="a" className="mt-2 ms-2" size="sm" variant="outline-success" href={"mailto:" + encodeURIComponent(inviteMail.email) + "?subject=" + encodeURIComponent(inviteMail.subject) + "&body=" + encodeURIComponent(inviteMail.body)}>Open email draft</Button><details className="mt-3"><summary>Preview invitation email</summary><p className="mt-2"><strong>{inviteMail.subject}</strong></p><p style={{ whiteSpace: "pre-wrap" }}>{inviteMail.body}</p></details></>}{inviteNotice && <p className="small mt-2 mb-0">{inviteNotice}</p>}</Alert>}</Card.Body></Card>}
      {["owner", "admin"].includes(data.household.role) && <Card className="create-card mb-3"><Card.Body><h3>{isCompany ? "Add an employee" : "Add a person or pet"}</h3><Form onSubmit={addProfile}><Row className="g-2 align-items-end"><Col md={5}><Form.Label>Name</Form.Label><Form.Control required maxLength={120} value={newProfile.display_name} onChange={(e) => setNewProfile({ ...newProfile, display_name: e.target.value })} /></Col><Col md={3}><Form.Label>Type</Form.Label><Form.Select value={newProfile.profile_type} onChange={(e) => setNewProfile({ ...newProfile, profile_type: e.target.value })}><option value="person">Person</option><option value="pet">Pet</option></Form.Select></Col><Col md={3}><Form.Label>Relationship (optional)</Form.Label><RelationshipSelect label={isCompany ? "Employee role" : "New family member relationship"} company={isCompany} value={newProfile.relationship} onChange={(relationship) => setNewProfile({ ...newProfile, relationship })} /></Col><Col md={3}><BirthdayInput value={newProfile.birthday} onChange={(birthday) => setNewProfile({ ...newProfile, birthday })} /></Col><Col md={1}><Button type="submit" variant="success" disabled={busy}>{busy ? "…" : "Add"}</Button></Col></Row></Form></Card.Body></Card>}
      <section className="section-block"><div className="section-heading"><div><p className="small-label">Plan ahead</p><h2>Special days</h2></div>{["owner", "admin"].includes(data.household.role) && <Button variant="outline-success" onClick={() => { setOccasion({ profile_id: "", name: "", type: "birthday", date: "" }); setShowSpecialDayDialog(true); }}>Add a special day</Button>}</div>{(data.occasions || []).length ? <ul className="occasion-list">{data.occasions.map((row) => <li key={row.id}><strong>{row.name}</strong>{row.profile_name && ` · ${row.profile_name}`}<span>{new Date(`${row.date}T12:00:00`).toLocaleDateString(undefined, { month: "long", day: "numeric", year: "numeric" })}</span></li>)}</ul> : <p className="text-secondary">No special days yet.</p>}</section>
      {upcomingBirthdays.length > 0 && <Card className="create-card mb-3"><Card.Body><h3>Birthdays coming up</h3><ul className="occasion-list mb-0">{upcomingBirthdays.map(({ profile, next, daysUntil }) => <li key={profile.id}><strong>{profile.display_name}</strong><span>{daysUntil === 0 ? "Today" : daysUntil === 1 ? "Tomorrow" : `In ${daysUntil} days`} · {next.toLocaleDateString(undefined, { month: "long", day: "numeric" })}</span></li>)}</ul></Card.Body></Card>}
      <Modal show={showSpecialDayDialog} onHide={() => setShowSpecialDayDialog(false)} centered>
        <Modal.Header closeButton><Modal.Title>Add a special day</Modal.Title></Modal.Header>
        <Modal.Body><SpecialDayForm company={isCompany} profiles={data.profiles} occasion={occasion} onChange={setOccasion} onSubmit={createOccasion} busy={busy} /></Modal.Body>
      </Modal>
    </Container>
  );
}

function MemberCard({ profile, company = false }) {
  return <Card as={Link} to={`/profiles/${profile.id}`} className="member-card"><Card.Body>{profile.photo_path ? <img src={mediaUrl(profile.photo_path)} alt="" className="profile-photo member-photo" /> : <ProfileAvatar name={profile.display_name} avatarKey={profile.profile_type === "pet" && profile.avatar_key === "flower" ? "paw" : profile.avatar_key} />}<h3>{profile.display_name}{(profile.is_you || profile.is_me) ? " (you)" : ""}{profile.profile_type === "pet" ? " · Pet" : ""}</h3>{profile.birthday_shared && profile.birthday && <p className="member-birthday">Birthday · {birthdayLabel(profile.birthday)}</p>}<p className="small text-secondary mb-2">{profile.profile_type === "pet" ? "Family pet" : FAMILY_RELATIONSHIPS.find(([key]) => key === profile.relationship)?.[1] || (company ? "Employee" : "Family member")}</p><div className="interest-tags">{(profile.interests || profile.preferences?.interests || []).slice(0, 2).map((interest) => <Badge key={interest} bg="light" text="success">{interest}</Badge>)}</div><span className="member-link">View wishes <span aria-hidden="true">→</span></span></Card.Body></Card>;
}

function ProfileAvatar({ name, avatarKey, photo }) {return <MemberAvatar name={name} photo={photo} avatarKey={avatarKey} className="profile-avatar"/>;}

function ProfilePage() {
  const {user,refresh}=useSession();
  const { crop: cropPhoto, cropper: profilePhotoCropper } = usePhotoCrop();
  const { profileId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [profile, setProfile] = useState(null);
  const [wishlists, setWishlists] = useState([]);
  const [occasions, setOccasions] = useState([]);
  const [selectedWishlistId, setSelectedWishlistId] = useState("");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [showListForm, setShowListForm] = useState(false);
  const [profileEdit, setProfileEdit] = useState(() => new URLSearchParams(window.location.search).get("edit") === "1");
  const [listTitle, setListTitle] = useState("");
  const [listOccasionId, setListOccasionId] = useState("");
  const [occasionDate, setOccasionDate] = useState("");
  const [busy, setBusy] = useState(false);
  const [gift, setGift] = useState({ name: "", description: "", estimated_price: "", store_name: "", product_url: "", priority: "2", quantity: "1", category: "" });

  const load = async () => {
    try {
      const [profileResult, listsResult, occasionResult] = await Promise.all([
        api(`/profiles/${profileId}`),
        api(`/profiles/${profileId}/wishlists`),
        api(`/profiles/${profileId}/occasions`),
      ]);
      setProfile(profileResult.profile);
      setWishlists(listsResult.wishlists);
      setOccasions(occasionResult.occasions);
      const requestedWishlistId = searchParams.get("wishlist") || selectedWishlistId;
      const selected = listsResult.wishlists.find((list) => String(list.id) === String(requestedWishlistId))
        || listsResult.wishlists.find((list) => list.is_everyday)
        || listsResult.wishlists[0];
      setSelectedWishlistId(selected ? String(selected.id) : "");
      setItems(selected ? (await api(`/wishlists/${selected.id}/items`)).items : []);
    } catch (err) {
      setError(err.message);
    }
  };
  useEffect(() => { load(); if (searchParams.get("add") === "1") setShowForm(true);const refresh=()=>load(true);window.addEventListener('wishlist-updated',refresh);return()=>window.removeEventListener('wishlist-updated',refresh); }, [profileId, searchParams]);

  const addGift = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const list = wishlists.find((row) => String(row.id) === String(selectedWishlistId));
      if (!list) throw new Error("Create an everyday wishlist first.");
      await api(`/wishlists/${list.id}/items`, { method: "POST", body: JSON.stringify(gift) });
      setGift({ name: "", description: "", estimated_price: "", store_name: "", product_url: "", priority: "2", quantity: "1", category: "" });
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const saveProfile = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = {
        is_adult: Boolean(profile.is_adult),
        is_guardian: Boolean(profile.is_guardian),
        member_email: profile.member_email || "",
        avatar_key: profile.avatar_key,
        use_avatar: Boolean(profile.use_avatar),
        birthday: completeBirthday(profile.birthday),
        birthday_shared: Boolean(profile.birthday_shared),
        clothing_sizes: profile.clothing_sizes || {},
        shoe_sizes: profile.shoe_sizes || {},
        ...preferencePayload(profile),
      };
      const result = await api(`/profiles/${profileId}`, { method: "PATCH", body: JSON.stringify(payload) });
      setProfile(result.profile);
      setProfileEdit(false);
      window.dispatchEvent(new Event("wishlist-updated"));window.dispatchEvent(new Event("notifications-updated"));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const uploadProfilePhoto = async (event) => {
    const image = await cropPhoto(event.target.files?.[0]);
    if (!image) { event.target.value = ""; return; }
    setError("");
    try {
      const form = new FormData();
      form.append("image", image);
      const result = await api(`/profiles/${profileId}/photo`, { method: "POST", body: form });
      setProfile(current => ({ ...current, photo_path: result.photo_path, completion: result.completion || current.completion, use_avatar: false }));
      window.dispatchEvent(new Event("wishlist-updated"));
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      event.target.value = "";
    }
  };

  const addWishlist = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api(`/profiles/${profileId}/wishlists`, {
        method: "POST",
        body: JSON.stringify({
          title: listTitle,
          occasion_id: listOccasionId && !listOccasionId.startsWith("preset:") ? Number(listOccasionId) : null,
          occasion_type: listOccasionId.startsWith("preset:") ? listOccasionId.slice(7) : undefined,
          occasion_date: occasionDate || undefined,
        }),
      });
      setListTitle("");
      setListOccasionId("");
      setOccasionDate("");
      setOccasions((await api(`/profiles/${profileId}/occasions`)).occasions);
      setSelectedWishlistId(String(result.wishlist.id));
      setSearchParams({ wishlist: String(result.wishlist.id) });
      setWishlists([...wishlists, result.wishlist]);
      setItems([]);
      setShowListForm(false);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const selectWishlist = async (id) => {
    setSelectedWishlistId(id);
    setSearchParams(id ? { wishlist: id } : {});
    setError("");
    try {
      setItems(id ? (await api(`/wishlists/${id}/items`)).items : []);
    } catch (err) {
      setError(err.message);
    }
  };

  const reserve = async (item) => {
    setError("");
    try {
      await api(`/items/${item.id}/reservations`, { method: "POST", body: JSON.stringify({ quantity: 1 }) });
      await load();
    } catch (err) {
      setError(err.message);
    }
  };

  if (!profile && !error) return <Loading label="Finding their wish list…" />;
  if (!profile) return <Container className="page-wrap"><ErrorAlert message={error} /></Container>;
  return (
    <Container className="page-wrap profile-wishes-page">
      <Link to={-1} className="back-link">← Back to family</Link>
      <div className="profile-intro mt-4">{profile.photo_path ? <img src={mediaUrl(profile.photo_path)} alt="" className="profile-photo" /> : <ProfileAvatar name={profile.display_name} photo={profile.photo_path} avatarKey={profile.avatar_key} />}<div><p className="small-label">{profile.profile_type === "pet" ? "A little about this pet" : "A little about"}</p><h1>{profile.display_name}</h1><p className="text-secondary mb-0">{profile.interests?.length ? profile.interests.join(" · ") : "A collection of thoughtful ideas"}</p></div></div>
      <ErrorAlert message={error} onDismiss={() => setError("")} />
      <section className="section-block">
        <div className="section-heading"><div><p className="small-label">Everyday and occasion wishes</p><h2>Gift ideas</h2></div>{profile.can_add && <div className="d-flex flex-wrap gap-2"><UniversalGift defaultProfileId={profile.id} defaultWishlistId={selectedWishlistId} onSaved={load}/><Button variant="success" onClick={() => setShowForm(true)}>Add gift</Button></div>}</div>
        <div className="profile-list-controls mb-3">
          <Form.Group controlId="profile-wishlist-select">
            <Form.Label>List</Form.Label>
            <Form.Select value={selectedWishlistId} onChange={(event) => selectWishlist(event.target.value)}>
              {wishlists.map((list) => <option key={list.id} value={list.id}>{list.title}</option>)}
            </Form.Select>
          </Form.Group>
          {profile.can_edit && <Button title="Create another wishlist for a birthday, holiday, or everyday wishes." variant="outline-success" onClick={() => { setListTitle(""); setListOccasionId(""); setOccasionDate(""); setShowListForm(true); }}>New list</Button>}
        </div>
        
        {profile.can_edit && wishlists.find(list=>String(list.id)===selectedWishlistId) && <WishlistActions key={selectedWishlistId} onSharingChanged={shared=>setWishlists(rows=>rows.map(row=>String(row.id)===selectedWishlistId?{...row,share_publicly:shared}:row))} list={wishlists.find(list=>String(list.id)===selectedWishlistId)} onRenamed={title=>setWishlists(rows=>rows.map(row=>String(row.id)===selectedWishlistId?{...row,title}:row))} onDeleted={async id=>{const remaining=wishlists.filter(row=>row.id!==id);setWishlists(remaining);await selectWishlist(String(remaining[0]?.id||''));}}/>}{selectedWishlistId && <ListDelivery listId={selectedWishlistId}/>}
                {profile.favorite_stores?.length > 0 && <p className="text-secondary">Favorite stores: {profile.favorite_stores.join(" · ")}</p>}
        <details className="profile-edit-section mb-3"><summary>Gift guide</summary><GiftGuide profile={profile} name={profile.display_name}/></details>{profile.can_edit && <ProfileCompletion profile={profile} live/>}{profile.can_edit && <Card className="create-card mb-3"><Card.Body><div className="d-flex justify-content-between align-items-center"><h3 className="mb-0">Gift preferences</h3><Button variant="outline-success" size="sm" onClick={()=>setProfileEdit(!profileEdit)}>{profileEdit?'Close':'Edit gift preferences'}</Button></div>{profileEdit && <Form className="mt-3" onSubmit={saveProfile}><ProfilePreferencesFields key={profile.id} profile={profile} onChange={setProfile} prefix="profile-preferences"/><BirthdayInput value={profile.birthday} onChange={birthday=>setProfile({...profile,birthday})}/><Form.Check label="Share birthday with invited viewers" checked={Boolean(profile.birthday_shared)} onChange={e=>setProfile({...profile,birthday_shared:e.target.checked})}/><Form.Group controlId="gift-profile-photo" className="my-3"><Form.Label>Profile photo</Form.Label><Form.Control type="file" accept="image/jpeg,image/png,image/gif,image/webp,.jpg,.jpeg" onChange={uploadProfilePhoto}/>{profilePhotoCropper}</Form.Group><Button type="submit" disabled={busy}>{busy?'Saving...':'Save gift preferences'}</Button></Form>}</Card.Body></Card>}
        {items.length ? <Row className="g-3 profile-wish-grid">{items.map((item) => <Col key={item.id} xs={6} md={4} lg={3}><GiftCard item={item} canRemove={profile.can_remove_wishes !== false} onManage={profile.can_remove_wishes ? async (wish, action) => { try { await api('/items/' + wish.id, { method: action === 'remove' ? 'DELETE' : 'PATCH', ...(action === 'remove' ? {} : { body: JSON.stringify({ family_only: !wish.family_only }) }) }); await load(true); window.dispatchEvent(new Event('wishlist-updated')); } catch(err) { setError(err.message); } } : undefined} onReserve={() => reserve(item)} onReserveRefresh={() => load(true)} /></Col>)}</Row> : <div className="empty-state"><span aria-hidden="true">✨</span><h3>No wishes just yet</h3><p>{profile.can_add ? "Add something they would love—big, small, or wonderfully unexpected." : "This family has not added any wishes yet."}</p>{profile.can_add && <Button variant="outline-success" onClick={() => setShowForm(true)}>Add the first gift</Button>}</div>}
      </section>
      {occasions.length > 0 && <Card className="create-card mt-4"><Card.Body><p className="small-label">Reasons to celebrate</p><h3>Occasions for {profile.display_name}</h3><ul className="occasion-list">{occasions.map((occasion) => <li key={occasion.id}><strong>{occasion.name}</strong><span>{new Date(occasion.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span></li>)}</ul></Card.Body></Card>}
      <Modal show={showForm} onHide={() => setShowForm(false)} centered size="xl">
        <Modal.Header closeButton><Modal.Title>Browse gifts for {profile.display_name}</Modal.Title></Modal.Header>
        <Modal.Body><p className="text-secondary">Search for a gift, or paste or drop a product link. Preview the details, then heart it to save the image and gift information for this person.</p><Form.Group className="mb-3" controlId="browse-destination"><Form.Label>Save to wishlist / occasion</Form.Label><Form.Select value={selectedWishlistId} onChange={e => selectWishlist(e.target.value)}>{wishlists.map(list => <option key={list.id} value={list.id}>{list.title}</option>)}</Form.Select></Form.Group>{selectedWishlistId ? <StoreGiftFinder key={selectedWishlistId} favoriteProfile={profile} onFavoriteSaved={()=>load(true)} gift={{ name: '' }} onChange={() => {}} savedUrls={items.map(item => item.original_product_url || item.product_url)} onRemoveProduct={async (product) => { const item = items.find(row => (row.original_product_url || row.product_url) === product.product_url); if (!item) throw new Error('Refresh the list and try again.'); await api('/items/' + item.id, { method: 'DELETE' }); await load(true); window.dispatchEvent(new Event('wishlist-updated')); }} onSaveProduct={async (product) => { await api('/wishlists/' + selectedWishlistId + '/items', { method: 'POST', body: JSON.stringify({ ...product, priority: 2, quantity: 1 }) }); await load(true); window.dispatchEvent(new Event('wishlist-updated')); }} /> : <p>Create a wishlist first, then browse gifts here.</p>}</Modal.Body>
        <Modal.Footer><Button variant="success" onClick={() => setShowForm(false)}>Done browsing</Button></Modal.Footer>
      </Modal>
      <Modal show={showListForm} onHide={() => setShowListForm(false)} centered>
        <Modal.Header closeButton><Modal.Title>Create a list</Modal.Title></Modal.Header>
        <Form onSubmit={addWishlist}>
          <Modal.Body>
            <Form.Group controlId="profile-list-occasion" className="mb-3">
              <Form.Label>Occasion</Form.Label>
              <Form.Select aria-label="Wishlist occasion" value={listOccasionId} onChange={(event) => {
                const value = event.target.value;
                setListOccasionId(value);
                setOccasionDate("");
                if (value.startsWith("preset:")) setListTitle(({ "preset:christmas": "Christmas wishes", "preset:birthday": "Birthday wishes", "preset:wedding": "Wedding registry", "preset:baby_shower": "Baby registry", "preset:anniversary": "Anniversary wishes" })[value] || "");
              }}>
                <option value="">Everyday / just because</option>
                <option value="preset:christmas">Christmas</option>
                <option value="preset:birthday">Birthday</option>
                <option value="preset:wedding">Wedding</option>
                <option value="preset:baby_shower">Baby shower</option>
                <option value="preset:anniversary">Anniversary</option>
                <option value="preset:other">Another occasion</option>
                {occasions.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
              </Form.Select>
            </Form.Group>
            <Form.Group controlId="profile-list-title" className="mb-3">
              <Form.Label>List name</Form.Label>
              <Form.Control required maxLength={160} placeholder="e.g. Birthday wishes" value={listTitle} onChange={(event) => setListTitle(event.target.value)} />
            </Form.Group>
            {listOccasionId.startsWith("preset:") && <Form.Group controlId="profile-list-date">
              <Form.Label>Date</Form.Label>
              <Form.Control aria-label="Occasion date" type="date" value={occasionDate} required={["preset:other", "preset:wedding", "preset:baby_shower", "preset:anniversary"].includes(listOccasionId) || (listOccasionId === "preset:birthday" && !profile.birthday)} onChange={(event) => setOccasionDate(event.target.value)} />
            </Form.Group>}
          </Modal.Body>
          <Modal.Footer><Button variant="outline-secondary" onClick={() => setShowListForm(false)}>Cancel</Button><Button type="submit" disabled={busy}>Create list</Button></Modal.Footer>
        </Form>
      </Modal>
    </Container>
  );
}

export const GIFT_STORES = storeCatalog;

const GIFT_INSPIRATION = [
  { key: 'everyday', name: 'Everyday / all gifts', ideas: [] },
  { key: 'toys', name: 'Toys & games', ideas: ['Building sets', 'Board games', 'Puzzles', 'Outdoor toys'] },
  { key: 'books', name: 'Books', ideas: ['Bestselling books', 'Children storybooks', 'Cookbooks'] },
  { key: 'home', name: 'Home & self care', ideas: ['Cozy blankets', 'Self care gifts', 'Kitchen gifts'] },
  { key: 'giftcards', name: 'Gift cards', icon: '04', description: 'Let them choose something they love.', ideas: ['Restaurant gift card', 'Gaming gift card', 'Bookstore gift card', 'Retail store gift card'] },
  { key: 'food', name: 'Food & treats', icon: '01', description: 'A little something delicious.', ideas: ['Chocolate gift box', 'Coffee and tea sampler', 'Savory snack collection', 'Baking gift set'] },
  { key: 'baskets', name: 'Gift baskets', icon: '02', description: 'A thoughtful bundle, ready to give.', ideas: ['Breakfast gift basket', 'Spa gift basket', 'Family movie night basket', 'Gourmet food basket'] },
  { key: 'stocking', name: 'Stocking stuffers', icon: '03', description: 'Small surprises with plenty of charm.', ideas: ['Mini puzzles', 'Cozy socks', 'Travel size self care gifts', 'Small art supplies'] },
];

export function GiftInspiration({ onChoose }) {
  const [selected, setSelected] = useState('everyday');
  const selectId = useId();
  const category = GIFT_INSPIRATION.find(row => row.key === selected);
  return <section className="gift-category-filter mb-3"><Form.Group controlId={selectId}><Form.Label>Gift category</Form.Label><Form.Select value={selected} onChange={e => { setSelected(e.target.value); const next = GIFT_INSPIRATION.find(row => row.key === e.target.value); onChoose({ query: next.key === 'everyday' ? '' : next.name, category: next.key === 'everyday' ? '' : next.name }); }}>{GIFT_INSPIRATION.map(row => <option value={row.key} key={row.key}>{row.name}</option>)}</Form.Select></Form.Group>{selected==='food' && <TreatIdeas onChoose={onChoose}/>} {selected!=='food' && category.ideas.length > 0 && <div className="d-flex flex-wrap gap-2 mt-2" aria-label={category.name + ' ideas'}>{category.ideas.map(idea => <Button type="button" variant="outline-success" size="sm" key={idea} onClick={() => onChoose({ query: idea, category: category.name })}>{idea}</Button>)}</div>}</section>;
}

export function StoreGiftFinder({ gift, onChange, onSaveProduct, onRemoveProduct, savedUrls = [], initialProducts = [], resultsOnly = false, priceFilter = {}, renderActions = null, favoriteProfile = null, favoriteProfiles = [], onFavoriteSaved = null }) {
  const searchInputId = useId();
  const [searchFilters,setSearchFilters]=useState({store:'',brand:'',category:'',min_price:priceFilter.minimum||'',max_price:priceFilter.maximum||'',currency:priceFilter.currency||'USD'});
  const [saved, setSaved] = useState([]);
  const [pendingRemoval, setPendingRemoval] = useState(null);
  const pendingRef = useRef(null);
  const [removedUrls, setRemovedUrls] = useState([]);
  const isSaved = (url) => !removedUrls.includes(url) && (saved.includes(url) || savedUrls.includes(url));
  const commitRemoval = async (entry) => {
    clearTimeout(entry.timer);
    try { await onRemoveProduct(entry.product); setSaved(previous => previous.filter(url => url !== entry.product.product_url)); }
    catch (err) { setRemovedUrls(previous => previous.filter(url => url !== entry.product.product_url)); setError(err.message || "Could not remove this gift."); }
    finally { if (pendingRef.current === entry) { pendingRef.current = null; setPendingRemoval(null); } }
  };
  const unheartProduct = async (product) => {
    if (pendingRef.current) await commitRemoval(pendingRef.current);
    const entry = { product };
    setRemovedUrls(previous => [...previous, product.product_url]);
    entry.timer = setTimeout(() => commitRemoval(entry), 8000);
    pendingRef.current = entry; setPendingRemoval(entry);
  };
  const undoRemoval = () => { const entry = pendingRef.current; if (!entry) return; clearTimeout(entry.timer); setRemovedUrls(previous => previous.filter(url => url !== entry.product.product_url)); pendingRef.current = null; setPendingRemoval(null); };
  const [saving, setSaving] = useState("");
  const saveLock = useRef(false);
  const heartProduct = async (product) => {
    if (saveLock.current) return;
    if (!product.name.trim()) { setError('Enter a gift name.'); return; }
    if (product.estimated_price !== '' && product.estimated_price != null && (!Number.isFinite(Number(product.estimated_price)) || Number(product.estimated_price)<0 || Number(product.estimated_price)>99999999.99)) { setError('Enter a valid estimated price or leave it blank.'); return; }
    saveLock.current = true; setSaving(product.product_url); setError("");
    try { await onSaveProduct({ name: product.name, store_name: product.store_name, estimated_price: product.estimated_price, currency: product.currency, product_url: product.product_url, image_url: product.thumbnail || "",...(product.source_token?{source_token:product.source_token}:{}) }); setRemovedUrls(previous => previous.filter(url => url !== product.product_url)); setSaved(previous => [...previous, product.product_url]); setSelected("Saved to your list. Keep browsing and heart more gifts."); }
    catch (err) { setError(err.message || "Could not save this gift. Please try again."); }
    finally { saveLock.current = false; setSaving(""); }
  };
  const [query, setQuery] = useState(gift.name || "");
  const [products, setProducts] = useState(initialProducts);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [selected, setSelected] = useState("");
  const requestId = useRef(0);
  const choose = (store) => {
    onChange({ ...gift, name: query.trim(), store_name: store.name, product_url: store.search + encodeURIComponent(query.trim()) });
    setSelected('Search link added for ' + store.name + '. It opens matching results.');
  };
  const search = async () => {
    const id = ++requestId.current;
    setBusy(true); setError(""); setMessage(""); setProducts([]); setSelected("");
    try {
      if (/^https?:\/\//i.test(query.trim())) {
        if (!query.trim().startsWith('https://')) throw new Error('Use a secure HTTPS product link.');
        const data = (await api('/link-preview', { method: 'POST', body: JSON.stringify({ url: query.trim() }) })).preview;
        if (id !== requestId.current) return;
        if (!data.title) throw new Error('This store did not provide a product name. Try searching for the product instead.');
        setProducts([{ name: data.title, product_url: query.trim(), store_name: data.store_name || '', thumbnail: data.image_url || '', estimated_price: data.estimated_price ?? '', currency: data.currency || 'USD' }]);
        setMessage(data.metadata_unavailable ? 'This store blocks previews. Review the gift name and add an estimated price before saving the link.' : 'Review the gift name and estimated price, then choose + Wish to save it.');
        return;
      }
      const params=new URLSearchParams({q:query.trim()});for(const [key,value] of Object.entries(searchFilters)){if(value!==''&&(key!=='currency'||searchFilters.min_price!==''||searchFilters.max_price!==''))params.set(key,value);}
      const data = await api('/gift-discovery?'+params);
      if (id !== requestId.current) return;
      setProducts(data.products || []);
      setMessage(data.message || (data.products?.length ? "Choose a product to fill in its details. Prices may change at checkout." : "No products found. Try a different search or browse a store below."));
    } catch (err) { if (id === requestId.current) setError(err.message); }
    finally { if (id === requestId.current) setBusy(false); }
  };
  return <section className={"store-finder mb-4"+(resultsOnly?" recommendation-results":"")}><div className="store-finder-heading"><span className="finder-icon" aria-hidden="true">+</span><div><p className="small-label mb-1">Discover something thoughtful</p><h3>Find their next favorite thing</h3></div></div><p>{renderActions?"Choose Buying now, save an item, or add it to a wishlist you manage.":onSaveProduct ? "Choose + Wish to add a product to this list." : "Search for a gift across stores. Choose a result to fill in its name, store, price, and shopping link."}</p>
    <GiftInspiration onChoose={({ query: idea, category }) => { setQuery(idea); requestId.current += 1; setBusy(false); setProducts([]); setMessage(''); setError(''); setSelected(''); onChange({ ...gift, name: idea, category, product_url: '', store_name: '', estimated_price: '', image_url: '' }); }} /><Form.Group controlId={searchInputId}><Form.Label>Search for a gift</Form.Label><p className="small text-secondary mb-2">Search or paste a link.</p><div className="d-flex gap-2"><Form.Control type="search" maxLength={2000} value={query} onChange={(e) => { setQuery(e.target.value); requestId.current += 1; setBusy(false); setProducts([]); setMessage(""); setError(""); setSelected(""); }} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); if (query.trim() && !busy) search(); } }} placeholder="Search for a gift or paste a product link" onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); const text = e.dataTransfer.getData("text/uri-list").split("\n").find(line => line && !line.startsWith("#")) || e.dataTransfer.getData("text/plain"); if (text) { setQuery(text.trim()); requestId.current += 1; setProducts([]); setError(""); setMessage("Link added. Select Preview link to load the details."); } }} /><Button type="button" variant="success" disabled={busy || !query.trim()} onClick={search}>{busy ? 'Loading...' : /^https?:\/\//i.test(query.trim()) ? 'Preview link' : 'Find gifts'}</Button></div></Form.Group>
    {!resultsOnly&&<details className="my-3"><summary>Filter products</summary><div className="row g-2 mt-1">{[['store','Store'],['brand','Brand'],['category','Category'],['min_price','Minimum price'],['max_price','Maximum price']].map(([key,label])=><Form.Group className="col-12 col-sm-6" key={key} controlId={searchInputId+'-filter-'+key}><Form.Label>{label}</Form.Label><Form.Control type={key.endsWith('price')?'number':'text'} min={key.endsWith('price')?0:undefined} step={key.endsWith('price')?'.01':undefined} value={searchFilters[key]} onChange={e=>setSearchFilters({...searchFilters,[key]:e.target.value})}/></Form.Group>)}<Form.Group className="col-12 col-sm-6" controlId={searchInputId+'-filter-currency'}><Form.Label>Price currency</Form.Label><Form.Select value={searchFilters.currency} onChange={e=>setSearchFilters({...searchFilters,currency:e.target.value})}>{['USD','CAD','GBP','EUR','AUD','NZD','JPY','INR'].map(code=><option key={code}>{code}</option>)}</Form.Select></Form.Group></div><Button variant="link" size="sm" onClick={()=>setSearchFilters({store:'',brand:'',category:'',min_price:'',max_price:'',currency:'USD'})}>Clear product filters</Button><small className="d-block text-secondary">Filters apply when you select Find gifts. Stores without connected search can still be added by product link.</small></details>}
    <div aria-live="polite">{pendingRemoval && <Alert variant="secondary">Removed {pendingRemoval.product.name} from your list. <Button type="button" variant="link" onClick={undoRemoval}>Undo</Button><small className="d-block">Undo is available for 8 seconds.</small></Alert>}{message && <p className="mt-3">{message}</p>}{selected && <Alert variant="success" className="mt-3">{selected}</Alert>}</div><ErrorAlert message={error} />
    {products.length > 0 && <div className="product-results">{orderProducts(products).filter(product=>inBudget(product,priceFilter)).map((product, index) => <article className="product-result" key={product.product_url + index}>{product.thumbnail && <img src={product.thumbnail} alt="" loading="lazy" referrerPolicy="no-referrer" />}<div className="product-result-body"><small>{product.store_name}</small><h4 className="item-title" title={product.name}>{product.name}</h4>{product.estimated_price && <strong>{product.currency} {product.estimated_price}</strong>}{/^https?:\/\//i.test(query.trim()) && !resultsOnly && <div className="pasted-gift-details my-2"><Form.Group controlId={searchInputId+'-name-'+index} className="mb-2"><Form.Label>Gift name</Form.Label><Form.Control maxLength={200} value={product.name} onChange={e=>setProducts(rows=>rows.map(row=>row===product?{...row,name:e.target.value}:row))}/></Form.Group><Form.Group controlId={searchInputId+'-price-'+index} className="mb-2"><Form.Label>Estimated price</Form.Label><Form.Control type="number" min="0" max="99999999.99" step="0.01" placeholder="Add price (optional)" value={product.estimated_price??''} onChange={e=>setProducts(rows=>rows.map(row=>row===product?{...row,estimated_price:e.target.value}:row))}/></Form.Group><Form.Group controlId={searchInputId+'-currency-'+index}><Form.Label>Currency</Form.Label><Form.Select value={product.currency||'USD'} onChange={e=>setProducts(rows=>rows.map(row=>row===product?{...row,currency:e.target.value}:row))}>{['USD','CAD','EUR','GBP','AUD','NZD','JPY','INR'].map(code=><option key={code}>{code}</option>)}</Form.Select></Form.Group><small className="text-secondary">Estimated price; confirm the current price at the store.</small></div>}<a href={product.product_url} target="_blank" rel="noopener noreferrer">View product</a>{renderActions?renderActions(product):onSaveProduct ? <Button type="button" size="sm" variant="outline-success" aria-label={isSaved(product.product_url)?(onRemoveProduct?"Remove wish":"Added to list"):"+ Wish"} title={isSaved(product.product_url)?"Saved":"Save gift"} aria-pressed={isSaved(product.product_url)} disabled={Boolean(saving) || (!onRemoveProduct && isSaved(product.product_url)) || pendingRemoval?.product.product_url === product.product_url} onClick={() => isSaved(product.product_url) ? unheartProduct(product) : heartProduct(product)}>{isSaved(product.product_url)?(onRemoveProduct?'Remove wish':'Added'):'+ Wish'}</Button> : <Button type="button" size="sm" variant="success" onClick={() => { onChange({ ...gift, name: product.name, store_name: product.store_name, estimated_price: product.estimated_price, currency: product.currency, product_url: product.product_url, image_url: product.thumbnail || "" }); setSelected('Gift details added. Review below, then save your gift.'); }}>Use this gift</Button>}</div></article>)}</div>}
    {onSaveProduct && <ManualGiftEntry onSave={onSaveProduct} initialName={query}/>}<details className="mt-3" open={!products.length}><summary className="fw-semibold">Browse Google and more stores</summary><div className="store-grid">{storeCatalog.map((store) => <div className={"store-tile " + (gift.store_name === store.name ? "selected" : "")} key={store.name}><StoreLogo name={store.name}/><strong>{store.name}</strong><a href={store.search + encodeURIComponent(query.trim() || 'gifts')} target="_blank" rel="noopener noreferrer">Browse store</a><Button variant="outline-success" size="sm" type="button" disabled={!query.trim()} onClick={() => choose(store)}>Use this store</Button><FavoriteStoreButton store={store.name} profile={favoriteProfile} profiles={favoriteProfiles} onSaved={onFavoriteSaved}/></div>)}</div><p className="small mb-0">Browse opens a new tab. Use this store saves your idea with a search link. Use this gift above saves a specific product.</p></details><AffiliateDisclosure/></section>;
}

export function BuyGiftButton({ item, alreadyHeld = false, onHeld }) {
 const shopping=useShoppingState();
 const [localRow,setLocalRow]=useState(null),[localStatus,setLocalStatus]=useState('');
 const sourceRow=shopping?.rows.find(r=>r.item.id===item.id&&r.status==='reserved');
 const row=sourceRow || (!shopping?.loaded&&localStatus==='reserved'?localRow:null);
 const current=shopping?.items[item.id] || item;
 const inBag=Boolean(row || (localStatus!=='cancelled'&&localStatus!=='purchased'&&(!shopping?.loaded)&&(alreadyHeld||item.availability?.held_by_you)));
 const unavailable=Boolean((localStatus==='purchased'&&!shopping) || (current.availability && current.availability.available<=0&&!inBag));
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[popupBlocked,setPopupBlocked]=useState(false),[confirm,setConfirm]=useState(false);
 const tooltipId=useId();
 const refresh=async()=>{window.dispatchEvent(new Event('shopping-updated'));window.dispatchEvent(new Event('wishlist-updated'));await onHeld?.();};
 const getRow=async()=>{if(row)return row;const result=await api('/my-shopping');const found=result.reservations.find(r=>r.item.id===item.id&&r.status==='reserved');if(!found)throw Error('This hold has ended. Refresh the list.');return found;};
 const destination=item.shopping_url||item.product_url;
 const buy=async()=>{if(unavailable||busy)return;setBusy(true);setError('');const tab=destination?window.open('about:blank','_blank'):null;if(tab)tab.opener=null;try{if(!inBag){const result=await api('/items/'+item.id+'/reservations',{method:'POST',body:JSON.stringify({quantity:1,reuse_existing:true})});const reserved={...result.reservation,item,is_owner:true,quantity:result.reservation.quantity||1};setLocalRow(reserved);setLocalStatus('reserved');shopping?.held(item,reserved);}setPopupBlocked(Boolean(destination&&!tab));if(tab)tab.location.replace(destination);await refresh();}catch(e){tab?.close();setError(e.message);}finally{setBusy(false);}};
 const change=async(status,secret=true,delivery_method='undecided')=>{setBusy(true);setError('');try{const active=await getRow();if(status==='cancelled'){if(!active.is_owner)throw Error('Only the person holding this gift can release it.');await api('/items/'+item.id+'/heart',{method:'PUT'});}await api('/reservations/'+active.id,{method:'PATCH',body:JSON.stringify({status,...(status==='purchased'?{purchase_secret:secret,delivery_method}:{})})});shopping?.changed(active,status);setLocalStatus(status);setLocalRow(null);setConfirm(false);await refresh();}catch(e){setError(e.message);}finally{setBusy(false);}};
 return <div className="gift-buy-control"><div className="purchase-quick-actions"><OverlayTrigger placement="top" trigger={['hover','focus']} overlay={<Tooltip id={tooltipId}>{unavailable?(current.availability?.reserved>0?'On hold by another shopper.':'This gift has been purchased.'):'Reserved for up to 24 hours. Mark purchased after checkout, or save for later to release your hold.'}</Tooltip>}><span className="buy-button-trigger" tabIndex={unavailable?0:undefined}><Button size="sm" variant="success" className={'buy-bag-button'+(inBag?' is-in-bag':'')} aria-pressed={inBag} aria-label={inBag?'Continue shopping':'Buying now'+(item.store_name?' at '+item.store_name:'')} title={inBag?'In Buying now':'Buying now - reserve for 24 hours'} disabled={busy||unavailable} onClick={buy}><ShoppingBagIcon filled={inBag}/></Button></span></OverlayTrigger>{inBag&&<Dropdown align="end"><Dropdown.Toggle size="sm" variant="outline-secondary" aria-label="Manage purchase" title="Manage purchase" disabled={busy}/><Dropdown.Menu>{(row?.is_owner!==false)&&<Dropdown.Item onClick={()=>change('cancelled')}>Save for later</Dropdown.Item>}<Dropdown.Item onClick={()=>{setError('');setConfirm(true);}}>Mark purchased</Dropdown.Item></Dropdown.Menu></Dropdown>}</div>{popupBlocked&&<a href={destination} target="_blank" rel="noopener noreferrer">Open store if it did not open</a>}{!confirm&&<ErrorAlert message={error}/>}<PurchaseConfirmation show={confirm} onHide={()=>setConfirm(false)} busy={busy} error={error} onConfirm={(secret,method)=>change('purchased',secret,method)} deliveryMethod={row?.delivery_method}/></div>;
}

function CartHoldInfo() {
  const id = useId();
  return <OverlayTrigger placement="top" trigger={['hover', 'focus']} overlay={<Tooltip id={id}>Reserved for up to 24 hours. Mark purchased after checkout, or remove it from Buying now. Hearts save gifts for later.</Tooltip>}><button type="button" className="cart-hold-info" aria-label="About the 24-hour gift hold"><span aria-hidden="true">&#9432;</span></button></OverlayTrigger>;
}

function GiftAvailability() { return null; }

function GiftCard({ item, onReserveRefresh, onManage, canRemove = true }) {
 const [editing,setEditing]=useState(false);
 const actions=<>{onManage&&canRemove&&<><Button size="sm" variant="outline-secondary" onClick={()=>setEditing(true)}>Edit gift</Button><Button size="sm" variant="outline-danger" aria-label="Remove wish" onClick={()=>onManage(item,'remove')}>Remove</Button></>}{item.availability&&<><HeartButton item={item}/><BuyGiftButton item={item} alreadyHeld={Boolean(item.availability.held_by_you)} onHeld={onReserveRefresh}/></>}</>;
 return <Card className="gift-card compact-wish-card"><Card.Body><GiftSummaryRow item={item} actions={actions} details={<><GiftIdentity item={item}/><GiftDetails item={item}/><WishOrganize item={item} onChanged={onReserveRefresh}/>{item.availability&&(item.availability.available>0||item.availability.held_by_you)&&<CoBuyInvite item={item} onHeld={onReserveRefresh}/>}</>}/><EditGiftDialog item={editing?item:null} onClose={()=>setEditing(false)} onSaved={onReserveRefresh}/></Card.Body></Card>;
}

function NotifyWhenAvailable({item}) {
 const [watching,setWatching]=useState(Boolean(item.availability_alert)),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>setWatching(Boolean(item.availability_alert)),[item.id,item.availability_alert]);
 const toggle=async()=>{setBusy(true);setError('');try{const r=await api('/items/'+item.id+'/availability-alert',{method:watching?'DELETE':'PUT'});setWatching(r.watching);}catch(e){setError(e.message);}finally{setBusy(false);}};
 return <><Button size="sm" variant="link" disabled={busy} onClick={toggle}>{watching?'Notification on':'Notify me'}</Button><ErrorAlert message={error}/></>;
}

export function GiftIdentity({ item }) {
  const shopping=useShoppingState();
  const availability = shopping?.items[item.id]?.availability || item.availability;
  const unavailable = availability && availability.available === 0;
  const status = unavailable ? (availability.reserved > 0 ? "On hold" : availability.purchased > 0 ? "SOLD" : "Unavailable") : "";
  const image = item.image_path || item.image_url;
  const [imageFailed, setImageFailed] = useState(false);
  useEffect(() => setImageFailed(false), [image]);
  return <><div className={"wishlist-gift-image" + (status && status !== "On hold" ? " gift-unavailable" : "")}>{image && !imageFailed ? <img src={mediaUrl(image)} alt={item.name} loading="lazy" referrerPolicy="no-referrer" onError={() => setImageFailed(true)} /> : <span aria-hidden="true">&#127873;</span>}{status && <div className={"gift-status-overlay"+(status==="On hold"?" gift-hold-banner":"")}><strong>{status}</strong>{status!=="On hold" && <small>No longer available</small>}</div>}</div>{availability?.purchased_by?.length>0 && <small className="d-block text-secondary mt-1">Purchased by {availability.purchased_by.join(", ")}</small>}{status === "On hold" && !availability.held_by_you && <NotifyWhenAvailable item={item}/>}{item.recipient && <p className="small mt-2 mb-1">{item.profile_id?<Link to={'/profiles/'+item.profile_id}><strong>{item.recipient}</strong></Link>:<strong>{item.recipient}</strong>}</p>}{item.recipient_preferences && <GiftGuideButton profile={item.recipient_preferences} name={item.recipient}/>}<p className="small text-secondary">{item.occasions?.length ? item.occasions.join(', ') : item.occasion || 'Everyday / just because'}</p></>;
}

function PriorityGifts({value=1}) {
 const count=Math.max(1,Math.min(4,Math.round(Number(value)||1)));
 const labels=["It's okay if I get it",'Really want it','Really, really want it','Have to have it'];
 const id=useId();
 return <OverlayTrigger placement="top" trigger={['hover','focus']} overlay={<Tooltip id={id}><strong>{labels[count-1]}</strong><br/>1 gift: {labels[0]}<br/>2 gifts: {labels[1]}<br/>3 gifts: {labels[2]}<br/>4 gifts: {labels[3]}</Tooltip>}><span className="wish-priority-gifts" tabIndex={0} role="img" aria-label={'Want level: '+labels[count-1]}>{labels.map((label,i)=><svg key={label} width="17" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true" className={i<count?'is-filled':'is-empty'}><rect x="4" y="11" width="16" height="10" rx="1.5" fill={i<count?'currentColor':'none'} fillOpacity=".2"/><rect x="3" y="7" width="18" height="4" rx="1" fill={i<count?'currentColor':'none'} fillOpacity=".25"/><path d="M12 7v14M12 7H8a2.5 2.5 0 1 1 2.5-2.5L12 7Zm0 0h4a2.5 2.5 0 1 0-2.5-2.5L12 7Z"/></svg>)}</span></OverlayTrigger>;
}

function HeartIcon({filled=false}) {return <svg width="21" height="21" viewBox="0 0 24 24" fill={filled?'currentColor':'none'} stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z"/></svg>;}

export function HeartButton({ item, onChanged }) {
  const [canUndo, setCanUndo] = useState(false);
  const undoTimer = useRef(null);
  useEffect(() => () => clearTimeout(undoTimer.current), []);
  const [hearted, setHearted] = useState(Boolean(item.is_hearted));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => setHearted(Boolean(item.is_hearted)), [item.id, item.is_hearted]);
  const toggle = async () => {
    setBusy(true); setError("");
    try {
      await api('/items/' + item.id + '/heart', { method: hearted ? "DELETE" : "PUT" });
      setHearted(!hearted);
      clearTimeout(undoTimer.current);
      setCanUndo(hearted);
      if (hearted) undoTimer.current = setTimeout(() => setCanUndo(false), 8000);
      window.dispatchEvent(new Event('wishlist-updated'));
      if (onChanged) await onChanged();
    } catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  return <><Button size="sm" type="button" className="heart-button" variant={hearted ? "success" : "outline-success"} disabled={busy} aria-pressed={hearted} aria-label={hearted?'Unheart':'Heart gift'} title={hearted?'Remove from Saved items':'Save for later'} onClick={toggle}><HeartIcon filled={hearted}/></Button>{canUndo && <span role="status" className="ms-2 small">Removed from favorites. <Button type="button" size="sm" variant="link" disabled={busy} onClick={toggle}>Undo</Button></span>}<ErrorAlert message={error} /></>;
}

function wishIsPrivate(wish) {return wish.visibility==='private' || ((!wish.visibility || wish.visibility==='custom') && !wish.viewer_ids.length);}
function wishAudience(wish,names) {return wish.visibility==='public'?'Public':wish.visibility==='followers'?'Followers':wish.visibility==='family'?'Family accounts':wish.visibility==='private'?'This shared login only':names.length?'Shared with '+names.join(', '):'This shared login only';}
function WishVisibilityIcon({ visibility, label }) {
 const id=useId();
 const globe=visibility==='public' || visibility==='followers';
 const locked=visibility==='private';
 return <OverlayTrigger placement="top" trigger={['hover','focus']} overlay={<Tooltip id={id}>{label}</Tooltip>}><span tabIndex={0} role="img" aria-label={label} className="wish-visibility-icon"><svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true">{globe?<><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></>:locked?<><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/></>:<><circle cx="9" cy="8" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6m2 3a5 5 0 0 1 3 4v3"/></>}</svg></span></OverlayTrigger>;
}

function PersonalWishesPanel({profiles=[]}) {
 const [detailEdit,setDetailEdit]=useState(null);
  const {user,households,refresh}=useSession();
  const [familyItems,setFamilyItems]=useState([]),[query,setQuery]=useState('');
  const [minimum,setMinimum]=useState(''),[maximum,setMaximum]=useState(''),[currency,setCurrency]=useState('USD');
  const matches=item=>inBudget(item,{minimum,maximum,currency}) && [item.name,item.recipient,...(item.occasions||[])].filter(Boolean).join(' ').toLowerCase().includes(query.trim().toLowerCase());
  const ownIds=new Set(households.filter(h=>['owner','admin','family_member'].includes(h.role)).map(h=>String(h.id)));

  const [data, setData] = useState({ mine: [], shared: [], audience: [] });
  const families=familyItems.filter(i=>!i.personal_wish && !data.mine.some(w=>w.item.id===i.id) && (i.households||[]).some(h=>ownIds.has(String(h.id)))).filter(matches);
  const [editing, setEditing] = useState(null);
  const [audienceQuery, setAudienceQuery] = useState('');
  const [show, setShow] = useState(false);
  const [savedNotice, setSavedNotice] = useState('');
  const [gift, setGift] = useState({ name: '', description: '', product_url: '', image_url: '', estimated_price: '', occasion: '', viewer_ids: [] });
  const [shareWithFamily, setShareWithFamily] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async () => { try { const [personal,shopping]=await Promise.allSettled([api('/personal-wishes'),api('/shopping?sort=priority')]);if(personal.status==='fulfilled')setData(personal.value);if(shopping.status==='fulfilled')setFamilyItems(shopping.value.items || []);setError([personal,shopping].filter(r=>r.status==='rejected').map(r=>r.reason.message).join(' ')); } catch (err) { setError(err.message); } };
  useEffect(() => { load(); const refresh = () => load(); window.addEventListener('wishlist-updated', refresh); window.addEventListener('shopping-updated', refresh); return () => { window.removeEventListener('wishlist-updated', refresh); window.removeEventListener('shopping-updated', refresh); }; }, []);
  const open = (wish) => {
    setError(''); setSavedNotice(''); setEditing(wish?.id || null);
    const eligible = new Set(data.audience.map((person) => person.id));
    const viewerIds = wish
      ? wish.viewer_ids.filter((id) => eligible.has(id))
      : data.audience.map((person) => person.id);
    setShareWithFamily(wish ? viewerIds.length > 0 : true);
    setGift(wish ? { visibility: wish.visibility || (viewerIds.length ? 'custom' : 'private'), occasion: wish.occasion || '', name: wish.item.name, priority: wish.item.priority, description: wish.item.description || '', store_name: wish.item.store_name || '', product_url: wish.item.product_url || '', image_url: wish.item.image_path || '', estimated_price: wish.item.estimated_price || '', viewer_ids: viewerIds } : { name: '', description: '', store_name: '', product_url: '', image_url: '', estimated_price: '', viewer_ids: viewerIds });
    setShow(true);
  };
  const save = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    try { await api('/personal-wishes' + (editing ? '/' + editing : ''), { method: editing ? 'PATCH' : 'POST', body: JSON.stringify(gift) }); await load(); setShow(false); window.dispatchEvent(new Event('wishlist-updated')); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const changeSharing = async (wish, visibility) => {
    setBusy(true); setError('');
    try {
      await api('/personal-wishes/' + wish.id, {method:'PATCH', body:JSON.stringify({visibility})});
      await load(); window.dispatchEvent(new Event('wishlist-updated'));
    } catch(err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const remove = async (id) => { setBusy(true); setError(''); try { await api('/personal-wishes/' + id, { method: 'DELETE' }); await load(); window.dispatchEvent(new Event('wishlist-updated')); } catch (err) { setError(err.message); } finally { setBusy(false); } };
  const hold = async (item) => { setBusy(true); setError(''); try { await api('/items/' + item.id + '/reservations', { method: 'POST', body: JSON.stringify({ quantity: 1, reuse_existing: true }) }); await load(); window.dispatchEvent(new Event('shopping-updated')); } catch (err) { setError(err.message); } finally { setBusy(false); } };
  const groups=[...new Set([...data.mine.filter(w=>matches(w.item)).map(w=>w.occasion || 'Everyday'),...families.flatMap(i=>i.occasions?.length?i.occasions:['Everyday'])])];
  return <section><BudgetFilters minimum={minimum} maximum={maximum} currency={currency} onMinimum={setMinimum} onMaximum={setMaximum} onCurrency={setCurrency} onClear={()=>{setMinimum('');setMaximum('');setQuery('');}} prefix="family-wishes-budget"><Form.Group controlId="family-wishes-search" className="mb-3"><Form.Label>Search family wishes</Form.Label><Form.Control type="search" placeholder="Gifts, people or occasions" value={query} onChange={e=>setQuery(e.target.value)}/></Form.Group></BudgetFilters><ErrorAlert message={error} />{groups.length ? <>{groups.map(group=><section key={group} className="mb-4"><h3>{group}</h3><Row className="g-3 shopping-status-rail">{data.mine.filter(wish=>(wish.occasion || 'Everyday')===group && matches(wish.item)).map((wish) => {
    const names = data.audience.filter((person) => wish.viewer_ids.includes(person.id)).map((person) => person.name);
    return <Col md={6} lg={4} key={wish.id}><Card className="gift-card wish-manage-card"><Card.Body><div className="wish-card-actions"><Dropdown className="wish-sharing-menu"><Dropdown.Toggle variant="light" className="wish-icon-button" disabled={busy} aria-label={'Change sharing for '+wish.item.name} title={wishAudience(wish,names)}><WishVisibilityIcon visibility={wishIsPrivate(wish)?"private":wish.visibility || "custom"} label={wishAudience(wish,names)}/></Dropdown.Toggle><Dropdown.Menu><Dropdown.Header>Who can see this?</Dropdown.Header>{[['private','Private'],['family','My household'],['followers','Families following me'],['public','Public - anyone']].map(([value,label])=><Dropdown.Item key={value} active={wish.visibility===value || value==='private' && wishIsPrivate(wish)} onClick={()=>changeSharing(wish,value)}>{label}</Dropdown.Item>)}</Dropdown.Menu></Dropdown><Button className="wish-icon-button" variant="light" aria-label="Edit wish / sharing" title="Edit wish / sharing" disabled={busy} onClick={() => open(wish)}><svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="m16 3 5 5-12 12-6 1 1-6L16 3Z M13 6l5 5"/></svg></Button><Button className="wish-icon-button" variant="light" aria-label="Remove wish" title="Remove wish" disabled={busy} onClick={() => remove(wish.id)}><span aria-hidden="true">&times;</span></Button></div><GiftSummaryRow item={wish.item} actions={<Button size="sm" variant="outline-secondary" onClick={()=>setDetailEdit(wish)}>Edit gift</Button>}/></Card.Body></Card></Col>;
  })}{families.filter(item=>(item.occasions?.length?item.occasions:['Everyday']).includes(group)).map(item=><Col md={6} lg={4} key={'family-'+item.id}><Card className="gift-card"><Card.Body><WishVisibilityIcon visibility={item.family_only?'family':'followers'} label={item.family_only?'Family only':'Shared with invited families'}/><GiftCardContent item={item} onReserve={()=>hold(item)} onReserveRefresh={load} viewWish/></Card.Body></Card></Col>)}</Row></section>)}</> : <div className="empty-state"><h3>Your wishes, your audience</h3><p>Add something you want and share it only with your spouse or chosen family members.</p></div>}
  <EditGiftDialog item={detailEdit?.item} endpoint={detailEdit?'/personal-wishes/'+detailEdit.id:undefined} onClose={()=>setDetailEdit(null)} onSaved={load}/><h2 className="mt-5">Wishes shared with me</h2><p className="text-secondary"></p>{data.shared.length ? <Row className="g-3 shopping-status-rail">{data.shared.filter(wish=>matches(wish.item)).map((wish) => <Col md={6} lg={4} key={wish.id}><Card className="gift-card"><Card.Body><GiftCardContent item={wish.item} onReserve={() => hold(wish.item)} onReserveRefresh={load} /></Card.Body></Card></Col>)}</Row> : <p>No wishes shared with you yet.</p>}
  <Modal show={show} onHide={() => setShow(false)} centered size="lg"><Modal.Header closeButton><Modal.Title>{editing ? 'Edit my wish' : 'A wish for me'}</Modal.Title></Modal.Header><Form onSubmit={save}><Modal.Body><Alert variant="info">Saved to Wishlist / Wishes / My wishes. New wishes are shared with eligible invited family members by default. Turn sharing off to keep a wish private to this login. Ideas for someone else go in Saved items / Saved items.</Alert><ErrorAlert message={error} />{savedNotice && <Alert variant="success" role="status">{savedNotice}</Alert>}{editing && data.mine.find(w=>w.id===editing) && <WishOrganize inline item={data.mine.find(w=>w.id===editing).item} onChanged={()=>{setShow(false);load();}}/>}<Form.Group controlId="personal-occasion" className="mb-3"><Form.Label>Occasion</Form.Label><Form.Select value={gift.occasion || ""} onChange={e=>setGift({...gift,occasion:e.target.value})}>{["", "Christmas", "Birthday", "Wedding", "Baby shower", "Anniversary", "Halloween", "Easter"].map(name=><option key={name} value={name}>{name || "Everyday / just because"}</option>)}</Form.Select></Form.Group><Form.Group controlId="personal-priority" className="mb-3"><Form.Label>Priority</Form.Label><Form.Select value={gift.priority || 2} onChange={e => setGift({ ...gift, priority: Number(e.target.value) })}><option value="4">Have to have it</option><option value="3">Really, really want it</option><option value="2">Really want it</option><option value="1">It&apos;s okay if I get it</option></Form.Select></Form.Group><fieldset className="personal-wish-audience mb-4"><legend className="fs-6 fw-semibold">Who can see this wish?</legend><Form.Check id="personal-wish-public" type="checkbox" label="Public to invited family members" checked={shareWithFamily} disabled={!data.audience.length} onChange={(event) => { const enabled = event.target.checked; const viewerIds = enabled ? data.audience.map((person) => person.id) : []; setShareWithFamily(enabled); setGift({ ...gift, visibility: enabled ? 'custom' : 'private', viewer_ids: viewerIds }); }} /><p className="small mt-2">{shareWithFamily ? 'People invited to view your family’s shared lists can see this wish.' : 'This wish is private to this login.'}</p>{data.audience.length > 0 && shareWithFamily && <><p className="small mb-2">Choose which eligible accounts can see it; new wishes start shared with everyone listed.</p><Button type="button" size="sm" variant="link" className="p-0 mb-2" onClick={() => { const viewerIds = gift.viewer_ids.length === data.audience.length ? [] : data.audience.map((person) => person.id); setShareWithFamily(viewerIds.length > 0); setGift({ ...gift, visibility:viewerIds.length?'custom':'private', viewer_ids: viewerIds }); }}>{gift.viewer_ids.length === data.audience.length ? 'Deselect all' : 'Select all invited family members'}</Button><Form.Control type="search" className="mb-2" aria-label="Find people to share with" placeholder="Search family members or shared family names" value={audienceQuery} onChange={e => setAudienceQuery(e.target.value)} />{data.audience.filter(person => [person.name, ...person.families].join(' ').toLowerCase().includes(audienceQuery.toLowerCase())).sort((a,b) => Number(Boolean(b.is_my_family)) - Number(Boolean(a.is_my_family)) || a.name.localeCompare(b.name)).map((person) => <Form.Check key={person.id} id={'wish-viewer-' + person.id} label={person.name + ' / ' + person.families.join(', ')} checked={gift.viewer_ids.includes(person.id)} onChange={(e) => { const viewerIds = e.target.checked ? [...gift.viewer_ids, person.id] : gift.viewer_ids.filter((id) => id !== person.id); setShareWithFamily(viewerIds.length > 0); setGift({ ...gift, visibility:viewerIds.length?'custom':'private', viewer_ids: viewerIds }); }} />)}</>}{!data.audience.length && <p className="small text-secondary">No eligible invited family accounts yet, so the wish stays private until you invite family members.</p>}</fieldset>{!editing && <StoreGiftFinder favoriteProfile={profiles.find(p=>p.is_me&&p.can_edit)} favoriteProfiles={profiles} onFavoriteSaved={load} gift={{ name: '' }} onChange={() => {}} savedUrls={data.mine.map(wish => wish.item.product_url)} onSaveProduct={async product => { await api('/personal-wishes', { method: 'POST', body: JSON.stringify({ ...product, occasion: gift.occasion || "", priority: gift.priority || 2, visibility: gift.visibility || 'custom', viewer_ids: gift.viewer_ids }) }); await load(); setSavedNotice(gift.viewer_ids.length ? "Saved in Wishes / My wishes, shared with your selected accounts." : "Saved in Wishes / My wishes. This account only; you can share it later."); window.dispatchEvent(new Event('wishlist-updated')); }} />}</Modal.Body><Modal.Footer><Button variant="outline-secondary" onClick={() => setShow(false)}>Cancel</Button>{editing ? <Button type="submit" variant="success" disabled={busy}>{busy ? "Saving..." : "Save sharing / priority"}</Button> : <Button type="button" variant="success" onClick={() => setShow(false)}>Done browsing</Button>}</Modal.Footer></Form></Modal></section>;
}

function FollowingPage({games=false}) {
 const [followingBudget,setFollowingBudget]=useState({minimum:'',maximum:'',currency:'USD'});
 const {user,households,refresh}=useSession();const [params]=useSearchParams();
 const [requestCount,setRequestCount]=useState(0);
 const tab=games?'games':['families',...(requestCount?['requests']:[]),'games'].includes(params.get('tab'))?params.get('tab'):'families';
 const [requestOpen,setRequestOpen]=useState(false),[familiesOpen,setFamiliesOpen]=useState(false),[selected,setSelected]=useState(null);
 useEffect(()=>{const sync=()=>{if(document.visibilityState!=='hidden'){refresh().catch(()=>{});api('/invitations').then(data=>setRequestCount([...(data.sent||[]),...(data.received||[])].filter(row=>row.status==='pending').length)).catch(()=>{});}};sync();const timer=setInterval(sync,15000);window.addEventListener('invitations-updated',sync);window.addEventListener('notifications-updated',sync);return()=>{clearInterval(timer);window.removeEventListener('invitations-updated',sync);window.removeEventListener('notifications-updated',sync);};},[]);
 const followed=households.filter(h=>!['owner','admin','family_member'].includes(h.role));
 const homes=households.filter(h=>['owner','admin','family_member'].includes(h.role) && h.registry_type!=='company');
 const familyCard=h=><HouseholdCard key={h.id} household={h} onOpen={()=>{setSelected(h);setFamiliesOpen(true);}}/>;
 return <Container className="page-wrap"><div className="following-toolbar mb-4"><Nav variant="pills" activeKey={tab}>{['families',...(requestCount?['requests']:[]),'games'].map(name=><Nav.Link as={Link} key={name} to={'/following?tab='+name} active={tab===name}>{name==='families'?'People & families':name==='requests'?'Requests ('+requestCount+')':'Games'}</Nav.Link>)}</Nav><div className="d-flex gap-2 flex-wrap"><Button variant="outline-success" onClick={()=>setRequestOpen(true)}>Find people to follow</Button><Button onClick={()=>document.getElementById("following-search-trigger")?.click()}>Search gifts</Button></div></div>
 <AdSlot placement="following" compact hideEmpty/>{tab==='games'?<GiftGamesPage embedded GiftFinder={StoreGiftFinder} activeProfileId={user.active_member_profile_id}/>:tab==='requests'?<><Button onClick={()=>setRequestOpen(true)}>Find people to follow</Button><InvitationInbox pendingOnly/></>:<><div className="mb-3"><Button size="sm" variant="outline-success" onClick={()=>{setSelected(null);setFamiliesOpen(true);}}>People & families ({followed.length})</Button></div><div className="family-rail mb-4">{followed.map(familyCard)}</div><GiftDashboardRows budgetFilter={followingBudget} onBudgetChange={setFollowingBudget} scope="following" triggerId="following-search-trigger" hideTrigger/></>}
 {tab!=='families' && <GiftDashboardRows scope="following" searchOnly triggerId="following-search-trigger" hideTrigger/>}<Modal show={requestOpen} onHide={()=>setRequestOpen(false)} centered><Modal.Header closeButton><Modal.Title>Find people to follow</Modal.Title></Modal.Header><Modal.Body><InviteRequestComposer homes={homes}/></Modal.Body></Modal>
 <Modal show={familiesOpen} onHide={()=>setFamiliesOpen(false)} size="xl" centered scrollable><Modal.Header closeButton><Modal.Title>{selected?selected.name:'People & families'}</Modal.Title></Modal.Header><Modal.Body>{selected?<><Button variant="link" className="mb-3" onClick={()=>setSelected(null)}>People & families</Button><FollowedFamilyBrowser key={selected.id} household={selected} budget={followingBudget} onBudgetChange={setFollowingBudget} renderGift={(item,refresh)=><GiftCardContent item={item} onReserveRefresh={refresh}/>}/></>:<><Row className="g-3">{followed.map(h=><Col key={h.id} xs={12} sm={6} lg={4}>{familyCard(h)}</Col>)}</Row>{!followed.length && <p>You aren?t following anyone yet. Find people or families to see their shared wishes.</p>}</>}</Modal.Body></Modal>
 </Container>;
}

function DiscoverPage() {
 const {households,refresh,user}=useSession();
 const [data,setData]=useState({family_profiles:[]}),[recommendations,setRecommendations]=useState({wishes:[],buys:[]}),[error,setError]=useState('');
 const load=async()=>{try{setData(await api('/wishlist'));setError('');}catch(err){setError(err.message);}};
 const recommend=()=>api('/gift-recommendations').then(setRecommendations).catch(()=>{});
 useEffect(()=>{const refresh=()=>{load();recommend();};refresh();window.addEventListener('wishlist-updated',refresh);return()=>window.removeEventListener('wishlist-updated',refresh);},[]);
 const save=async product=>{await api('/personal-wishes',{method:'POST',body:JSON.stringify({...product,image_url:product.thumbnail || '',visibility:'followers',viewer_ids:[],priority:2,quantity:1})});await load();window.dispatchEvent(new Event('wishlist-updated'));};
 return <Container className="page-wrap"><div className="section-heading mb-4"><h1>Discover</h1><div className="d-flex flex-wrap gap-2"><UniversalGift profiles={data.family_profiles} onSaved={load}/><QuickAddGifts profiles={data.family_profiles} onSaved={load}/></div></div><ErrorAlert message={error}/><section className="discover-preferences mb-4"><h2>Better gifts start with your favorites</h2><p>Save your favorite brands, stores, colors and sizes so people know what you love. Parents can add what children and pets are into right now.</p>{data.family_profiles.filter((p,i,rows)=>p.can_edit && rows.findIndex(row=>row.id===p.id)===i).map(profile=><DiscoverGiftProfile key={profile.id} profile={profile}><FamilyEditor households={households} refresh={async()=>{await refresh();await load();}} BirthdayInput={BirthdayInput} RelationshipSelect={RelationshipSelect} initialHome={profile.household_id} initialPerson={String(profile.id)} label={(profile.completion?.percent===100?'Edit ':'Complete ')+profile.display_name+"'s gift profile"}/></DiscoverGiftProfile>)}</section><AdSlot placement="discover" sponsoredRow hideEmpty/><section className="mb-4"><h2>Ideas for your wishlist</h2>{recommendations.wishes.length?<StoreGiftFinder favoriteProfiles={data.family_profiles} onFavoriteSaved={load} renderActions={product=><ProductActions product={product} profiles={data.family_profiles} selfName={user.name} onSaved={load}/>} initialProducts={recommendations.wishes} resultsOnly gift={{name:''}} onChange={()=>{}} onSaveProduct={save}/>:<p className="text-secondary">Search gifts to find your next favorite.</p>}</section><section><h2>Gifts to give</h2>{recommendations.buys.length?<GiftRail title="Gifts to give">{recommendations.buys.map(item=><Card className="gift-card" key={item.id}><Card.Body><GiftCardContent item={item} onReserve={async()=>{await api('/items/'+item.id+'/reservations',{method:'POST',body:JSON.stringify({quantity:1,reuse_existing:true})});recommend();}} onReserveRefresh={recommend}/></Card.Body></Card>)}</GiftRail>:<p className="text-secondary">Follow people and families to find gifts they want.</p>}</section></Container>;
}



function QuickAddGifts({ profiles = [], onSaved }) {
  const [addParams]=useSearchParams();
  const [searchOpen,setSearchOpen]=useState(addParams.get('add')==='1');
  const [mode,setMode]=useState('me'),[person,setPerson]=useState(''),[lists,setLists]=useState([]),[list,setList]=useState(''),[occasion,setOccasion]=useState('');
  const [visibility,setVisibility]=useState('followers');
  const [audience,setAudience]=useState([]),[viewers,setViewers]=useState([]),[message,setMessage]=useState(''),[error,setError]=useState('');
  useEffect(()=>{api('/personal-wishes').then(data=>{const eligible=data.audience || [];setAudience(eligible);setViewers(eligible.map(person=>person.id));}).catch(err=>setError(err.message));const focus=()=>{setMode('me');document.getElementById('quick-add')?.scrollIntoView?.({behavior:'smooth'});};window.addEventListener('quick-add-for-me',focus);return()=>window.removeEventListener('quick-add-for-me',focus);},[]);
  useEffect(()=>{let active=true;setLists([]);setList('');if(mode==='family' && person) api('/profiles/'+person+'/wishlists').then(data=>{if(active){setLists(data.wishlists);setList(String(data.wishlists[0]?.id || ''));}}).catch(err=>{if(active)setError(err.message);});return()=>{active=false;};},[mode,person]);
  async function save(product) {
    const recipient=profiles.find(p=>String(p.id)===person);
    if(mode==='family' && !recipient?.can_suggest && !list)throw new Error('Choose a family member and wishlist first.');
    if(mode==='idea' && !recipient)throw new Error('Choose who this gift idea is for first.');
    await api(mode==='me'?'/personal-wishes':mode==='family'?(recipient?.can_suggest?'/profiles/'+person+'/suggestions':'/wishlists/'+list+'/items'):'/private-gifts',{method:'POST',body:JSON.stringify({...product,priority:2,quantity:1,...(mode==='me'?{viewer_ids:viewers,occasion,visibility}:mode==='idea'?{recipient:recipient.display_name,household_name:recipient.household_name,occasion}:{})})});
    setMessage(mode==='me'?'Saved to My wishes.':mode==='family'?(recipient?.can_suggest?'Suggestion sent.':'Saved to '+recipient?.display_name+' wishlist.'):'Saved items for '+recipient.display_name+'.');
    await onSaved();window.dispatchEvent(new Event('wishlist-updated'));
  }
  return <section id="quick-add" className="mb-4">
    <Button onClick={() => setSearchOpen(true)}>Search gifts</Button>
    <Modal show={searchOpen} onHide={() => setSearchOpen(false)} size="xl" centered scrollable>
      <Modal.Header closeButton><Modal.Title>Search gifts or add a link</Modal.Title></Modal.Header>
      <Modal.Body>
        <div className="d-flex gap-3 flex-wrap mb-3">
          <Form.Group controlId="quick-add-destination">
            <Form.Label>Save to</Form.Label>
            <Form.Select value={mode} onChange={event => { setMode(event.target.value); setPerson(''); setMessage(''); }}>
              <option value="me">My wishes</option>
              <option value="family">A family member's wishlist</option>
              <option value="idea">Gift for someone else</option>
            </Form.Select>
          </Form.Group>
          {mode !== 'me' && <Form.Group controlId="quick-add-person">
            <Form.Label>For</Form.Label>
            <Form.Select value={person} onChange={event => setPerson(event.target.value)}>
              <option value="">Choose a person</option>
              {profiles.filter(profile => mode === 'idea' || profile.can_edit || profile.can_add || profile.can_suggest).map(profile => <option key={profile.household_id + ':' + profile.id} value={profile.id}>{profile.display_name} / {profile.household_name}</option>)}
            </Form.Select>
          </Form.Group>}
          {mode === 'family' && profiles.find(profile => String(profile.id) === person)?.can_suggest
            ? <p className="small">They will approve this suggestion before it is added.</p>
            : mode === 'family'
              ? <Form.Group controlId="quick-add-list">
                <Form.Label>Wishlist / occasion</Form.Label>
                <Form.Select value={list} onChange={event => setList(event.target.value)}>
                  <option value="">Choose a list</option>
                  {lists.map(row => <option key={row.id} value={row.id}>{row.title}</option>)}
                </Form.Select>
              </Form.Group>
              : <Form.Group controlId="quick-add-occasion">
                <Form.Label>Occasion / list</Form.Label>
                <Form.Select value={occasion} onChange={event => setOccasion(event.target.value)}>
                  {['', 'Christmas', 'Birthday', 'Stocking stuffers', 'Anniversary', 'Wedding', 'Baby shower', 'Easter', 'Halloween'].map(name => <option key={name} value={name}>{name || 'Everyday'}</option>)}
                </Form.Select>
              </Form.Group>}
        </div>
        {mode === 'me' && <div className="mb-3">
          <WishAudiencePicker value={visibility} onChange={setVisibility} />
          {visibility === 'custom' && <fieldset>
            <legend className="fs-6">Choose invited family accounts</legend>
            {audience.length
              ? audience.map(person => <Form.Check key={person.id} id={'quick-add-viewer-' + person.id} label={person.name + ' / ' + person.families.join(', ')} checked={viewers.includes(person.id)} onChange={event => setViewers(current => event.target.checked ? [...new Set([...current, person.id])] : current.filter(id => id !== person.id))} />)
              : <p className="small text-secondary">No invited family accounts are available yet.</p>}
          </fieldset>}
        </div>}
        {message && <Alert variant="success" role="status">{message}</Alert>}
        <ErrorAlert message={error} />
        <StoreGiftFinder favoriteProfile={mode==='me'?profiles.find(p=>p.is_me&&p.can_edit):profiles.find(p=>String(p.id)===person)} favoriteProfiles={profiles} onFavoriteSaved={onSaved} priceFilter={{minimum:addParams.get("min_price")||"",maximum:addParams.get("max_price")||"",currency:addParams.get("currency")||"USD"}} gift={{ name: '' }} onChange={() => {}} onSaveProduct={save} />
      </Modal.Body>
    </Modal>
  </section>;
}

function PastGifts({privateGifts=[]}) {
 const [open,setOpen]=useState(false),[rows,setRows]=useState([]),[query,setQuery]=useState(''),[occasion,setOccasion]=useState(''),[source,setSource]=useState('all'),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 useEffect(()=>{if(!open)return;let active=true;setLoading(true);setError('');api('/my-shopping').then(data=>{if(active)setRows(data.reservations.filter(r=>r.status==='purchased').map(r=>({...r.item,historyKey:'purchase-'+r.id,source:'registry',quantity:r.quantity})));}).catch(err=>{if(active)setError(err.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[open]);
 const gifts=[...rows,...privateGifts.filter(g=>g.status==='purchased').map(g=>({...g,historyKey:'idea-'+g.id,source:'idea'}))];
 const occasionOf=g=>(g.occasions?.length?g.occasions:[g.occasion]).filter(Boolean);
 const occasions=[...new Set(gifts.flatMap(occasionOf))].sort();
 const visible=gifts.filter(g=>(source==='all'||source===g.source)&&(!occasion||occasionOf(g).includes(occasion))&&[g.name,g.recipient,g.household_name,g.store_name,...(g.households||[]).map(h=>h.name),...occasionOf(g)].filter(Boolean).join(' ').toLowerCase().includes(query.trim().toLowerCase()));
 return <><Button variant="outline-secondary" className="past-gifts-button" onClick={()=>setOpen(true)}>Past gifts</Button><Modal show={open} onHide={()=>setOpen(false)} size="lg" centered scrollable><Modal.Header closeButton><Modal.Title>Past gifts</Modal.Title></Modal.Header><Modal.Body><Form className="d-flex gap-2 flex-wrap mb-3" onSubmit={e=>e.preventDefault()}><Form.Control type="search" aria-label="Search past gifts" placeholder="Search gifts, people or families" value={query} onChange={e=>setQuery(e.target.value)}/><Form.Select aria-label="Past gift occasion" value={occasion} onChange={e=>setOccasion(e.target.value)}><option value="">All occasions</option>{occasions.map(o=><option key={o}>{o}</option>)}</Form.Select><Form.Select aria-label="Past gift type" value={source} onChange={e=>setSource(e.target.value)}><option value="all">All gifts</option><option value="registry">Wishlist gifts</option><option value="idea">Private ideas</option></Form.Select></Form><ErrorAlert message={error}/>{loading?<Loading label="Loading past gifts..."/>:!error && <>{visible.length?<div className="table-responsive"><table className="table align-middle"><thead><tr><th>Gift</th><th>For</th><th>Occasion</th><th>Store</th></tr></thead><tbody>{visible.map(g=><tr key={g.historyKey}><td><span className="item-title" title={g.name}>{g.name}</span></td><td>{g.recipient || '-'}</td><td>{occasionOf(g).join(', ') || '-'}</td><td>{g.product_url?<a href={g.product_url} target="_blank" rel="noopener noreferrer">{g.store_name || 'View store'}</a>:g.store_name || '-'}</td></tr>)}</tbody></table></div>:<p>No past gifts match.</p>}</>}</Modal.Body></Modal></>;
}

function PrivateBuyingItems({items,onChanged}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 async function move(item,body){setBusy(true);setError('');try{await api('/private-gifts/'+item.id,{method:'PATCH',body:JSON.stringify(body)});await onChanged();window.dispatchEvent(new Event('wishlist-updated'));}catch(err){setError(err.message);}finally{setBusy(false);}}
 return <><ErrorAlert message={error}/><div className="private-buying-items">{items.map(item=><Card key={item.id} className="mb-3"><Card.Body className="d-flex flex-wrap gap-3">{item.image_url&&<img src={item.image_url} alt="" width="72" height="90" style={{objectFit:'contain'}}/>}<div className="flex-grow-1"><h3 className="h5">{item.name}</h3><p className="small">For {item.recipient}{item.estimated_price?' / '+item.currency+' '+item.estimated_price:''}</p><div className="d-flex flex-wrap gap-2">{item.product_url&&<Button as="a" href={item.product_url} target="_blank" rel="noopener noreferrer">Visit store</Button>}<Button variant="outline-success" disabled={busy} onClick={()=>move(item,{buying_now:false})}>Save for later</Button><Button variant="outline-secondary" disabled={busy} onClick={()=>move(item,{status:'purchased'})}>Mark purchased</Button></div></div></Card.Body></Card>)}</div></>;
}

function WishlistPage({area="wishes",embedded=false,initialTab=null}) {
  const { user, households } = useSession();
  const [params, setParams] = useSearchParams();
  const [savedQuery, setSavedQuery] = useState('');
  const [giftingTab,setGiftingTab]=useState(initialTab || (params.get('view')==='buying'?'buying':'saved'));
  const matchesSaved = item => [item.name,item.recipient,item.household_name,item.occasion].filter(Boolean).join(' ').toLowerCase().includes(savedQuery.trim().toLowerCase());
  const section = params.get('section') === 'plans' ? 'plans' : 'personal';
  useEffect(()=>{if(params.get('section')) document.getElementById(section==='plans'?'my-gifting':'my-wishes')?.scrollIntoView?.({block:'start'});},[section]);
  const [data, setData] = useState({ hearted: [], private_gifts: [], family_profiles: [] });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [gift, setGift] = useState({ name: "", recipient: "", household_name: "", occasion: "", store_name: "", product_url: "", estimated_price: "" });
  const load = async () => { try { const result = await api('/wishlist'); setData(result); setError(""); } catch (err) { setError(err.message); } };
  useEffect(() => { load(); const refresh = () => load(); window.addEventListener('wishlist-updated', refresh); window.addEventListener('shopping-updated', refresh); return () => { window.removeEventListener('wishlist-updated', refresh); window.removeEventListener('shopping-updated', refresh); }; }, [section]);
  const mutate = async (path, method, body) => {
    setBusy(true); setError("");
    try { await api(path, { method, ...(body ? { body: JSON.stringify(body) } : {}) }); await load(); return true; }
    catch (err) { setError(err.message); return false; }
    finally { setBusy(false); }
  };
  const savePrivate = async (event) => {
    event.preventDefault();
    if (await mutate('/private-gifts', 'POST', gift)) { setShowForm(false); setGift({ name: "", recipient: "", household_name: "", occasion: "", store_name: "", product_url: "", estimated_price: "" }); }
  };
  const savedCount=data.hearted.filter(item=>!item.availability?.held_by_you).length + data.private_gifts.filter(item=>item.status!=='purchased'&&!item.buying_now).length;
  const hasSaved=savedCount>0;
  useEffect(()=>{if(savedCount<=9)setSavedQuery('');},[savedCount]);
  return <Container className={embedded?"p-0":"page-wrap"}>{!embedded&&<div className="d-flex flex-wrap justify-content-between align-items-center gap-3"><div><p className="small-label">Your family</p><h1 className="page-title">{area==="gifting"?"Saved items":"My wishes"}</h1></div></div>}<ErrorAlert message={error} />{!embedded&&!households.length && <DashboardPage manageOnly />}{area==="wishes" && <><div className="wish-actions mb-3"><p>Save gifts you want. Share them with your family.</p><div><Button as={Link} to="/discover">Add a wish</Button><UniversalGift profiles={data.family_profiles} onSaved={load}/><CreateWishlist profiles={data.family_profiles}/></div></div></>}
    {area==='wishes' && <section id="my-wishes"><MyWishlistLists profiles={data.family_profiles}/><h2 id="family-wishes">My family wishes</h2><div className="family-rail mb-3">{households.filter(h=>['owner','admin','family_member'].includes(h.role)).map(h=><HouseholdCard key={h.id} household={h}/>)}</div><FamilyRows profiles={data.family_profiles.filter(p=>households.some(h=>String(h.id)===String(p.household_id) && ["owner","admin","family_member"].includes(h.role)))} renderMember={profile=><MemberCard profile={profile}/>}/><PersonalWishesPanel profiles={data.family_profiles}/></section>}
    {area==='gifting' && <section id="my-gifting"><div className="gifting-toolbar mb-3"><Nav variant="pills" activeKey={giftingTab}><Nav.Link active={giftingTab==='buying'} onClick={()=>setGiftingTab('buying')}><ShoppingBagIcon/> Buying now</Nav.Link><Nav.Link active={giftingTab==='saved'} onClick={()=>setGiftingTab('saved')}><HeartIcon/> Saved items{savedCount>0?' ('+savedCount+')':''}</Nav.Link></Nav><PastGifts privateGifts={data.private_gifts}/></div>{giftingTab==='buying'?<><MyShoppingPage embedded statusFilter="reserved" hideHeading showEmpty={!data.private_gifts.some(item=>item.buying_now)}/><PrivateBuyingItems items={data.private_gifts.filter(item=>item.buying_now)} onChanged={load}/></>:<><GiftDashboardRows scope="following" searchOnly buttonLabel="Add gift"/>{savedCount>9 && <Form.Control type="search" className="mb-4" aria-label="Search saved gifts" placeholder="Search gifts or people" value={savedQuery} onChange={e=>setSavedQuery(e.target.value)} />}<Row className="g-3 shopping-status-rail">{[...data.hearted.filter(item=>!item.availability?.held_by_you).map(item=>({...item,ideaType:'heart'})),...data.private_gifts.filter(item=>item.status!=='purchased'&&!item.buying_now).map(item=>({...item,ideaType:'plan'}))].filter(matchesSaved).map(item=><Col md={6} lg={4} key={item.ideaType+item.id}><Card className="gift-card"><Card.Body><GiftIdentity item={item}/><h3 className="item-title" title={item.name}>{item.name}</h3>{item.ideaType==='heart' ? <><div className="gift-icon-actions"><Button as={Link} variant="link" to={item.personal_wish ? '/wishlist' : '/profiles/'+item.profile_id}>View wish</Button><HeartButton item={item}/>{item.availability && <BuyGiftButton item={item} alreadyHeld={Boolean(item.availability?.held_by_you)} onHeld={load}/>} {item.availability && (item.availability.available>0 || item.availability.held_by_you) && <CoBuyInvite item={item} onHeld={load}/>}</div><GiftAvailability availability={item.availability}/></> : <><Badge bg="light" text="dark">Private idea</Badge><Button size="sm" variant="outline-success" className="mt-2" disabled={busy} onClick={()=>mutate('/private-gifts/'+item.id,'PATCH',{buying_now:true})}>Buying now</Button><div className="d-flex gap-2 flex-wrap mt-3">{item.product_url && <Button as="a" size="sm" href={item.product_url} target="_blank" rel="noopener noreferrer">{item.status==='purchased' ? 'View store' : 'Shop this idea'}</Button>}<Button size="sm" variant="outline-success" disabled={busy} onClick={()=>mutate('/private-gifts/'+item.id,'PATCH',{status:item.status==='purchased'?'planned':'purchased'})}>{item.status==='purchased'?'Mark not purchased':'Mark purchased'}</Button><Button className="heart-button" size="sm" variant="outline-success" aria-label="Remove from Saved items" title="Remove from Saved items" aria-pressed={true} disabled={busy} onClick={()=>mutate('/private-gifts/'+item.id,'DELETE')}><HeartIcon filled/></Button></div>{item.status==='purchased' && <p className="small mt-2">Purchased</p>}</>}<PriceComparison item={item}/></Card.Body></Card></Col>)}</Row>{!hasSaved && <div className="empty-state"><h3>No gift ideas yet</h3><p>Heart a gift in Discover or Following to save it here.</p></div>}</>}{!embedded&&<AdvertisingSpace/>}</section>}


  </Container>;
}

function ShoppingPage({ embedded = false }) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState("recent");
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const load = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      params.set("sort", sort);
      setItems((await api(`/shopping?${params.toString()}`)).items);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { load(); }, [sort]);
  const search = (event) => { event.preventDefault(); load(); };
  const reserve = async (item) => {
    try {
      await api(`/items/${item.id}/reservations`, { method: "POST", body: JSON.stringify({ quantity: 1 }) });
      await load();
    } catch (err) { setError(err.message); }
  };
  return <Container className={embedded ? "p-0" : "page-wrap"}><p className="small-label">A little inspiration</p><h2>Browse shared wishes</h2><p className="text-secondary">Browse wishes from the family circles you belong to. Your plans stay private.</p><Card className="filter-card"><Card.Body><Form onSubmit={search}><Row className="g-2 align-items-end"><Col md={8}><Form.Group controlId="shopping-query"><Form.Label>Find a person, gift, or store</Form.Label><Form.Control value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Try “books” or a family member’s name" /></Form.Group></Col><Col md={2}><Form.Group controlId="shopping-sort"><Form.Label>Sort by</Form.Label><Form.Select value={sort} onChange={(e) => setSort(e.target.value)}><option value="recent">Recently added</option><option value="priority">Most wanted</option><option value="price">Price</option></Form.Select></Form.Group></Col><Col md={2}><Button type="submit" className="w-100" variant="success">Search</Button></Col></Row></Form></Card.Body></Card><ErrorAlert message={error} onDismiss={() => setError("")} />{loading ? <Loading label="Gathering gift ideas…" /> : items.length ? <Row className="g-3 mt-1">{items.map((item) => <Col key={item.id} md={6} lg={4}><Card className="gift-card"><Card.Body><p className="small-label">For {item.recipient}</p><GiftCardContent item={item} onReserve={() => reserve(item)} onReserveRefresh={() => load(true)} /></Card.Body></Card></Col>)}</Row> : <div className="empty-state"><span aria-hidden="true">🌼</span><h3>No gift ideas found</h3><p>When a family member adds a wish, it will bloom here.</p></div>}</Container>;
}

export function PriceComparison({ item, onHeld }) {
  const [show, setShow] = useState(false);
  const [products, setProducts] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const compare = async () => { setShow(true); setBusy(true); setError(''); setMessage(''); setProducts([]); try { const query = [item.name, item.desired_size, item.desired_color].filter(Boolean).join(' ').slice(0,200); const data = await api('/gift-discovery?q=' + encodeURIComponent(query)); const offers = (data.products || []).filter(product => product.currency === 'USD' && product.estimated_price !== '' && product.estimated_price != null && Number.isFinite(Number(product.estimated_price))).sort((a,b) => Number(a.estimated_price) - Number(b.estimated_price)); setProducts(offers); if (!offers.length) setMessage(data.message || 'No priced offers found. Try searching stores for this product.'); } catch(err) { setError(err.message); } finally { setBusy(false); } };
  return <><Button type="button" variant="link" size="sm" className="px-0 d-block" onClick={compare}>Compare prices</Button><Modal show={show} onHide={() => setShow(false)} size="lg" centered><Modal.Header closeButton><Modal.Title>Compare prices for {item.name}</Modal.Title></Modal.Header><Modal.Body><p className="small text-secondary">Similar offers, lowest listed price first. Check the exact model, size, color, and quantity. Shipping and tax may change the total.</p>{busy && <Loading label="Checking store prices..." />}<ErrorAlert message={error} />{message && <p>{message}</p>}<div className="comparison-offers">{products.map((offer,index) => <Card key={offer.product_url + index}><Card.Body>{index === 0 && <Badge bg="light" text="dark">Lowest listed price in these results</Badge>}<div className="d-flex gap-3 mt-2">{offer.thumbnail && <img className="comparison-image" src={offer.thumbnail} alt="" referrerPolicy="no-referrer" />}<div><h3 className="fs-6 item-title" title={offer.name}>{offer.name}</h3><p className="mb-1">{offer.store_name}</p><strong>USD {offer.estimated_price}</strong><a className="d-block" href={offer.shopping_url || offer.product_url} target="_blank" rel="noopener noreferrer">View offer</a>{item.availability && (item.availability.available > 0 || item.availability.held_by_you) && <BuyGiftButton item={{ ...item, shopping_url: offer.shopping_url || offer.product_url, product_url: offer.product_url, store_name: offer.store_name }} alreadyHeld={Boolean(item.availability.held_by_you)} onHeld={onHeld} />}</div></div></Card.Body></Card>)}</div></Modal.Body></Modal></>;
}

function GiftCardContent({ item, onReserveRefresh, viewWish = false }) {
 return <GiftSummaryRow item={item} actions={<>{viewWish&&<Button as={Link} to={'/profiles/'+item.profile_id} variant="link" size="sm">View wish</Button>}<HeartButton item={item}/>{item.availability&&<BuyGiftButton item={item} alreadyHeld={Boolean(item.availability.held_by_you)} onHeld={onReserveRefresh}/>}</>} details={<><GiftIdentity item={item}/><GiftDetails item={item}/><GiftDelivery itemId={item.id}/><ProductActions product={item} listOnly onSaved={onReserveRefresh}/></>}/>;
}

function CoBuyInvite({reservationId, item, onHeld}) {
 const [share,setShare]=useState('50');
 const [activeReservation,setActiveReservation]=useState(reservationId);
 const [open,setOpen]=useState(false),[people,setPeople]=useState([]),[query,setQuery]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const show=async()=>{setOpen(true);setBusy(true);setError('');setNotice('');try{let id=reservationId;if(!id){const result=await api('/items/'+item.id+'/reservations',{method:'POST',body:JSON.stringify({quantity:1,reuse_existing:true})});id=result.reservation.id;setActiveReservation(id);window.dispatchEvent(new Event('shopping-updated'));}setPeople((await api('/reservations/'+id+'/co-buyers/options')).people);await onHeld?.();}catch(err){setError(err.message);}finally{setBusy(false);}};
 const invite=async person=>{setBusy(true);setError('');try{const result=await api('/reservations/'+activeReservation+'/co-buyers',{method:'POST',body:JSON.stringify({user_id:person.id,share_percent:share})});setNotice(result.email_warning || 'Invitation sent.');setPeople(current=>current.filter(p=>p.id!==person.id));window.dispatchEvent(new Event('shopping-updated'));}catch(err){setError(err.message);}finally{setBusy(false);}};
 return <><Button size="sm" variant="outline-success" onClick={show}>Co-buy</Button><Modal show={open} onHide={()=>setOpen(false)} centered><Modal.Header closeButton><Modal.Title>Invite to co-buy / {share}%</Modal.Title></Modal.Header><Modal.Body><ErrorAlert message={error}/>{notice && <Alert variant="info">{notice}</Alert>}<Form.Group controlId="co-buy-share" className="mb-3"><Form.Label>Their contribution (%)</Form.Label><Form.Control type="number" min="0.01" max="100" step="0.01" value={share} onChange={e=>setShare(e.target.value)}/><Form.Text>Coordination only; no payment is collected here.</Form.Text></Form.Group><Form.Control type="search" aria-label="Find a co-buyer" placeholder="Search your family or followed families" value={query} onChange={e=>setQuery(e.target.value)} className="mb-3"/>{busy?<Loading/>:people.filter(p=>[p.name,...(p.families||[])].join(' ').toLowerCase().includes(query.toLowerCase())).map(p=><div key={p.id} className="d-flex justify-content-between align-items-center py-2"><div><strong>{p.name}</strong><small className="d-block text-secondary">{p.families?.join(", ")}</small></div><Button size="sm" disabled={busy || !Number(share) || Number(share)>100} onClick={()=>invite(p)}>Invite / {share}%</Button></div>)}{!busy && !people.length && <p>No eligible people. Co-buyers need access to this wish.</p>}</Modal.Body></Modal></>;
}

function MyShoppingPage({ embedded = false, statusFilter = null, children, showEmpty = true, hideHeading = false }) {
  const [rows, setRows] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [emails, setEmails] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = async () => {
    const [shopping, pending] = await Promise.all([api("/my-shopping"), api("/co-buy-invitations")]);
    setRows(statusFilter ? shopping.reservations.filter(row=>row.status===statusFilter) : shopping.reservations); setInvitations(statusFilter==='purchased' ? [] : pending.invitations);
  };
  useEffect(() => { const refresh = () => load().catch((err) => setError(err.message)); refresh(); window.addEventListener("shopping-updated", refresh); window.addEventListener("focus", refresh); return () => { window.removeEventListener("shopping-updated", refresh); window.removeEventListener("focus", refresh); }; }, []);
  const action = async (path, body) => {
    setBusy(true); setError("");
    try { await api(path, { method: "POST", body: JSON.stringify(body) }); await load(); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const saveForLater = async row => {
    setBusy(true); setError('');
    try {
      await api('/items/' + row.item.id + '/heart', { method:'PUT' });
      await api('/reservations/' + row.id, { method:'PATCH', body:JSON.stringify({status:'cancelled'}) });
      await load();
      window.dispatchEvent(new Event('wishlist-updated'));
      window.dispatchEvent(new Event('shopping-updated'));
    } catch(err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const [purchaseRow,setPurchaseRow]=useState(null),[purchaseSecret,setPurchaseSecret]=useState(true),[deliveryMethod,setDeliveryMethod]=useState('undecided');
  const update = async (row, status, purchase_secret=true, delivery_method='undecided') => {
    setBusy(true); setError("");
    try { await api('/reservations/' + row.id, { method: "PATCH", body: JSON.stringify({ status, ...(status === "purchased" ? {purchase_secret, delivery_method} : {}) }) }); setPurchaseRow(null); await load(); window.dispatchEvent(new Event('wishlist-updated')); window.dispatchEvent(new Event('shopping-updated')); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  return <Container className={embedded ? "p-0 mt-4" : "page-wrap"}>{!hideHeading && <h2>{statusFilter === "purchased" ? "Purchased" : "Buying now"}</h2>}{statusFilter !== "purchased" && !hideHeading && <p className="text-secondary">Reserved for 24 hours. Mark purchased after checkout.</p>}<ErrorAlert message={error} />
    {invitations.map((invite) => <Alert variant="info" key={invite.id}>You?re invited to co-buy <strong>{invite.item_name}</strong> ({invite.share_percent || 50}%). <Button size="sm" disabled={busy} onClick={() => action('/co-buy-invitations/' + invite.id + '/accept', {})}>Accept co-buy invitation</Button> <Button size="sm" variant="outline-secondary" disabled={busy} onClick={() => action('/co-buy-invitations/' + invite.id + '/decline', {})}>Decline</Button></Alert>)}
    {rows.length ? <Row className="g-3 shopping-status-rail">{rows.map((row) => <Col key={row.id} md={6} lg={4}><Card className="gift-card"><Card.Body><Badge bg={row.status === "purchased" ? "success" : "warning"}>{row.status === "reserved" ? <><ShoppingBagIcon filled/> Buying now</> : "Purchased"}</Badge><GiftIdentity item={row.item} /><h3 className="mt-3 item-title" title={row.item.name}>{row.item.name}</h3><p>Quantity: {row.quantity}</p>{row.delivery_method==='in_person'&&<small className="d-block mb-2">Giving in person</small>}{row.delivery_method==='shipping'&&<small className="d-block mb-2">Shipping to them</small>}{row.status === "reserved" && row.expires_at && <p className="small">Hold expires {new Date(row.expires_at).toLocaleString()}</p>}{row.private_note && <p className="private-note">Your note: {row.private_note}</p>}
      <div className="d-flex flex-wrap gap-2">{row.item.product_url && row.status === "reserved" && <a className="small" href={row.item.product_url} target="_blank" rel="noopener noreferrer">Store</a>}{row.status === "reserved" && <GiftDelivery itemId={row.item.id}/>} {row.status === "reserved" && <Button size="sm" variant="success" disabled={busy} onClick={() => {setPurchaseSecret(true);setDeliveryMethod(row.delivery_method || 'undecided');setPurchaseRow(row);}}>Mark purchased</Button>}{row.status === "reserved" && row.is_owner && <Button size="sm" variant="outline-success" disabled={busy} onClick={()=>saveForLater(row)}>Save for later</Button>}{row.is_owner && row.status === "reserved" && <CoBuyInvite reservationId={row.id}/>}{row.status === "reserved" && row.is_owner && <Button className="wish-icon-button buying-remove" size="sm" variant="light" aria-label="Remove from Buying now" title="Remove from Buying now and release hold" disabled={busy} onClick={() => update(row, "cancelled")}><span aria-hidden="true">&times;</span></Button>}</div>
      {row.co_buyers?.length > 0 && <ul className="mt-3">{row.co_buyers.map((person) => <li key={person.email}>{person.email}: {person.share_percent}% / {person.declined ? 'Declined' : person.accepted ? 'Co-buying' : 'Invitation pending'}</li>)}</ul>}
      
    </Card.Body></Card></Col>)}</Row> : showEmpty && <p className="text-secondary">{statusFilter === "purchased" ? "Completed gifts appear here." : "Nothing in progress."}</p>}{children}<PurchaseConfirmation show={Boolean(purchaseRow)} onHide={()=>setPurchaseRow(null)} busy={busy} error={error} deliveryMethod={purchaseRow?.delivery_method} onConfirm={(secret,method)=>update(purchaseRow,"purchased",secret,method)}/></Container>;
}

function NotificationPreferences() {
 const [values,setValues]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{api('/notification-preferences').then(r=>setValues(r.preferences)).catch(e=>setError(e.message));},[]);
 const change=async(key,value)=>{setBusy(true);setError('');try{const r=await api('/notification-preferences',{method:'PATCH',body:JSON.stringify({[key]:value})});setValues(r.preferences);window.dispatchEvent(new Event('notifications-updated'));}catch(e){setError(e.message);}finally{setBusy(false);}};
 return <section className="mb-4"><h2>Notify me about</h2><ErrorAlert message={error}/>{values && [['follow_requests','Follow requests'],['co_buy','Co-buy invitations (in app)'],['co_buy_emails','Co-buy invitation emails'],['games','Gift games (in app)'],['game_emails','Game invitation emails'],['purchases','Purchase updates'],['availability','Gifts available again'],['holds','Expired holds'],['suggestions','Gift suggestions']].map(([key,label])=><div className="notification-preference" key={key}><Form.Check type="switch" id={'notify-'+key} label={label} checked={values[key]} disabled={busy} onChange={e=>change(key,e.target.checked)}/></div>)}</section>;
}

function NotificationsPage({ embedded = false }) {
  const {user,refresh: refreshSession}=useSession();
  const [budgetItems,setBudgetItems]=useState(null);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const load = async () => {
    try {
      const result=await api("/notifications");
      setRows([...(result.notifications || []),...(result.profile_reminders || [])]);
      const [personal, dashboard]=await Promise.all([api('/personal-wishes'),api('/wishlist')]);
      const profiles=(dashboard.family_profiles||[]).filter(p=>p.is_me);
      const lists=await Promise.all(profiles.map(p=>api('/profiles/'+p.id+'/wishlists')));
      setBudgetItems([...(personal.mine||[]).map(w=>w.item),...lists.flatMap(result=>(result.wishlists||[]).flatMap(list=>list.items||[]))]);
      setError("");
    } catch (err) {
      setError(err.message);
    }
  };
  useEffect(() => { const refresh=()=>{if(document.visibilityState!=='hidden')load();};refresh();const timer=setInterval(refresh,15000);window.addEventListener('notifications-updated',refresh);window.addEventListener('wishlist-updated',refresh);window.addEventListener('focus',refresh);return()=>{clearInterval(timer);window.removeEventListener('notifications-updated',refresh);window.removeEventListener('wishlist-updated',refresh);window.removeEventListener('focus',refresh);};}, []);
  const markRead = async (id) => {
    const row=rows.find(item=>item.id===id);if(!row)return;
    try{await readNotification(row);setRows(current=>current.map(item=>item.id===id?{...item,read:true}:item));}catch(err){setError(err.message);}
  };
  return <Container className={embedded ? "p-0" : "page-wrap"}><div className="d-flex justify-content-between align-items-center mb-3"><h1>Notifications</h1><Button as={Link} to="/settings?tab=notifications" variant="outline-secondary" aria-label="Notification settings">?</Button></div><GiftSuggestions/><WishlistBudgetSuggestions items={budgetItems||[]} enabled={budgetItems!==null && user.wishlist_budget_suggestions!==false} onChange={async enabled=>{await api("/wishlist-budget-preferences",{method:"PATCH",body:JSON.stringify({enabled})});await refreshSession();}}/><p className="text-secondary">Purchase updates are private to the household heads. Gift recipients never see who has reserved or purchased their wishes.</p><ErrorAlert message={error} />{rows.filter(row=>!row.suggestion_id).length ? rows.filter(row=>!row.suggestion_id).map((row) => <Card className="settings-card mb-3" key={row.id}><Card.Body className="d-flex justify-content-between align-items-center gap-3"><div><strong>{row.message}</strong><div className="mb-1">{row.invitation_id?<RequestFamilyPreview notification={row}/>:row.household_name}</div><Link onClick={()=>markRead(row.id)} to={row.url || `/profiles/${row.profile_id}${row.wishlist_id ? `?wishlist=${row.wishlist_id}` : ""}`}>{row.profile_completion ? "Complete gift profile" : row.price_request ? "Add wishes in this price range" : row.hold_expired ? "View Saved items" : row.co_buy_invitation_id ? "Review co-buy invitation" : row.game_id ? "Review game invitation" : row.invitation_id ? "Review follow request" : "Open the relevant wish list"}</Link><br /><small className="text-secondary">{row.read?'Read':'Unread'} / {new Date(row.created_at).toLocaleString()}</small></div>{(row.profile_completion||row.price_request) && <Button size="sm" variant="link" onClick={async()=>{try{await dismissNotification(row);setRows(current=>current.filter(item=>item.id!==row.id));}catch(err){setError(err.message);}}}>Ignore</Button>}{!row.read && !row.profile_completion && !row.invitation_id && !row.co_buy_invitation_id && !row.suggestion_id && !row.game_id && <Button size="sm" variant="outline-success" onClick={() => markRead(row.id)}>Mark read</Button>}</Card.Body></Card>) : <div className="empty-state"><span aria-hidden="true">🔔</span><h3>You’re all caught up</h3><p>When a gift is marked purchased, the household parent will see it here.</p></div>}</Container>;
}

function ThemeSettings() {
  const { user, refresh } = useSession();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const change = async (path, method, body) => {
    setBusy(true); setError(''); setNotice('');
    try { await api(path, { method, ...(body ? { body: body instanceof FormData ? body : JSON.stringify(body) } : {}) }); await refresh(); setNotice('Your theme has been updated.'); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  return <section><h2>Make it feel like the occasion</h2><p className="text-secondary">Choose a seasonal palette or artwork from the shared collection. Your theme follows your account while browsing gifts and does not change anyone else's view.</p><ErrorAlert message={error} />{notice && <Alert variant="success">{notice}</Alert>}<div className="theme-options mb-4">{[['classic', 'Classic', 'Warm paper and violet ribbon'], ['christmas', 'Christmas', 'Cranberry, gold, and a little snowfall'], ['halloween', 'Halloween', 'Pumpkin, plum, and a little magic']].map(([key, title, description]) => <button type="button" key={key} className={'theme-option theme-preview-' + key} aria-pressed={(user.theme_key || 'classic') === key} disabled={busy} onClick={() => change('/auth/theme', 'PATCH', { theme_key: key })}><span className="theme-preview-art" aria-hidden="true"></span><strong>{title}</strong><small>{description}</small><span className="small">{(user.theme_key || 'classic') === key ? 'Selected' : 'Use theme'}</span></button>)}</div><SharedThemePicker user={user} refresh={refresh} /></section>;
}

function SessionFamilyInvites() { const { households } = useSession(); return <FamilyInvites households={households} />; }

function AddPetProfile({ householdId, onCreated }) {
  const { crop: cropPhoto, cropper: petPhotoCropper } = usePhotoCrop();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [image, setImage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await api('/households/' + householdId + '/profiles', {
        method: 'POST',
        body: JSON.stringify({ display_name: name.trim(), profile_type: 'pet' }),
      });
      setOpen(false);
      setName('');
      setImage(null);
      await onCreated();
      if (image) {
        const body = new FormData();
        body.append('image', image);
        try {
          await api('/profiles/' + result.profile.id + '/photo', { method: 'POST', body });
          await onCreated();
        } catch (err) {
          setNotice('Pet profile added, but the photo could not be uploaded: ' + err.message);
          return;
        }
      }
      setNotice('Pet profile added.');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };
  return <><div><Button title="Add another furry, feathered, or scaly member to your family." variant="outline-success" onClick={() => { setOpen(true); setError(''); setNotice(''); }}>Add pet</Button>{notice && <small className="d-block mt-1 text-secondary">{notice}</small>}</div><Modal show={open} onHide={() => setOpen(false)} centered><Modal.Header closeButton><Modal.Title>Add a pet to your family</Modal.Title></Modal.Header><Form onSubmit={submit}><Modal.Body><ErrorAlert message={error}/><Form.Group controlId="settings-pet-name" className="mb-3"><Form.Label>Pet's name</Form.Label><Form.Control required maxLength={120} value={name} onChange={event => setName(event.target.value)}/></Form.Group><Form.Group controlId="settings-pet-photo"><Form.Label>Pet photo (optional)</Form.Label><Form.Control type="file" accept="image/jpeg,image/png,image/gif,image/webp,.jpg,.jpeg" onChange={async event => { const picked = await cropPhoto(event.target.files?.[0]); if (picked) setImage(picked); else event.target.value = ''; }}/>{petPhotoCropper}<Form.Text>JPG, JPEG, PNG, GIF, or WebP; up to 5 MB.</Form.Text></Form.Group></Modal.Body><Modal.Footer><Button type="button" variant="outline-secondary" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" disabled={busy || !name.trim()}>{busy ? 'Adding…' : 'Add pet'}</Button></Modal.Footer></Form></Modal></>;
}

function FamilySettingsTools() {
  const [profileParams]=useSearchParams();
  const { user, households, refresh } = useSession();
  const navigate = useNavigate();
  const [homeId, setHomeId] = useState('');
  const [profiles, setProfiles] = useState([]);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const managed = households.filter(home => ['owner', 'admin', 'family_member'].includes(home.role));
  useEffect(() => { if (!homeId && managed.length) setHomeId(String(managed.find(home=>String(home.id)===profileParams.get('letter_family'))?.id || managed[0].id)); }, [households]);
  const load = async () => { if (!homeId) return; try { setProfiles((await api('/households/' + homeId)).profiles); } catch(err) { setError(err.message); } };
  useEffect(() => { load(); const update=()=>load(); window.addEventListener("wishlist-updated",update); return()=>window.removeEventListener("wishlist-updated",update); }, [homeId, households]);
  const edit = async path => { setError(''); setBusy(true); try { await api('/household-session/switch', { method: 'POST', body: JSON.stringify({ profile_id: null }) }); await refresh(); navigate(path); } catch(err) { setError(err.message); } finally { setBusy(false); } };
  const identify = async profile_id => { setBusy(true); setError(''); try { const result = await api('/households/' + homeId + '/identify-me', { method: 'POST', body: JSON.stringify({ profile_id }) }); setMessage(result.message); await refresh(); await load(); } catch(err) { setError(err.message); } finally { setBusy(false); } };
  return <section className="mb-4">
    <h2>Profiles &amp; family</h2>
    <ErrorAlert message={error} />
    {message && <Alert variant="success">{message}</Alert>}
    {managed.length > 0 && <>
      {managed.length > 1 && <Form.Group controlId="settings-household" className="mb-3">
        <Form.Label>Household</Form.Label>
        <Form.Select value={homeId} onChange={event => setHomeId(event.target.value)}>
          {managed.map(home => <option key={home.id} value={home.id}>{home.name}</option>)}
        </Form.Select>
      </Form.Group>}
      <div className="d-flex flex-wrap gap-2 mb-3">
        {['owner', 'admin'].includes(managed.find(home => String(home.id) === homeId)?.role) && <>
          <FamilyEditor households={households} refresh={refresh} BirthdayInput={BirthdayInput} RelationshipSelect={RelationshipSelect} initialHome={homeId} initialPerson="family" label={managed.find(home => String(home.id) === homeId)?.name || "Family"} />
          <FamilyEditor households={households} refresh={refresh} BirthdayInput={BirthdayInput} RelationshipSelect={RelationshipSelect} initialHome={homeId} initialPerson="new" label="Add member" />
          <AddPetProfile householdId={homeId} onCreated={async () => { await refresh(); await load(); }} />
        </>}
      </div>
      {!profiles.some(profile => profile.is_you) && <Alert variant="info">Which person is you? Choose This is me to link your main adult profile.</Alert>}
      {managed.find(home=>String(home.id)===homeId)?.owner_id===user.id && <WishlistLetterManager householdId={homeId} profiles={profiles} resume={profileParams.get("letter_family")===String(homeId)?profileParams.get("letter_art_checkout"):false}/>}
      <div className="member-profile-grid"><FamilyRows profiles={profiles} renderMember={profile => <>
          <FamilyEditor showCompletion member={profile} households={households} refresh={refresh} BirthdayInput={BirthdayInput} RelationshipSelect={RelationshipSelect} initialHome={homeId} initialPerson={String(profile.id)} autoOpen={profileParams.get('profile')===String(profile.id)} label={profile.display_name + (profile.is_you ? ' (you)' : '')} disabled={!profile.can_edit} disabledReason={!profile.can_edit ? (profile.is_adult === false ? 'Only the family creator can edit ' + profile.display_name + "'s profile." : profile.display_name + ' must edit their information.') : ''} />
          <div className="d-flex flex-wrap gap-2 mt-2">
            {!profile.is_you && profile.is_adult !== false && !profile.has_login && profile.profile_type !== 'pet' && managed.find(home => String(home.id) === homeId)?.owner_id === user.id && <Button title="Link this adult profile to your signed-in account." size="sm" variant="outline-secondary" disabled={busy} onClick={() => identify(profile.id)}>This is me</Button>}
          </div>
        </>}/></div>
    </>}

  </section>;
}

function SettingsPage() {
  const { user, households, refresh, setUser, setHouseholds } = useSession();
  const navigate=useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab')==='family'?'account':['account', 'appearance', 'notifications', 'help'].includes(params.get('tab')) ? params.get('tab') : 'account';
  useEffect(()=>{if(tab==='account'){const id=params.get('section')==='parent-pin'?'settings-parent-pin':params.get('section')==='password'?'settings-password':null;if(id){document.getElementById(id)?.scrollIntoView?.({block:'center'});document.getElementById(id)?.focus({preventScroll:true});}}},[tab,params]);
  const [form, setForm] = useState({ name: user.name || '', email: user.email || '', current_password: '', challenge_id: '', code: '' });
  const [passwords, setPasswords] = useState({ old_password: '', new_password: '', confirmation: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const save = async (event) => {
    event.preventDefault(); setBusy(true); setMessage(''); setError('');
    try { await api('/auth/profile', { method: 'PATCH', body: JSON.stringify(form) }); await refresh(); setForm({ ...form, current_password: '', challenge_id: '', code: '' }); setMessage('Your account has been updated.'); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  const changePassword = async (event) => {
    event.preventDefault(); setMessage(''); setError('');
    if (passwords.new_password !== passwords.confirmation) { setError('The new passwords do not match.'); return; }
    setBusy(true);
    try { const result = await api('/auth/password', { method: 'POST', body: JSON.stringify({ old_password: passwords.old_password, new_password: passwords.new_password }) }); setPasswords({ old_password: '', new_password: '', confirmation: '' }); setMessage(result.message); }
    catch (err) { setError(err.message); }
    finally { setBusy(false); }
  };
  return <Container className="page-wrap"><p className="small-label">Your preferences and updates</p><h1 className="page-title">Settings</h1><Form.Group controlId="settings-section" className="settings-section-select mb-4"><Form.Label>Settings section</Form.Label><Form.Select aria-label="Settings section" value={tab} onChange={event => { setParams({ tab: event.target.value }); setMessage(''); setError(''); }}><option value="account">Profiles &amp; account</option><option value="appearance">Appearance</option><option value="notifications">Notifications</option><option value="help">Help &amp; support</option></Form.Select></Form.Group><ErrorAlert message={error} />{message && <Alert variant="success">{message}</Alert>}
    {tab === 'account' && <>{params.get('section')==='parent-pin'?<ParentPinSettings/>:<Button type="button" variant="outline-success" className="mb-3" onClick={()=>setParams({tab:'account',section:'parent-pin'})}>Set / change parent PIN</Button>}<FamilySettingsTools/><WishlistBudgetPreference enabled={user.wishlist_budget_suggestions!==false} onChange={async enabled=>{await api('/wishlist-budget-preferences',{method:'PATCH',body:JSON.stringify({enabled})});await refresh();}}/>{!households.some(h=>['owner','admin','family_member'].includes(h.role)) && <DashboardPage manageOnly/>}<Row className="g-4"><Col lg={6}><Card className="settings-card h-100"><Card.Body><h2>Account details</h2><Form onSubmit={save}><Form.Group controlId="settings-name" className="mb-3"><Form.Label>Name</Form.Label><Form.Control required maxLength={120} autoComplete="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Form.Group><Form.Group controlId="settings-email" className="mb-3"><Form.Label>Main household email address</Form.Label><Form.Control required type="email" autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Form.Group>{form.email.trim().toLowerCase() !== user.email?.toLowerCase() && <Form.Group controlId="settings-current-password" className="mb-3"><Form.Label>Current password to change email</Form.Label><Form.Control required type="password" autoComplete="current-password" value={form.current_password} onChange={(e) => setForm({ ...form, current_password: e.target.value })} /></Form.Group>}{form.challenge_id && <Form.Group controlId="email-change-code" className="mb-3"><Form.Label>Code sent to the current main email</Form.Label><Form.Control inputMode="numeric" autoComplete="one-time-code" required pattern="[0-9]{6}" maxLength={6} value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} /><Button title="Start a new email verification request for this account change." type="button" variant="link" onClick={() => setForm({ ...form, challenge_id: '', code: '' })}>Request a new code</Button></Form.Group>}<Button type="submit" disabled={busy} variant="success">{busy ? 'Saving...' : 'Save account changes'}</Button></Form></Card.Body></Card></Col><Col lg={6}><Card className="settings-card h-100"><Card.Body id="settings-password" tabIndex={-1}><h2>Password &amp; security</h2><Button type="button" variant="outline-success" className="mb-3" aria-expanded={params.get('section')==='password'} aria-controls="settings-password-form" onClick={()=>{setParams(params.get('section')==='password'?{tab:'account'}:{tab:'account',section:'password'});setPasswords({old_password:'',new_password:'',confirmation:''});}}> {params.get('section')==='password'?'Close password form':'Change password'}</Button>{params.get('section')==='password'&&<Form id="settings-password-form" onSubmit={changePassword}>{[['old_password', 'Current password'], ['new_password', 'New password'], ['confirmation', 'Confirm new password']].map(([key, label]) => <Form.Group key={key} controlId={'password-' + key} className="mb-3"><Form.Label>{label}</Form.Label><Form.Control required type="password" autoComplete={key === 'old_password' ? 'current-password' : 'new-password'} minLength={key === 'old_password' ? undefined : 10} value={passwords[key]} onChange={(e) => setPasswords({ ...passwords, [key]: e.target.value })} /></Form.Group>)}<div className="d-flex align-items-center gap-3"><Button title="Replace your current password with the new password entered above." type="submit" variant="outline-success" disabled={busy}>Update password</Button><Link className="small" to="/forgot-password">Forgot password?</Link></div></Form>}</Card.Body></Card></Col></Row></>}{tab === 'appearance' && <><DisplayPreferences/><ThemeSettings /></>}{tab === 'notifications' && <><NotificationPreferences/><WishlistBudgetPreference enabled={user.wishlist_budget_suggestions!==false} onChange={async enabled=>{await api('/wishlist-budget-preferences',{method:'PATCH',body:JSON.stringify({enabled})});await refresh();}}/><Link to="/notifications">View notifications</Link></>}{tab === 'help' && <HelpCenter />}
    <DeleteAccount onDeleted={result=>{clearCsrfToken();setUser(null);setHouseholds([]);navigate('/account-deleted',{replace:true,state:{deletionConfirmed:true,...result}});}}/>
  </Container>;
}

function HelpCenter() {
  const { households } = useSession();
  const [tickets, setTickets] = useState([]);
  const [accessRequests, setAccessRequests] = useState([]);
  const [accessLogs, setAccessLogs] = useState([]);
  const [form, setForm] = useState({ subject: "", description: "", category: "bug" });
  const [ticketReplies, setTicketReplies] = useState({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = async () => {
    try {
      const [ticketResult, requestResults, logResults] = await Promise.all([
        api("/support/tickets"),
        Promise.all(households.filter((household) => ["owner", "admin"].includes(household.role)).map((household) => api(`/support/access-requests?household_id=${household.id}`))),
        Promise.all(households
          .filter((household) => ["owner", "admin"].includes(household.role))
          .map((household) => api(`/households/${household.id}/support-audit-logs`))),
      ]);
      setTickets(ticketResult.tickets);
      setAccessRequests(requestResults.flatMap((result) => result.requests));
      setAccessLogs(logResults.flatMap((result) => result.logs));
    } catch (err) { setError(err.message); }
  };
  useEffect(() => { load(); }, [households]);

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setNotice("");
    try {
      const payload = form.category === "merge"
        ? { ...form, category: "help", subject: "[Merge logins] " + form.subject }
        : form;
      await api("/support/tickets", { method: "POST", body: JSON.stringify(payload) });
      setForm({ subject: "", description: "", category: "bug" });
      setNotice("Your help request was sent.");
      await load();
    } catch (err) { setError(err.message); }
  };

  const decide = async (requestId, decision) => {
    setError("");
    try {
      await api(`/support/access-requests/${requestId}`, { method: "PATCH", body: JSON.stringify({ decision }) });
      await load();
    } catch (err) { setError(err.message); }
  };
  const revoke = async (grantId) => {
    setError("");
    try {
      await api(`/support/grants/${grantId}`, { method: "DELETE" });
      await load();
    } catch (err) { setError(err.message); }
  };
  const reply = async (ticketId) => {
    const message = ticketReplies[ticketId]?.trim();
    if (!message) return;
    setError("");
    try {
      await api(`/support/tickets/${ticketId}/messages`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      setTicketReplies({ ...ticketReplies, [ticketId]: "" });
      await load();
    } catch (err) { setError(err.message); }
  };

  return <section>
    <div className="section-heading"><div><p className="small-label">We’re here to help</p><h2>Help &amp; feedback</h2></div></div>
    <ErrorAlert message={error} />
    {notice && <Alert variant="success">{notice}</Alert>}
    <Row className="g-3">
      <Col lg={6}><Card className="settings-card h-100"><Card.Body><h3>Send a help request or bug report</h3><Form onSubmit={submit}><Form.Group controlId="ticket-category" className="mb-3"><Form.Label>What is this about?</Form.Label><Form.Select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}><option value="bug">Report a problem</option><option value="help">Ask for help</option><option value="feedback">Share feedback</option><option value="merge">Merge our logins into one</option></Form.Select>{form.category === 'merge' && <Form.Text>Tell us which family members should return to your one login. Support will confirm with everyone before merging.</Form.Text>}</Form.Group><Form.Group controlId="ticket-subject" className="mb-3"><Form.Label>Subject</Form.Label><Form.Control required maxLength={180} value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} /></Form.Group><Form.Group controlId="ticket-description" className="mb-3"><Form.Label>Tell us a little more</Form.Label><Form.Control required as="textarea" rows={4} maxLength={10000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></Form.Group><Button title="Send your question or problem to support and follow their replies here." type="submit" variant="success">Send to support</Button></Form></Card.Body></Card></Col>
      <Col lg={6}><Card className="settings-card h-100"><Card.Body><h3>Family data support access</h3><p className="text-secondary">A support agent can only inspect your registry if you explicitly approve their request. Approved access lasts one hour, can be revoked, and is audited.</p>{accessRequests.length ? accessRequests.map((item) => <div className="ticket-row" key={item.id}><strong>{item.support_name} requested help</strong><p className="mb-1">{item.reason}</p><small>{item.status} · {new Date(item.created_at).toLocaleString()}</small>{item.status === "pending" && <div className="d-flex gap-2 mt-2"><Button title="Allow the requested support access to this family for one hour." size="sm" variant="success" onClick={() => decide(item.id, "approve")}>Approve for 1 hour</Button><Button title="Decline this support access request." size="sm" variant="outline-secondary" onClick={() => decide(item.id, "deny")}>Deny</Button></div>}{item.status === "approved" && item.grant_id && <Button title="End the active support permission for this family immediately." className="mt-2" size="sm" variant="outline-danger" onClick={() => revoke(item.grant_id)}>Revoke support access now</Button>}</div>) : <p className="text-secondary mb-0">No support-access requests.</p>}</Card.Body></Card></Col>
    </Row>
    <Card className="settings-card mt-3"><Card.Body><h3>Your support requests</h3>{tickets.length ? tickets.map((ticket) => <div className="ticket-row" key={ticket.id}><div className="d-flex justify-content-between gap-2"><strong>{ticket.subject}</strong><Badge bg={ticket.status === "resolved" ? "success" : "secondary"}>{ticket.status}</Badge></div><p className="text-secondary mt-2 mb-1">{ticket.description}</p>{ticket.messages.slice(1).map((reply) => <p className="support-reply" key={reply.id}><strong>{reply.author_name}:</strong> {reply.message}</p>)}{!["closed", "resolved"].includes(ticket.status) && <div className="d-flex gap-2 mt-2"><Form.Control aria-label={`Reply to ${ticket.subject}`} value={ticketReplies[ticket.id] || ""} onChange={(e) => setTicketReplies({ ...ticketReplies, [ticket.id]: e.target.value })} placeholder="Reply to support" /><Button title="Send your reply to this support conversation." size="sm" variant="outline-success" onClick={() => reply(ticket.id)}>Reply</Button></div>}</div>) : <p className="text-secondary mb-0">No help requests yet.</p>}</Card.Body></Card>
    {accessLogs.length > 0 && <Card className="settings-card mt-3"><Card.Body><h3>Family support access log</h3><p className="text-secondary">A record of support access, approvals, edits, and revocations in households you administer.</p>{accessLogs.map((log, index) => <div className="ticket-row" key={`${log.entity_type}-${log.entity_id}-${log.action}-${index}`}><strong>{log.action.replaceAll(".", " ")}</strong><p className="mb-0">{log.entity_type} #{log.entity_id} · {new Date(log.created_at).toLocaleString()}</p></div>)}</Card.Body></Card>}
  </section>;
}

function SupportPortal() {
  const { crop: cropSetupPhoto, cropper: setupPhotoCropper } = usePhotoCrop();
  const { user } = useSession();
  const [portalParams]=useSearchParams();
  const advertisingRequest=portalParams.get("advertising_request");
  const [requests, setRequests] = useState([]);
  const [grants, setGrants] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [logs, setLogs] = useState([]);
  const [staffInvitations, setStaffInvitations] = useState([]);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const [familySetup, setFamilySetup] = useState({ email: "", householdName: "", profileName: "", birthday: "" });
  const [familySetupPhoto, setFamilySetupPhoto] = useState(null);
  const [familySetupResult, setFamilySetupResult] = useState(null);
  const [familySetupBusy, setFamilySetupBusy] = useState(false);
  const [familySetupNotice, setFamilySetupNotice] = useState("");
  const [householdId, setHouseholdId] = useState("");
  const [reason, setReason] = useState("");
  const [snapshot, setSnapshot] = useState(null);
  const [ticketReplies, setTicketReplies] = useState({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    setError("");
    try {
      const [requestResult, grantResult, ticketResult, logResult, invitationResult] = await Promise.all([
        api("/support/requests"),
        api("/support/grants"),
        api("/support/tickets"),
        api("/support/audit-logs"),
        user.is_superuser ? api("/support/staff-invitations") : Promise.resolve({ invitations: [] }),
      ]);
      setRequests(requestResult.requests);
      setGrants(grantResult.grants);
      setTickets(ticketResult.tickets);
      setLogs(logResult.logs);
      setStaffInvitations(invitationResult.invitations);
    } catch (err) { setError(err.message); }
  };
  useEffect(() => { load(); }, []);

  const requestAccess = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      await api("/support/access-requests", { method: "POST", body: JSON.stringify({ household_id: Number(householdId), reason }) });
      setMessage("Access request sent to the household owner. No family information is available until they approve.");
      setHouseholdId("");
      setReason("");
      await load();
    } catch (err) { setError(err.message); }
  };

  const openSnapshot = async (grant) => {
    setError("");
    try { setSnapshot(await api(`/support/grants/${grant.id}/snapshot`)); await load(); }
    catch (err) { setError(err.message); }
  };

  const editProfile = async (profile) => {
    const displayName = window.prompt("Edit this profile name (the action will be logged):", profile.profile.display_name);
    if (displayName === null || displayName === profile.profile.display_name) return;
    setError("");
    try {
      await api(`/support/grants/${snapshot.grant_id}/profiles/${profile.profile.id}`, {
        method: "PATCH",
        body: JSON.stringify({ display_name: displayName }),
      });
      await openSnapshot({ id: snapshot.grant_id });
    } catch (err) { setError(err.message); }
  };

  const updateTicket = async (ticket, changes) => {
    setError("");
    try {
      await api(`/support/tickets/${ticket.id}`, { method: "PATCH", body: JSON.stringify(changes) });
      await load();
    } catch (err) { setError(err.message); }
  };
  const [section, setSection] = useState(user.is_superuser ? advertisingRequest ? "ads" : "tickets" : "access");
  useEffect(()=>{if(user.is_superuser && advertisingRequest)setSection("ads");},[user.is_superuser,advertisingRequest]);
  const [staffList, setStaffList] = useState([]);
  useEffect(() => {
    if (user.is_superuser) api("/support/staff").then((result) => setStaffList(result.staff)).catch(() => {});
  }, [user.is_superuser]);
  const portalSections = [
    ["tickets", "Tickets"],
    ["access", "Support access, debug & feedback"],
    ["family", "Family & invites"],
    ...(user.is_superuser ? [["commerce", "Affiliate Management"], ["email", "Email control"], ["money", "Money & Stripe"], ["accounts", "User accounts"], ["theme", "Theme"], ["pictures", "Profile pictures & cartoons"], ["ads", "Advertising"], ["assistant", "Assistant chats"]] : []),
  ];
  const [mergeOptions, setMergeOptions] = useState({});
  const loadMergeOptions = async (ticket) => {
    setError("");
    try { setMergeOptions({ ...mergeOptions, [ticket.id]: (await api(`/support/tickets/${ticket.id}/merge-candidates`)).candidates }); }
    catch (err) { setError(err.message); }
  };
  const mergeLogin = async (ticket, candidate) => {
    if (!window.confirm(`Merge ${candidate.profile_name} (${candidate.login_email}) back into ${ticket.user_email}'s login? Both people must have agreed. ${candidate.login_email} will be signed out of this family.`)) return;
    setError("");
    setMessage("");
    try {
      await api(`/support/tickets/${ticket.id}/merge-login`, { method: "POST", body: JSON.stringify({ profile_id: candidate.profile_id, confirmed: true }) });
      setMergeOptions({ ...mergeOptions, [ticket.id]: undefined });
      setMessage(`${candidate.profile_name} was merged into ${ticket.user_email}. Their email info is kept on the profile.`);
      await load();
    } catch (err) { setError(err.message); }
  };
  const replyToTicket = async (ticketId) => {
    const reply = ticketReplies[ticketId]?.trim();
    if (!reply) return;
    setError("");
    try {
      await api(`/support/tickets/${ticketId}/messages`, {
        method: "POST",
        body: JSON.stringify({ message: reply }),
      });
      setTicketReplies({ ...ticketReplies, [ticketId]: "" });
      await load();
    } catch (err) { setError(err.message); }
  };

  const inviteStaff = async (event) => {
    event.preventDefault();
    setError("");
    setMessage("");
    setInviteLink("");
    try {
      const result = await api("/support/staff-invitations", {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail }),
      });
      setInviteLink(`${window.location.origin}/support/accept-invitation/${encodeURIComponent(result.invitation.token)}`);
      setInviteEmail("");
      setMessage(`Private staff invitation created for ${result.invitation.email}. It expires in three days; copy the link below and send it directly to them.`);
      await load();
    } catch (err) { setError(err.message); }
  };

  const createFamilySetup = async (event) => {
    event.preventDefault();
    setError("");
    setFamilySetupNotice("");
    setFamilySetupResult(null);
    setFamilySetupBusy(true);
    const body = new FormData();
    body.append("email", familySetup.email);
    body.append("household_name", familySetup.householdName);
    body.append("profile_name", familySetup.profileName);
    body.append("birthday", familySetup.birthday);
    if (familySetupPhoto) body.append("image", familySetupPhoto);
    try {
      const result = await api("/support/family-setup-invitations", { method: "POST", body });
      setFamilySetupResult(result);
      setFamilySetup({ email: "", householdName: "", profileName: "", birthday: "" });
      setFamilySetupPhoto(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setFamilySetupBusy(false);
    }
  };
  const copyFamilySetupLink = async () => {
    if (!familySetupResult?.email_message?.link) return;
    try {
      await navigator.clipboard.writeText(familySetupResult.email_message.link);
      setFamilySetupNotice("Private family invitation link copied.");
    } catch {
      setFamilySetupNotice("Copy was unavailable. Select the private link and copy it manually.");
    }
  };

  return <Container className="page-wrap support-portal"><p className="small-label">Separate staff account</p><h1 className="page-title">Developer &amp; support portal</h1><p className="text-secondary">Customer registry access is blocked until its owner approves a one-hour support session. Every support view and edit is recorded.</p><ErrorAlert message={error} />{message && <Alert variant="success">{message}</Alert>}<Row className="g-4"><Col md={3}><Form.Select className="d-md-none mb-3" aria-label="Portal section" value={section} onChange={(e) => setSection(e.target.value)}>{portalSections.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</Form.Select><Nav variant="pills" className="flex-column d-none d-md-flex portal-side-menu" aria-label="Portal sections" activeKey={section} onSelect={(key) => key && setSection(key)}>{portalSections.map(([key, label]) => <Nav.Item key={key}><Nav.Link eventKey={key}>{label}</Nav.Link></Nav.Item>)}</Nav></Col><Col md={9}>{section === "money" && user.is_superuser && <MoneyPanel />}{section === "accounts" && user.is_superuser && <AccountsPanel />}{section === "theme" && user.is_superuser && <ThemeStudio />}{section === "pictures" && user.is_superuser && <AvatarStudio />}{section === "ads" && user.is_superuser && <AdvertisingReview />}
    {section === "family" && <>
    <Card className="settings-card mb-4"><Card.Body><h2>Set up a family for someone</h2><p className="text-secondary">Create a family space and its primary adult profile using details the person provided. The invitation is sent to their email; after they sign up or sign in and accept it, they become the family owner. This does not give support staff access to the claimed family.</p><Form onSubmit={createFamilySetup}><Row className="g-3"><Col md={6}><Form.Group controlId="setup-family-email"><Form.Label>Invitee email</Form.Label><Form.Control type="email" autoComplete="email" required value={familySetup.email} onChange={(event) => setFamilySetup({ ...familySetup, email: event.target.value })} /></Form.Group></Col><Col md={6}><Form.Group controlId="setup-family-name"><Form.Label>Family name</Form.Label><Form.Control required maxLength={160} value={familySetup.householdName} onChange={(event) => setFamilySetup({ ...familySetup, householdName: event.target.value })} placeholder="The Rivera family" /></Form.Group></Col><Col md={6}><Form.Group controlId="setup-profile-name"><Form.Label>Primary adult profile name</Form.Label><Form.Control required maxLength={120} value={familySetup.profileName} onChange={(event) => setFamilySetup({ ...familySetup, profileName: event.target.value })} /></Form.Group></Col><Col md={6}><Form.Group controlId="setup-profile-birthday"><Form.Label>Birthday (optional)</Form.Label><Form.Control type="date" value={familySetup.birthday} onChange={(event) => setFamilySetup({ ...familySetup, birthday: event.target.value })} /><Form.Text>Only the month and day are stored.</Form.Text></Form.Group></Col><Col md={8}><Form.Group controlId="setup-profile-photo"><Form.Label>Profile photo (optional)</Form.Label><Form.Control type="file" accept="image/jpeg,image/png,image/gif,image/webp,.jpg,.jpeg" onChange={async (event) => { const picked = await cropSetupPhoto(event.target.files?.[0]); if (picked) setFamilySetupPhoto(picked); else event.target.value = ""; }} />{setupPhotoCropper}<Form.Text>JPG, JPEG, PNG, GIF, or WebP; up to 5 MB.</Form.Text></Form.Group></Col><Col md={4} className="d-flex align-items-end"><Button type="submit" className="w-100" variant="success" disabled={familySetupBusy}>{familySetupBusy ? "Preparing family…" : "Create family and invite"}</Button></Col></Row></Form>{familySetupResult && <Alert variant={familySetupResult.email_message.delivery === "sent" ? "success" : "warning"} className="mt-4"><strong>{familySetupResult.email_message.delivery === "sent" ? "Invitation email sent." : familySetupResult.email_message.delivery === "failed" ? "Email delivery failed." : "Email is not configured."}</strong> {familySetupResult.invitation.email} can claim the family using the email invitation. The private link expires {new Date(familySetupResult.invitation.expires_at).toLocaleString()}.<Form.Group controlId="family-setup-invitation-link" className="mt-3"><Form.Label>Private invitation link</Form.Label><div className="d-flex gap-2"><Form.Control readOnly aria-label="Private family invitation link" value={familySetupResult.email_message.link} onFocus={(event) => event.target.select()} /><Button type="button" variant="outline-success" onClick={copyFamilySetupLink}>Copy link</Button></div></Form.Group>{familySetupResult.email_message.delivery !== "sent" && <Form.Group controlId="family-setup-email-draft" className="mt-3"><Form.Label>Email draft</Form.Label><Form.Control as="textarea" rows={6} readOnly value={familySetupResult.email_message.body} /></Form.Group>}</Alert>}{familySetupNotice && <p className="small text-secondary mt-2" role="status">{familySetupNotice}</p>}</Card.Body></Card>
    {user.is_superuser && <Card className="settings-card mb-4"><Card.Body><h2>Invite support staff</h2><p className="text-secondary">Only the master account can invite staff. Invitations are single-use and expire after three days. There is no public staff registration page.</p><Form onSubmit={inviteStaff}><Row className="g-2 align-items-end"><Col md={8}><Form.Group controlId="staff-invite-email"><Form.Label>Staff email address</Form.Label><Form.Control type="email" required value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} /></Form.Group></Col><Col md={4}><Button className="w-100" type="submit" variant="success">Create private invitation</Button></Col></Row></Form>{inviteLink && <Form.Group controlId="staff-invite-link" className="mt-3"><Form.Label>Private invitation link</Form.Label><Form.Control readOnly aria-label="Private invitation link" value={inviteLink} onFocus={(event) => event.target.select()} /><Form.Text>Copy and send this link directly to the invited person. Anyone with the link can accept it before it expires.</Form.Text></Form.Group>}{staffInvitations.length > 0 && <div className="mt-4"><h3>Pending invitations</h3>{staffInvitations.map((invitation) => <div className="ticket-row" key={invitation.id}><strong>{invitation.email}</strong><p className="mb-0">Expires {new Date(invitation.expires_at).toLocaleString()}</p></div>)}</div>}</Card.Body></Card>}
    </>}
    {section === "access" && <>
    <Card className="settings-card mb-4"><Card.Body><h2>Request customer access</h2><Form onSubmit={requestAccess}><Row className="g-2"><Col md={3}><Form.Group controlId="support-household-id"><Form.Label>Household ID</Form.Label><Form.Control type="number" min="1" required value={householdId} onChange={(e) => setHouseholdId(e.target.value)} /></Form.Group></Col><Col md={6}><Form.Group controlId="support-reason"><Form.Label>Support reason</Form.Label><Form.Control required maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Describe the issue you need to investigate" /></Form.Group></Col><Col md={3} className="d-flex align-items-end"><Button className="w-100" type="submit" variant="success">Ask owner to approve</Button></Col></Row></Form></Card.Body></Card>
    <Row className="g-3">
      <Col lg={6}><Card className="settings-card h-100"><Card.Body><h2>Customer-approved access</h2>{grants.length ? grants.map((grant) => <div className="ticket-row" key={grant.id}><div className="d-flex justify-content-between"><strong>{grant.household_name}</strong><small>Until {new Date(grant.expires_at).toLocaleTimeString()}</small></div><p className="text-secondary">{grant.reason}</p><Button size="sm" variant="outline-success" onClick={() => openSnapshot(grant)}>Open audited support view</Button></div>) : <p className="text-secondary mb-0">No active approved support sessions.</p>}</Card.Body></Card></Col>
      <Col lg={6}><Card className="settings-card h-100"><Card.Body><h2>Support requests</h2>{requests.length ? requests.map((item) => <div key={item.id} className="ticket-row"><strong>{item.household_name} · {item.status}</strong><p className="mb-0">{item.reason}</p><small>{new Date(item.created_at).toLocaleString()}</small></div>) : <p className="text-secondary mb-0">No support access requests.</p>}</Card.Body></Card></Col>
    </Row>
    {snapshot && <Card className="settings-card mt-4"><Card.Body><div className="d-flex justify-content-between"><div><p className="small-label">Audited session · expires {new Date(snapshot.expires_at).toLocaleTimeString()}</p><h2>{snapshot.household.name}</h2></div><Button variant="outline-secondary" onClick={() => setSnapshot(null)}>Close view</Button></div><Alert variant="warning">This view is logged. Only use customer data for the approved support reason: {snapshot.reason}</Alert><HoldManager path={"/support/grants/" + snapshot.grant_id + "/holds"} />{snapshot.profiles.map((entry) => <div className="ticket-row" key={entry.profile.id}><div className="d-flex justify-content-between align-items-center"><strong>{entry.profile.display_name}</strong><Button size="sm" variant="outline-success" onClick={() => editProfile(entry)}>Edit name (logged)</Button></div><p className="text-secondary mt-2">{entry.items.length} gift items. Reservation details are excluded from this support view.</p>{entry.items.map((item) => <p className="mb-1 item-title" key={item.id} title={item.name}>{item.name}</p>)}</div>)}</Card.Body></Card>}
    </>}
    {section === "tickets" && <>
    <Card className="settings-card mt-4"><Card.Body><h2>{user.is_superuser ? "All support tickets" : "Your assigned tickets"}</h2>{tickets.length ? tickets.map((ticket) => <div className="ticket-row" key={ticket.id}><div className="d-flex justify-content-between gap-2"><strong>{ticket.subject}</strong><Form.Select aria-label={`Status for ${ticket.subject}`} size="sm" className="w-auto" value={ticket.status} onChange={(e) => updateTicket(ticket, { status: e.target.value })}><option value="open">Open</option><option value="in_progress">In progress</option><option value="resolved">Resolved</option><option value="closed">Closed</option></Form.Select></div><p className="mb-1">{ticket.description}</p><small>{ticket.user_name} &lt;{ticket.user_email}&gt; · {ticket.category} · opened {new Date(ticket.created_at).toLocaleString()} · updated {new Date(ticket.updated_at).toLocaleString()}</small><div className="mt-1">{user.is_superuser ? <Form.Select aria-label={`Assign ${ticket.subject}`} size="sm" className="w-auto d-inline-block" value={ticket.assigned_to?.id ?? ""} onChange={(e) => updateTicket(ticket, { assigned_to_id: e.target.value ? Number(e.target.value) : null })}><option value="">Unassigned</option>{staffList.map((member) => <option key={member.id} value={member.id}>{member.name}</option>)}</Form.Select> : <small>Assigned to you</small>}{ticket.assigned_to && !user.is_superuser ? null : ticket.assigned_to && <small className="ms-2">Working: {ticket.assigned_to.name}</small>}</div><div className="mt-2"><Button size="sm" variant="outline-success" onClick={() => loadMergeOptions(ticket)}>Find logins to merge</Button>{mergeOptions[ticket.id] && (mergeOptions[ticket.id].length ? mergeOptions[ticket.id].map(candidate => <div className="d-flex flex-wrap align-items-center gap-2 mt-2" key={candidate.profile_id}><span><strong>{candidate.profile_name}</strong> · {candidate.household_name} · login {candidate.login_email}</span><Button size="sm" variant="success" onClick={() => mergeLogin(ticket, candidate)}>Merge into {ticket.user_email}</Button></div>) : <p className="small text-secondary mt-2 mb-0">No separate adult logins to merge for this requester.</p>)}</div>{ticket.messages.map((reply) => <p className="support-reply" key={reply.id}><strong>{reply.author_name}:</strong> {reply.message}</p>)}<div className="d-flex gap-2 mt-2"><Form.Control aria-label={`Reply to ${ticket.subject}`} value={ticketReplies[ticket.id] || ""} onChange={(e) => setTicketReplies({ ...ticketReplies, [ticket.id]: e.target.value })} placeholder="Write a support reply" /><Button size="sm" variant="outline-success" onClick={() => replyToTicket(ticket.id)}>Reply</Button></div></div>) : <p className="text-secondary mb-0">No support tickets.</p>}</Card.Body></Card>
    </>}
    {section === "commerce" && user.is_superuser && <CommerceAdmin/>}{section === "email" && user.is_superuser && <EmailControl/>}{section === "assistant" && user.is_superuser && <HelpChatLogs />}
    {section === "access" && <>
    <Card className="settings-card mt-4"><Card.Body><h2>Recent audit log</h2>{logs.length ? <div className="table-responsive"><table className="table align-middle"><thead><tr><th>When</th><th>Action</th><th>Household</th><th>Details</th></tr></thead><tbody>{logs.map((log) => <tr key={log.id}><td>{new Date(log.created_at).toLocaleString()}</td><td>{log.action}</td><td>{log.household_id ?? "—"}</td><td>{log.entity_type} #{log.entity_id}</td></tr>)}</tbody></table></div> : <p className="text-secondary mb-0">No logged support actions yet.</p>}</Card.Body></Card>
    </>}
    </Col></Row>
  </Container>;
}

function NotFoundPage() {
  return <Container className="empty-state not-found"><span aria-hidden="true">🌿</span><h1>We couldn’t find that page</h1><p>Let’s get you back to your family space.</p><Button as={Link} to="/" variant="success">Back home</Button></Container>;
}

export default App;
