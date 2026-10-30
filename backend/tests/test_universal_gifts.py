import pytest
from backend.tests.test_reservation_privacy import register,mutate


def test_unknown_store_saves_without_fetching_or_affiliate_approval(app,monkeypatch):
    client=app.test_client();register(client,'Parent','universal-parent@example.com')
    monkeypatch.setattr('backend.app.universal_gifts.preview_link',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Unknown stores must not be scraped')))
    link='https://independent-shop.example/handmade-cup?ref=my-original-link'
    preview=mutate(client,'POST','/api/commerce/preview',{'url':link})
    assert preview.status_code==200 and preview.json['preview']['metadata_unavailable']
    payload={'name':'Handmade cup','product_url':link,'estimated_price':'25.50','currency':'CAD','quantity':3,'priority':4,'notes':'Blue glaze','avoid_duplicate':True,'visibility':'private','viewer_ids':[]}
    saved=mutate(client,'POST','/api/personal-wishes',payload)
    assert saved.status_code==201,saved.json
    item=saved.json['wish']['item']
    assert item['original_product_url']==link and item['currency']=='CAD' and item['quantity']==3 and item['notes']=='Blue glaze'
    duplicate=mutate(client,'POST','/api/personal-wishes',{**payload,'name':'Do not overwrite existing gift'})
    assert duplicate.status_code==200 and duplicate.json['already_saved']
    assert duplicate.json['wish']['item']['name']=='Handmade cup'
    assert len(client.get('/api/personal-wishes').json['mine'])==1


def test_same_link_can_be_added_to_different_child_registries_but_not_by_stranger(app):
    owner,other=app.test_client(),app.test_client();register(owner,'Owner','any-store-owner@example.com');register(other,'Other','any-store-other@example.com')
    home=mutate(owner,'POST','/api/households',{'name':'Family','profiles':[{'display_name':'Kid','relationship':'child'}]}).json['household']
    profile=owner.get(f"/api/households/{home['id']}").json['profiles'][0]
    first=mutate(owner,'POST',f"/api/profiles/{profile['id']}/wishlists",{'title':'Birthday'}).json['wishlist']
    second=mutate(owner,'POST',f"/api/profiles/{profile['id']}/wishlists",{'title':'Christmas'}).json['wishlist']
    payload={'name':'Toy','product_url':'https://www.target.com/p/toy/-/A-123','avoid_duplicate':True,'quantity':2}
    for wishlist in (first,second):
        path=f"/api/wishlists/{wishlist['id']}/items"
        assert mutate(owner,'POST',path,payload).status_code==201
        assert mutate(owner,'POST',path,payload).json['already_saved']
        assert len(owner.get(path).json['items'])==1
        assert mutate(other,'POST',path,payload).status_code==404


@pytest.mark.parametrize('link',['javascript:alert(1)','https://127.0.0.1/','https://localhost/','https://shop.local/a','https://user:secret@shop.example/a','https://shop.example:8443/a','https://shop.example/\nsecret'])
def test_universal_preview_rejects_unsafe_links_without_fetching(app,link):
    client=app.test_client();register(client,'Parent','unsafe-universal@example.com')
    assert mutate(client,'POST','/api/commerce/preview',{'url':link}).status_code==400
    assert mutate(client,'POST','/api/personal-wishes',{'name':'Bad link','product_url':link,'avoid_duplicate':True}).status_code==400


def test_metadata_only_uses_explicitly_permitted_domains(app,monkeypatch):
    client=app.test_client();register(client,'Parent','permitted-meta@example.com');app.config['PERMITTED_METADATA_DOMAINS']='shop.example'
    calls=[]
    def permitted(url,allowed_hosts):
        calls.append((url,allowed_hosts));return {'title':'Permitted product','image_url':None,'store_name':'Shop'}
    monkeypatch.setattr('backend.app.universal_gifts.preview_link',permitted)
    assert mutate(client,'POST','/api/commerce/preview',{'url':'https://shop.example/product'}).json['preview']['title']=='Permitted product'
    assert calls==[('https://shop.example/product',{'shop.example'})]
