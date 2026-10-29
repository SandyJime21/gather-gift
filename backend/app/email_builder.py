"""Editable email blocks with a protected, live message slot."""
import re
from html import escape
from html.parser import HTMLParser
from flask import g
from .extensions import db
from .models import EmailTemplateDesign

DEFAULT_BLOCKS = [dict(type='message', html='', font='Arial', color='#302b43', background='#ffffff', size=16)]


class SafeHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag not in {'p','br','strong','em','b','i','u','h1','h2','h3','div','span','ul','ol','li','a','hr','table','tr','td'}:
            return
        safe = []
        for name, value in attrs:
            if name == 'href' and tag == 'a' and re.match(r'^https?://', value or '', re.I):
                safe.append('href="'+escape(value, quote=True)+'"')
            if name == 'style' and value and re.fullmatch(r'[a-zA-Z0-9#:,;. %()\-]+', value) and not re.search(r'url|expression|position|behavior', value, re.I):
                safe.append('style="'+escape(value, quote=True)+'"')
        self.output.append('<'+tag+(' '+' '.join(safe) if safe else '')+'>')

    def handle_endtag(self, tag):
        if tag in {'p','strong','em','b','i','u','h1','h2','h3','div','span','ul','ol','li','a','table','tr','td'}:
            self.output.append('</'+tag+'>')

    def handle_data(self, data):
        self.output.append(escape(data))


def validate_blocks(blocks):
    if not isinstance(blocks, list) or not 1 <= len(blocks) <= 30:
        raise ValueError('Use between 1 and 30 blocks.')
    cleaned = []
    for block in blocks:
        if not isinstance(block, dict) or block.get('type') not in ('html','message'):
            raise ValueError('Choose an HTML or live message block.')
        font = block.get('font', 'Arial')
        if font not in ('Arial','Georgia','Verdana','Tahoma','Courier New'):
            raise ValueError('Choose a supported font.')
        color, background, size = block.get('color','#302b43'), block.get('background','#ffffff'), block.get('size',16)
        if not all(isinstance(v,str) and re.fullmatch(r'#[0-9a-fA-F]{6}', v) for v in (color,background)) or type(size) is not int or not 10 <= size <= 48:
            raise ValueError('Use valid colors and a font size between 10 and 48.')
        html = block.get('html','')
        if not isinstance(html,str) or len(html)>20000:
            raise ValueError('Each HTML block must be under 20,000 characters.')
        parser = SafeHTML();parser.feed(html)
        cleaned.append(dict(type=block['type'],html=''.join(parser.output) if block['type']=='html' else '',font=font,color=color,background=background,size=size))
    if sum(b['type']=='message' for b in cleaned)!=1:
        raise ValueError('Keep exactly one live message block for current codes, links and account details.')
    return cleaned


def render_blocks(blocks, content):
    parts = []
    # Strip the original document wrapper so block typography can be inherited.
    content = re.sub(r'</?(?:html|body)\b[^>]*>', '', content, flags=re.I)
    for b in blocks:
        inner = content if b['type']=='message' else b['html']
        parts.append(f'<div style="font-family:{b["font"]},sans-serif;font-size:{b["size"]}px;color:{b["color"]};background:{b["background"]};padding:16px">{inner}</div>')
    return '<html><body><div style="max-width:600px;margin:24px auto">'+''.join(parts)+'</div></body></html>'


def apply_design(message):
    if getattr(g,'email_design_disabled',False):
        return
    if getattr(message,'_email_design_applied',False):
        return
    key = getattr(message,'_template_id',None)
    row = db.session.get(EmailTemplateDesign,key) if key else None
    if row:
        plain = message.get_body(preferencelist=('plain',))
        html = message.get_body(preferencelist=('html',))
        original = html.get_content() if html else '<div style="white-space:pre-wrap">'+escape(plain.get_content() if plain else '')+'</div>'
        rendered = render_blocks(row.blocks,original)
        if html:
            html.set_content(rendered,subtype='html')
        else:
            # Convert just the text part; mixed attachments remain untouched.
            plain.add_alternative(rendered,subtype='html')
    message._email_design_applied = True
