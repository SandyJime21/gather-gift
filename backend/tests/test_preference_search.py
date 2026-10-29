import json
from urllib.parse import urlsplit,parse_qs
from backend.tests.test_reservation_privacy import register
from backend.tests.test_child_access import child_setup
from backend.app.profile_preferences import completion
from backend.tests.test_profile_preferences import profile


def test_search_only_sends_typed_words_and_filters_invalid_results(app,monkeypatch):
    client=app.test_client();register(client,'Private account name','private-name@example.com')
    requests=[]
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,*args):return json.dumps(['Target',['Target','Target','Unsafe'],[],['https://en.wikipedia.org/wiki/Target','https://en.wikipedia.org/wiki/Target','javascript:alert(1)']]).encode()
    def lookup(request,**kwargs):requests.append(request);return Response()
    monkeypatch.setattr('backend.app.preference_search.urlopen',lookup)
    result=client.get('/api/preference-search?field=favorite_stores&q=Target')
    assert result.status_code==200
    assert result.json['results']==[dict(label='Target',url='https://en.wikipedia.org/wiki/Target')]
    query=parse_qs(urlsplit(requests[0].full_url).query)
    assert query['search']==['Target']
    assert 'Private account name' not in requests[0].full_url
    assert 'private-name@example.com' not in requests[0].full_url
    assert client.get('/api/preference-search?field=allergies&q=Peanuts').status_code==400
    assert client.get('/api/preference-search?field=favorite_stores&q=x').status_code==400


def test_search_failure_does_not_prevent_manual_completion(app,monkeypatch):
    client=app.test_client();register(client,'Parent','search-parent@example.com')
    def fail(*args,**kwargs):raise OSError('Offline')
    monkeypatch.setattr('backend.app.preference_search.urlopen',fail)
    result=client.get('/api/preference-search?field=favorite_snacks&q=Cookies')
    assert result.status_code==503 and 'still counts' in result.json['error']
    filled=profile(photo_path='/photo.jpg',birthday='2000-01-01',allergies='None known',clothing_sizes={'shirt':'M'},shoe_sizes={'US':'7'},favorite_colors=['Pink'],favorite_brands=['Local brand'],favorite_stores=['Corner shop'],favorite_snacks=['Cookies'],gift_preferences='Books')
    assert completion(filled)['percent']==100


def test_children_cannot_use_the_parent_preference_search(app):
    _,child,*_=child_setup(app)
    assert child.get('/api/preference-search?field=interests&q=Minnie').status_code==403
