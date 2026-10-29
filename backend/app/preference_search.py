"""Optional public-name search; manual favorites never need verification."""
import json
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,urlopen
from flask import jsonify,request
from .api import api,authenticated,error
from .extensions import limiter

FIELDS={'favorite_stores','favorite_brands','favorite_snacks','favorite_colors','favorite_characters','interests','hobbies'}


@api.get('/preference-search')
@authenticated
@limiter.limit('30 per hour',key_func=lambda:str(request.current_user.id))
def search_preferences():
    field=request.args.get('field','')
    query=request.args.get('q','').strip()
    if field not in FIELDS or not 2<=len(query)<=120:
        return error('Choose a favorites field and enter 2 to 120 characters.',400)
    params=urlencode(dict(action='opensearch',search=query,limit=8,namespace=0,format='json',redirects='resolve'))
    req=Request('https://en.wikipedia.org/w/api.php?'+params,headers={'User-Agent':'GatherAndGift/1.0 (optional favorites search)','Accept':'application/json'})
    try:
        with urlopen(req,timeout=8) as response:
            data=json.loads(response.read(500001))
        if not isinstance(data,list) or len(data)<4 or not isinstance(data[1],list) or not isinstance(data[3],list):
            raise ValueError()
    except (OSError,ValueError):
        return error('Online search is unavailable. Type your favorite manually; it still counts toward completion.',503)
    rows=[];seen=set()
    for title,url in zip(data[1],data[3]):
        if not isinstance(title,str) or not 1<=len(title.strip())<=120 or not isinstance(url,str):
            continue
        try:
            parsed=urlsplit(url)
            if parsed.scheme!='https' or parsed.hostname!='en.wikipedia.org':continue
        except ValueError:
            continue
        title=title.strip()
        if title.casefold() not in seen:
            rows.append(dict(label=title,url=url));seen.add(title.casefold())
    return jsonify(results=rows,source='Wikipedia')
