"""Capture primary bibliography metadata for the conference manuscript."""
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'/'paper'/'sources'
ACL_IDS=['P97-1023','W02-1011','P02-1053','P04-1035','H05-1044','J11-2001','J11-1002',
         'L06-1225','L10-1531','S14-2004','S15-2082','S16-1002','D13-1170','C16-1311',
         'D16-1058','D16-1059','P18-1234','D19-1464','N19-1035','N19-1242','S13-2053',
         'S16-1004','D17-1058','D14-1181','W03-1014']


class Metadata(HTMLParser):
    def __init__(self):super().__init__();self.values={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='meta' and 'content' in attrs:
            key=attrs.get('name',attrs.get('property',''))
            self.values.setdefault(key,[]).append(attrs['content'])


def fetch(identifier):
    url=f'https://aclanthology.org/{identifier}/'
    data=urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Team17 academic project bibliography verification'}),timeout=35).read().decode('utf-8')
    p=Metadata();p.feed(data)
    abstract=re.search(r'<div[^>]*class="[^"]*acl-abstract[^"]*"[^>]*>(.*?)</div>',data,re.S)
    clean=lambda s:unescape(re.sub('<[^>]+>',' ',s))
    bib=re.search(r'<pre[^>]*id=["\x27]?citeBibtex["\x27]?[^>]*>(.*?)</pre>',data,re.S)
    record={'id':identifier,'url':url,'metadata':p.values,
            'abstract':re.sub(r'\s+',' ',clean(abstract.group(1))).strip() if abstract else '',
            'bibtex':clean(bib.group(1)).strip() if bib else ''}
    pdf_text = ''
    if not record['abstract']:
        pdf=OUT/f'{identifier}.pdf'
        if not pdf.exists():pdf.write_bytes(urllib.request.urlopen(f'https://aclanthology.org/{identifier}.pdf',timeout=35).read())
        import pdfplumber
        with pdfplumber.open(pdf) as document:
            pdf_text='\n'.join(page.extract_text() or '' for page in document.pages[:2])
        # Private reading notes stay ignored; publish citation metadata only.
        (OUT/f'{identifier}.notes.txt').write_text(pdf_text,encoding='utf-8')
    (OUT/f'{identifier}.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'id':identifier,'abstract_chars':len(record['abstract']),'pdf_text_chars':len(pdf_text)}


if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        for row in pool.map(fetch,ACL_IDS):print(json.dumps(row,ensure_ascii=True))
