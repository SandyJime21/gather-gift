"""Capability-aware affiliate adapters. No approval is inferred from credentials."""
import json
import ssl
from urllib.parse import urlencode,quote,urlsplit,parse_qsl,unquote
from urllib.request import urlopen
import certifi
from flask import current_app
from .commerce_urls import validated_product_url

PROVIDERS={
    'sovrn':{'name':'Sovrn Commerce','implementation':'link_check','env':['SOVRN_COMMERCE_API_KEY'],'docs':'https://developer.sovrn.com/reference/link','documented':['merchant_eligibility','affiliate_links','price_comparison','reporting']},
    'awin':{'name':'Awin','implementation':'approved_link_templates','env':['AWIN_API_TOKEN','AWIN_PUBLISHER_ID'],'docs':'https://help.awin.com/apidocs/for-publishers','documented':['affiliate_links','product_feeds','reporting']},
    'impact':{'name':'Impact.com','implementation':'approved_link_templates','env':['IMPACT_ACCOUNT_SID','IMPACT_AUTH_TOKEN'],'docs':'https://help.impact.com/partner/what-would-you-like-to-learn-about/platform-features/tracking/tracking-links/create-and-manage-links/create-tracking-links','documented':['affiliate_links','product_catalogs','reporting']},
    'cj':{'name':'CJ Affiliate','implementation':'approved_link_templates','env':['CJ_API_TOKEN','CJ_COMPANY_ID','CJ_WEBSITE_ID'],'docs':'https://docs.cj.com/docs/productfeed-api-search','documented':['affiliate_links','product_search','reporting']},
    'rakuten':{'name':'Rakuten Advertising','implementation':'approved_link_templates','env':['RAKUTEN_API_TOKEN'],'docs':'https://developers.rakutenadvertising.com/guides/deep_link','documented':['affiliate_links','product_search','reporting']},
    'skimlinks':{'name':'Skimlinks','implementation':'approved_link_templates','env':['SKIMLINKS_CLIENT_ID','SKIMLINKS_CLIENT_SECRET'],'docs':'https://developers.skimlinks.com/','documented':['merchant_information','affiliate_links','reporting']},
}
TRACKING_HOSTS=('sovrn.co','viglink.com','awin1.com','pxf.io','sjv.io','evyy.net','anrdoezrs.net','jdoqocy.com','tkqlhce.com','dpbolvw.net','kqzyfj.com','linksynergy.com','skimresources.com','skimlinks.com','amzn.to','link.amazon')


def already_affiliated(url):
    parts=urlsplit(url);host=(parts.hostname or '').lower()
    return any(host==domain or host.endswith('.'+domain) for domain in TRACKING_HOSTS) or any(key.lower() in {'tag','campid','afftrack','affid','affiliate_id','affiliate','partner','aff','irclickid','irgwc','awc','cjevent','ranmid','ransiteid','linkcode','affsrc'} for key,_ in parse_qsl(parts.query))


def matches(host,domains):
    return any(host==domain or host.endswith('.'+domain) for domain in domains)


class AffiliateAdapter:
    capabilities={'checkMerchantEligibility':True,'searchProducts':False,'getProductDetails':False,'generateAffiliateLink':True,'getMerchantInformation':True,'getAvailableReporting':False}
    def __init__(self,key,setting):self.key=key;self.setting=setting
    def configured(self):return bool((self.setting.merchant_rules or {}).get('links'))
    def eligible_host(self,url):
        _,host=validated_product_url(url);rules=self.setting.merchant_rules or {}
        return bool(self.setting.enabled and self.setting.approved and matches(host,rules.get('approved_merchants',[])) and not matches(host,rules.get('excluded_merchants',[])))
    def checkMerchantEligibility(self,url):return {'supported':True,'eligible':self.eligible_host(url)}
    def searchProducts(self,*args,**kwargs):return {'supported':False,'reason':'Product search/feed ingestion is not implemented for this adapter.'}
    def getProductDetails(self,*args,**kwargs):return {'supported':False,'reason':'Product details are not implemented for this adapter.'}
    def getMerchantInformation(self):return {'supported':True,'approved_merchants':(self.setting.merchant_rules or {}).get('approved_merchants',[])}
    def getAvailableReporting(self):return {'supported':False,'conversions':None,'commissions':None,'reason':'No authenticated reporting adapter is connected.'}
    def generateAffiliateLink(self,url):
        if not self.eligible_host(url):return None
        _,host=validated_product_url(url)
        for domain,template in (self.setting.merchant_rules or {}).get('links',{}).items():
            if matches(host,[domain]):
                target=template.replace('{url}',quote(url,safe=''))
                validated_product_url(target)
                return target
        return None


class SovrnAdapter(AffiliateAdapter):
    def configured(self):return bool(current_app.config.get('SOVRN_COMMERCE_API_KEY','').strip())
    def checkMerchantEligibility(self,url):
        if not self.eligible_host(url) or not self.configured():return {'supported':True,'eligible':False,'url':None}
        key=current_app.config['SOVRN_COMMERCE_API_KEY'].strip()
        params=urlencode({'out':url,'key':key,'format':'json','optimize':'false'})
        with urlopen('https://api.viglink.com/api/link/?'+params,timeout=5,context=ssl.create_default_context(cafile=certifi.where())) as response:
            raw=response.read(200001)
        if len(raw)>200000:raise ValueError('Invalid provider response.')
        data=json.loads(raw)
        if not isinstance(data,dict) or data.get('affiliatable') is not True:return {'supported':True,'eligible':False,'url':None}
        target=data.get('optimized')
        _,host=validated_product_url(target)
        if not matches(host,['sovrn.co','viglink.com']):raise ValueError('Unrecognized Sovrn redirect destination.')
        # Never expose API credentials, even if a provider includes them in its
        # suggested redirect. Such responses fall back to the original URL.
        if key in unquote(target):raise ValueError('Provider requires an opaque, credential-free tracking URL.')
        return {'supported':True,'eligible':True,'url':target}
    def generateAffiliateLink(self,url):return self.checkMerchantEligibility(url).get('url')


def adapter(key,setting):return SovrnAdapter(key,setting) if key=='sovrn' else AffiliateAdapter(key,setting)
