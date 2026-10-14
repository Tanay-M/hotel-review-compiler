"""Build the curated hotel lexicon from the checksum-pinned SentiWordNet corpus.

No download/model dependency at runtime. Sense selection follows the WordNet
lemma rank unless an explicit hotel-context sense is listed in the catalog.
Source polarity is never used to choose a sense. Original corpus rows stay intact.
"""
import csv
import hashlib
import json
from pathlib import Path
import zipfile

from prepare_sentiwordnet import SOURCE_SHA256, prepare

ROOT = Path(__file__).resolve().parents[1]


def expand():
    archive = ROOT / 'data/vendor/sentiwordnet.zip'
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError('Unverified source corpus.')
    catalog = json.loads((ROOT/'scripts/hotel_vocabulary_catalog.json').read_text())
    domain_path = ROOT/'hotel_compiler/resources/domain.json'
    vocabulary = json.loads(domain_path.read_text())
    for term, calibration in catalog.get('legacy_calibrations',{}).items():
        vocabulary['opinions'][term].update(calibration)
    categories = vocabulary['categories']
    lookup, senses = {}, {}
    with zipfile.ZipFile(archive) as z:
        for line in z.read('sentiwordnet/SentiWordNet_3.0.0.txt').decode().splitlines():
            if not line or line.startswith('#'):
                continue
            pos, offset, p, n, terms, gloss = line.split('\t',5)
            if pos not in {'a','n','v','r'} or not p or not n:
                continue
            key = f'{pos}:{offset}'
            senses[key] = (float(p),float(n),gloss)
            if pos == 'a':
                for entry in terms.split():
                    term, rank = entry.rsplit('#',1)
                    lookup.setdefault(term,[]).append((int(rank),key))
    restrictions = {
        'Cleanliness': ['Room','Food','Cleanliness','Facilities'],
        'Comfort': ['Room','Facilities'], 'Noise':['Room','Facilities'],
        'Service': ['Staff','Service','Facilities'], 'Food':['Food'],
        'Facilities':['Room','Facilities'],
    }
    issues = {'Quality':'Quality','Cleanliness':'Cleanliness','Comfort':'Comfort',
              'Noise':'Noise','Service':'Professionalism','Food':'Taste','Facilities':'Condition'}
    space = set('cramped tiny small large roomy huge narrow big crowded uncrowded congested compact'.split())
    timing = set('quick prompt rapid speedy sluggish delayed punctual timely late tardy'.split())
    missing = []
    seen = set()
    for group, words in catalog['groups'].items():
        for term in dict.fromkeys(words):
            if term in seen:
                continue
            seen.add(term)
            if term in catalog.get('preserved_opinions', []):
                continue
            candidates = lookup.get(term,[])
            if not candidates:
                missing.append(term)
                continue
            sense = catalog['sense_overrides'].get(term,sorted(candidates)[0][1])
            if sense not in {s for _,s in candidates}:
                raise ValueError(f'{term}: override does not contain this lemma.')
            issue = catalog.get('issue_overrides', {}).get(term,
                'Space' if term in space else 'Response Time' if term in timing else issues[group])
            spec = {'synset':sense,'issue':issue,'sense_selection':
                    'Explicit hotel-context gloss selection.' if term in catalog['sense_overrides'] else
                    'First-ranked WordNet adjective sense; original SentiWordNet score retained.'}
            if group in restrictions:
                spec['allowed_categories'] = restrictions[group]
            vocabulary['opinions'][term] = spec
    for category, groups in catalog['aspects'].items():
        if category not in categories:
            raise ValueError('Catalog must retain the existing category taxonomy.')
        for issue, terms in groups.items():
            for term in terms:
                term = term.lower()
                if term not in catalog.get('preserved_aspects', []):
                    vocabulary['aspects'][term] = {'category':category,**({'issue':issue} if issue!='General' else {})}
    equipment = {term for term,spec in vocabulary['aspects'].items() if spec['category']=='Facilities' and spec.get('issue') in
                 {'Ventilation','Air Conditioning','Shower','Plumbing','Water','Television','Refrigerator','WiFi','Elevator','Heating','Lighting'}}
    for term in ('working','functioning','operational','functional'):
        spec = vocabulary['opinions'][term]
        spec['allowed_aspects'] = sorted(set(spec.get('allowed_aspects',[])) | equipment)
    # Source-backed domain conventions only when the selected lexical score has
    # the opposite sign or zero. These never overwrite source P/N or TSV rows.
    for polarity, field in ((1,'positive_preferences'),(-1,'negative_preferences')):
        for category, terms in catalog[field].items():
            for term in terms:
                spec = vocabulary['opinions'].get(term)
                if not spec or category not in spec.get('allowed_categories',categories):
                    continue
                if category in spec.get('calibration', {}):
                    continue
                p,n,_ = senses[spec['synset']]
                lexical = p-n
                if lexical*polarity > 0:
                    continue
                spec.setdefault('calibration',{})[category] = round(polarity*(abs(lexical) or .25),6)
                spec['calibration_rule_id'] = 'hotel_attribute_preference'
                spec['calibration_reason'] = (
                    'Explicit hotel attribute preference: orient the magnitude of the original P-N score to the documented '
                    'domain preference; use 0.25 only when P-N is zero. Original P/N, selected sense and lexical score remain visible. '
                    'This is a domain rule, not a changed SentiWordNet score or learned confidence.'
                )
    # Fresh linen and fresh food have different WordNet senses and issues.
    vocabulary['opinions']['fresh']['category_senses'] = {
        'Room':{'synset':'a:00418198','issue':'Cleanliness','calibration':.75,
                'rule_id':'fresh_linen_preference','reason':'Unused/unsoiled linen is a positive hotel preference; the selected source score is negative. P/N are retained.'},
        'Cleanliness':{'synset':'a:01906320','issue':'Hygiene'},
        'Facilities':{'synset':'a:01906320','issue':'Ventilation'},
    }
    vocabulary['opinions']['fresh']['issue'] = 'Freshness'
    vocabulary['opinions']['stale']['issue'] = 'Freshness'
    vocabulary['opinions']['fresh']['allowed_categories'] = ['Food','Room','Cleanliness','Facilities']
    vocabulary['opinions']['stale']['allowed_categories'] = ['Food','Room']
    # Physical descriptors are not universally evaluative.
    vocabulary['opinions']['firm']['calibration'] = {'Room':0.0}
    vocabulary['opinions']['firm']['calibration_rule_id'] = 'firmness_description'
    vocabulary['opinions']['firm']['calibration_reason'] = 'Firmness alone is a bedding property, not a universal positive/negative preference. Source P/N are retained.'
    aliases = {
        'leaking':'leaky','stopped working':'malfunctioning','stops working':'malfunctioning',
        'stopped cooling':'malfunctioning','stops cooling':'malfunctioning',
        'not functioning properly':'malfunctioning', 'undercooked':'underdone','overcooked':'overdone',
        'mouthwatering':'mouth-watering','saggy':'sagging','freezing':'chilly',
        'well maintained':'maintained','well-maintained':'maintained','well kept':'maintained',
        'well-kept':'maintained','poorly maintained':'dilapidated','poorly-maintained':'dilapidated',
        'well lit':'well-lighted','well-lit':'well-lighted',
        'spotlessly clean':'spotless','squeaky clean':'spotless','brand new':'new',
        'overcrowded':'crowded','crunchy':'crisp','watered-down':'diluted','watered down':'diluted',
    }
    # Do not absorb negation into an alias: negation must remain a visible token.
    aliases.pop('not functioning properly')
    for alias, canonical in aliases.items():
        if canonical in vocabulary['opinions'] and alias not in vocabulary['opinions'] and alias not in vocabulary['aspects']:
            vocabulary.setdefault('opinion_aliases',{})[alias] = {'canonical':canonical,'kind':'OPINION'}
    for alias in ('stopped cooling','stops cooling'):
        if alias in vocabulary['opinion_aliases']:
            vocabulary['opinion_aliases'][alias]['allowed_aspects'] = sorted(t for t in equipment if vocabulary['aspects'][t].get('issue')=='Air Conditioning')
    vocabulary['opinion_aliases']['leaking']['allowed_aspects'] = sorted(t for t in equipment if vocabulary['aspects'][t].get('issue') in {'Shower','Plumbing','Water','Refrigerator'})
    vocabulary['intensifiers'].update({'slightly':.75,'somewhat':.75,'fairly':.9,'rather':1.1,'quite':1.1,
        'exceptionally':1.5,'incredibly':1.5,'absolutely':1.5,'particularly':1.25,'very much':1.25,
        'a bit':.75,'a little':.75,'a little bit':.75,'a lot':1.25,'so':1.25,'too':1.25})
    vocabulary['copulas'] = list(dict.fromkeys(vocabulary['copulas']+['seem','look','feel','taste','smell','smells','smelled','appear','appears','appeared','became','become','remained','remains']))
    vocabulary['introductions'] = ['i found','we found','i thought','we thought','i felt','we felt','i think','we think','i must say','we must say','overall','honestly','unfortunately','fortunately','there was','there were','there is','there are']
    vocabulary['introductions'] += ['i was','we were','i am','we are']
    vocabulary['experience_opinions'] = ['happy','unhappy','satisfied','dissatisfied','pleased','displeased','disappointed','impressed','disgusted','delighted']
    vocabulary['context_phrases'] = ['when we arrived','when i arrived','on arrival','upon arrival','during our stay','during my stay','throughout our stay','throughout my stay','during the night','at night','in the morning','in the evening','at breakfast','at dinner','for us','to us','to me','to everyone','for my family','for our family','at the hotel','in our room','in my room','in the room','for the price','for the money','for a hotel','for a short stay','for our stay','for my stay','on our first night','on the first night','throughout the night']
    vocabulary['possessives'] = ['has','have','had','with']
    vocabulary['post_modifiers'] = ['enough','indeed']
    vocabulary['context_relations'] = ['to','for','with','from','near','by']
    vocabulary['relation_targets'] = ['airport','the airport','station','train station','railway station','bus station','beach','the beach','city center','city centre','town center','town centre','shops','shopping','restaurants','town','downtown','everything','the city','the station']
    domain_path.write_text(json.dumps(vocabulary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    prepare()
    manifest = ROOT/'hotel_compiler/resources/opinion_senses.csv'
    with manifest.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['opinion','category_context','issue','synset','source_positive','source_negative','source_lexical','domain_score','selection_or_rule','gloss'])
        for term,spec in vocabulary['opinions'].items():
            p,n,g=senses[spec['synset']]
            writer.writerow([term,'default',spec['issue'],spec['synset'],p,n,p-n,'',spec.get('sense_selection','Previously configured sense.'),g])
            for category,score in spec.get('calibration',{}).items():
                writer.writerow([term,category,spec['issue'],spec['synset'],p,n,p-n,score,spec['calibration_reason'],g])
            for category,context in spec.get('category_senses',{}).items():
                p,n,g=senses[context['synset']]
                writer.writerow([term,category,context.get('issue',spec['issue']),context['synset'],p,n,p-n,context.get('calibration',''),'Explicit category-specific sense. '+context.get('reason',''),g])
    print(f"Vocabulary: {len(vocabulary['aspects'])} aspects, {len(vocabulary['opinions'])} opinions, {len(vocabulary['opinion_aliases'])} aliases; {len(categories)} categories.")
    print('Unavailable adjective forms (only explicit sourced aliases may cover them): '+', '.join(sorted(set(missing))))


if __name__ == '__main__':
    expand()
