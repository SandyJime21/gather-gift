"""Existing authorized search services behind a common, read-only interface."""
from flask import current_app
from .extensions import db
from .models import CommerceIntegration


class SearchProvider:
    capabilities={'checkMerchantEligibility':False,'searchProducts':True,'getProductDetails':False,'generateAffiliateLink':False,'getMerchantInformation':True,'getAvailableReporting':False}
    def enabled(self):
        from .commerce import schema_ready
        setting=db.session.get(CommerceIntegration,'search_'+self.key) if schema_ready() else None
        return setting.enabled if setting else True
    def getProductDetails(self,*args):return {'supported':False,'reason':'No product detail adapter is connected.'}
    def getAvailableReporting(self):return {'supported':False,'conversions':None,'commissions':None}
    def getMerchantInformation(self):return {'supported':True,'name':self.name}


class EbaySearchProvider(SearchProvider):
    key='ebay';name='eBay Browse API';child_safe=False
    def configured(self):
        from .ebay_search import configured
        return configured()
    def searchProducts(self,query,child_safe=False):
        from .ebay_search import search_ebay
        return search_ebay(query)


class SerpSearchProvider(SearchProvider):
    key='serpapi';name='SerpApi Shopping';child_safe=True
    def configured(self):return bool(current_app.config.get('SERPAPI_API_KEY'))
    def searchProducts(self,query,child_safe=False):
        from .product_search import search_serpapi
        return search_serpapi(query,child_safe=child_safe)


def search_providers():return [EbaySearchProvider(),SerpSearchProvider()]


def search_status():
    return [{'id':'search_'+p.key,'name':p.name,'implementation':'product_search','enabled':p.enabled(),'approved':None,'configured':p.configured(),
             'required_environment':['EBAY_CLIENT_ID','EBAY_CLIENT_SECRET'] if p.key=='ebay' else ['SERPAPI_API_KEY'],
             'status':'disabled' if not p.enabled() else 'ready' if p.configured() else 'credentials_required',
             'capabilities':p.capabilities,'documented_capabilities':['product_search'],'merchant_rules':{},'last_error':None,'reporting':p.getAvailableReporting(),
             'docs':'https://developer.ebay.com/develop/api/buy/browse_api' if p.key=='ebay' else 'https://serpapi.com/google-shopping-api'} for p in search_providers()]
