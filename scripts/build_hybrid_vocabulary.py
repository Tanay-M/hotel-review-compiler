"""Build a reviewed hotel vocabulary overlay; no learning from ratings/labels.

Canonical expressions are scored by the existing VADER and TextBlob tools.
This catalog does not assign numerical valences or alter domain-rule weights.
"""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
ALL = ['Room', 'Staff', 'Service', 'Food', 'Cleanliness', 'Facilities']

ASPECTS = {
    'Room': '''guest room|guest rooms|guestroom|guestrooms|double room|double rooms|twin room|twin rooms|single room|single rooms|triple room|family room|family rooms|studio|studios|studio apartment|studio apartments|sleeping area|sleeping space|room size|room layout|room comfort|room decor|bed linen|bedlinen|bed sheet|bed sheets|bedsheets|sheet|sheets|duvet|duvets|quilt|quilts|blanket|blankets|bedspread|bedspreads|bed cover|pillowcase|pillowcases|pillow case|pillow cases|mattress topper|double bed|single bed|twin beds|king bed|queen bed|king size bed|queen size bed|sofa bed|sofabed|cot|cots|crib|cribs|bunk bed|bunk beds|bath|bathtub|bathtubs|bath tub|bath tubs|en suite|ensuite|en-suite bathroom|ensuite bathroom|private bathroom|shared bathroom|bathroom floor|bathroom ceiling|bathroom door|toilet seat|toilet paper|bidet|bidets|sink|sinks|washbasin|washbasins|basin|basins|showerhead|showerheads|shower head|shower heads|shower curtain|shower screen|shower cubicle|shower cabin|shower drain|bath mat|bath mats|bathmat|bathrobe|bathrobes|toiletries|toiletry|hairdryer|hairdryers|hair dryer|hair dryers|wardrobe|wardrobes|closet|closets|cupboard|cupboards|desk|desks|chair|chairs|armchair|armchairs|sofa|sofas|couch|couches|bedside table|bedside tables|nightstand|nightstands|night stand|night stands|bedside lamp|furnishings|furnishing|decor|décor|decoration|decorations|wall|window|door|doors|ceiling|ceilings|floor|floors|flooring|tile|tiles|curtain|carpet|room insulation|noise insulation|sound insulation|sound proofing|accomodation|accomodations|accommmodation|appartment|appartments''',
    'Staff': '''owner|owners|hotel owner|property owner|property owners|hostess|hostesses|landlord|landlady|host family|reception team|hotel team|cleaning staff|kitchen staff|breakfast staff|restaurant staff|bar staff|night staff|night porter|night receptionist|reception personnel|hotel personnel|service staff|frontdesk staff|cleaner|cleaners|housekeeper|housekeepers|caretaker|caretakers|reception lady|lady at reception|gentleman at reception|reception desk staff|receptionists team|reception manager|general manager|waitstaff|wait staff|bellhop|bellhops|doorman|doormen|doorkeeper''',
    'Service': '''communication|communications|check-in instructions|check in instructions|arrival instructions|arrival process|self check-in|self check in|self-check-in|self checkin|key collection|key pickup|key pick-up|key handover|luggage storage|baggage storage|luggage assistance|baggage assistance|luggage handling|luggage service|baggage service|transfer service|airport shuttle|airport pickup|airport pick-up|airport pick up|taxi booking|taxi service|housekeeping service|cleaning service|reception service|reception desk|frontdesk|customer care|guest service|guest services|customer support|reception assistance|tour booking|restaurant reservation|restaurant reservations|booking process|reservation process|check in process|check-in process|check out process|check-out process|late checkout|late check-out|early check-in|early check in|room allocation|room delivery|room cleaning|breakfast delivery|luggage delivery|porter service|booking assistance|guest assistance''',
    'Food': '''kitchen|kitchens|kitchenette|kitchenettes|cooking facilities|cooking utensils|cookware|utensils|cutlery|crockery|plates|kettle|kettles|coffee machine|coffee machines|coffee maker|coffee makers|espresso machine|nespresso machine|tea bags|teabags|cappuccino|cappuccinos|espresso|croissant|croissants|pastry|cake|cakes|biscuit|biscuits|cookie|cookies|yoghurt|yogurt|cereal|cereals|muesli|toast|cheese|cheeses|ham|scrambled eggs|omelette|omelet|fresh fruit|fruits|vegetables|salad|salads|pasta|seafood|fish|meat|milk|butter|jam|jams|honey|wine|wines|beer|beers|bottled water|drinking water|breakfast selection|breakfast spread|breakfast options|breakfast variety|breakfast buffet|buffet breakfast|continental breakfast|cooked breakfast|packed lunch|snack|fruit juice|orange juice|buffet selection|gluten free options|gluten-free options|vegan options|vegetarian options|dining room|dining area|dining experience|evening meal|breakfest|coffe|resturant|restuarant''',
    'Cleanliness': '''cleaning standard|cleaning quality|hygiene standards|hygiene standard|sanitary conditions|sanitary condition|hotel cleanliness|room cleanliness|bathroom cleanliness|cleanliness standards|general cleanliness''',
    'Facilities': '''air-conditioner|airconditioner|airconditioners|airconditioning|air conditioning unit|air conditioning units|air con|air-con|air co|airco|a c|air condition|air-condition|air-conditioning system|ventilation|fan|fans|ceiling fan|extractor fan|extractor|internet access|wireless internet|wireless connection|wi-fi connection|wifi connection|wi fi connection|wireless network|internet connection|internet speed|wifi signal|wi-fi signal|router|wifi router|plug|plugs|socket|sockets|electric sockets|electrical outlets|power outlets|power socket|power sockets|charger|charging station|charging points|ev charger|car charging|light|lights|lighting|lamp|lamps|stairs|stair|stairway|stairwell|staircase|staircases|steps|entrance|entryway|gate|gates|access code|door code|keycode|keypad|key card|key cards|keycard|keycards|room key|room keys|door lock|door locks|lock|locks|carpark|carparks|garage|garages|parking area|parking space|parking spaces|parking lot|private parking|secure parking|covered parking|free parking|private pool|outdoor pool|indoor pool|rooftop pool|swimming pools|jacuzzi|hot tub|steam room|wellness centre|wellness center|fitness room|exercise room|sunbed|sunbeds|sun lounger|sun loungers|loungers|parasols|pool area|pool towels|patio|courtyard|rooftop terrace|roof terrace|roof garden|garden area|outdoor area|communal area|common area|shared lounge|lounge|seating area|washing machine|washing machines|dryer|tumble dryer|iron|ironing board|ironing facilities|dishwasher|microwave|oven|stove|hob|cooktop|toaster|kitchen appliances|wheelchair access|disabled access|wheelchair ramp|ramp|escalator|luggage lift|room safe|security safe|security system|security|cctv|minifridge|mini fridge|mini refrigerator''',
}


def build():
    aliases = {}
    def add(canonical, words, categories=ALL, reason='Reviewed hotel opinion synonym'):
        for word in words.split('|'):
            word = word.strip().lower()
            if not word or word == canonical: continue
            entry = {'canonical': canonical, 'categories': categories, 'reason': reason}
            if word in aliases:
                if aliases[word]['canonical'] != canonical:
                    raise ValueError(f'Conflicting canonical expression for {word}')
                aliases[word]['categories'] = sorted(set(aliases[word]['categories']) | set(categories))
                continue
            aliases[word] = entry

    people = ['Staff', 'Service']
    space = ['Room', 'Facilities']
    hygiene = ['Room', 'Facilities', 'Food', 'Cleanliness']
    add('courteous', 'polite|politeness|politely|courteously|well-mannered|well mannered|civil', people)
    add('helpful', 'accommodating|accomodating|accomodative|accommodative|hospitable|hospitably|obliging|obligingly|cooperative|co-operative|cooperatively|resourceful|resourcefully|supportively|service-minded|service minded', people)
    add('competent', 'knowledgeable|knowledgeably|informative|informatively|well-informed|well informed|well-trained|well trained|proficient|proficiently|capable|capably', people)
    add('friendly', 'personable|cordial|cordially|approachable|approachability|affable|affably|amiable|amiably|communicative|communicatively|unfailingly friendly|freindly|friendy', people)
    add('attentive', 'attentiveness|attentively|considerate|considerately|thoughtful|thoughtfully|proactive|proactively|mindful|mindfully|receptive', people)
    add('welcoming', 'warm-hearted|warmhearted|warm hearted|wholehearted|inviting|invitingly|welcomed', people)
    add('efficient', 'efficiency|efficiently|organized|organised|well-organized|well-organised|well organized|well organised|seamless|seamlessly|streamlined|smoothly', people)
    add('quick', 'prompt|promptly|timely|punctual|punctually|speedy|speedily|swift|swiftly|expeditious|expeditiously|rapid|rapidly', people)
    add('trustworthy', 'reliable|reliably|reliability|dependable|dependably|dependability|trustworthy|trustworthiness', ['Staff', 'Service', 'Facilities'])
    add('rude', 'impolite|impolitely|discourteous|discourteously|disrespectful|disrespectfully|unfriendly|unwelcoming|unhelpful|unprofessional|unprofessionally|uncooperative|unaccommodating|unaccomodating|dismissive|dismissively|inattentive|inattentively|unattentive|arrogant|arrogantly|hostile|hostility', people)
    add('incompetent', 'inefficient|inefficiently|inefficiency|disorganized|disorganised|disorganization|disorganisation|uncommunicative|unprepared|untrained|inept|ineptly|unqualified', people)
    add('uncomfortable', 'uncomfy|stuffy|airless|unventilated|poorly-ventilated|poorly ventilated|claustrophobic|suffocating|unbreathable|draughty|drafty', space)
    add('comfortable', 'comfy|cosy|homey|homely|homelike|cozily|cosily|comfortably|comfortableness|confortable|confortably|comfotable|comfortible|well-cushioned|well cushioned|restful', space)
    add('large', 'spacious|spaciousness|roomy|airy|expansive|capacious|generously-sized|generously sized|well-proportioned|well proportioned', space)
    add('uncomfortable', 'crampy|constricted|pokey|poky|squashed|squeezy', space)
    # 'cramped' has an existing domain rule but no native lexical evidence.
    add('uncomfortable', 'cramped|crampedness|overcrowded|congested', space)
    add('peaceful', 'soundproof|sound-proof|sound proof|soundproofed|sound-proofed|sound proofed|well-insulated|well insulated|tranquil|tranquillity|tranquility|serene|serenity|quietest|quieter', space)
    add('noisy', 'noise|noisiness|noisier|noisiest|loudness|boisterous|raucous|deafening|unquiet', space)
    add('clean', 'spotless|spotlessly|immaculate|immaculately|pristine|hygienic|hygienically|sanitary|sanitized|sanitised|well-cleaned|well cleaned|squeaky-clean|squeaky clean|cleanest|cleaner|cleanness|cleanliness|neatness|tidiness', hygiene)
    add('dirty', 'unclean|unhygienic|unhygienically|unsanitary|unsanitized|unsanitised|grimy|grubbiness|grubby|mouldy|moldy|mould|mold|mildewed|mildew|stained|stains|stain|soiled|soiling|greasy|sticky|smelly|smells|stinky|stinking|odorous|malodorous|foul-smelling|foul smelling|uncleanliness', hygiene)
    add('disgusting', 'filth|squalid|squalor|vermin|infested|infestation|bug-infested|cockroach|cockroaches|bedbug|bedbugs|bed bugs|bed-bugs|reeking', hygiene)
    add('delicious', 'tasty|tastier|tastiest|flavoursome|flavorsome|flavourful|flavorful|scrumptious|delectable|mouthwatering|mouth-watering|appetizing|appetising|yummy|yummiest|flavours|flavors', ['Food'])
    add('generous', 'plentiful|plentifully|ample|abundant|abundantly|bountiful|copious|copiously|lavish|lavishly|well-stocked|well stocked', ['Food', 'Facilities'])
    add('fresh', 'freshly-baked|freshly baked|freshly-cooked|freshly cooked|freshness', ['Food'])
    add('bad', 'inedible|unpalatable|unappetizing|unappetising|tasteless|flavourless|flavorless|overcooked|undercooked|burnt|burned|rancid|spoilt|spoiled|soggy|staleness|spoiling', ['Food'])
    add('beautiful', 'picturesque|picture-perfect|picture perfect|aesthetically-pleasing|aesthetically pleasing|tastefully-decorated|tastefully decorated|tasteful|tastefully|stylish|stylishly|aesthetic|aesthetically', ['Room', 'Facilities'])
    add('charming', 'quaint|quaintly|characterful|character-filled|character filled|chic|charmingness', ['Room', 'Facilities'])
    add('excellent', 'luxurious|luxuriously|luxury|sumptuous|sumptuously|upscale|high-end|high end|high-quality|high quality|top-quality|top quality|first-class|first class|top-notch|top notch|impeccably|exemplary|faultless|faultlessly|unbeatable|unsurpassed|unparalleled', ALL)
    add('good', 'well-equipped|well equipped|fully-equipped|fully equipped|well-appointed|well appointed|well-furnished|well furnished|well-maintained|well maintained|well-kept|well kept|well-designed|well designed|well-designed|well-serviced|well serviced|well-supplied|well supplied|well-run|well run', ALL)
    add('useful', 'functional|functionality|practical|practically|convenient|conveniently|convenience|user-friendly|user friendly|intuitive|intuitively|usable|usability', ['Room', 'Facilities', 'Service'])
    add('dangerous', 'unsafe|hazardous|hazard|hazards|slippery|treacherous|insecure|unsecured', ['Room', 'Facilities'])
    add('broken', 'malfunctioning|malfunctioned|malfunction|faulty|faultiness|defective|defect|defects|inoperable|nonfunctional|non-functional|unusable|unserviceable|damaged|leaky|leakage|leaking|clogged|blocked|disconnected|disconnecting|out-of-order|out of order', ['Room', 'Facilities'])
    add('bad', 'unreliable|undependable|intermittent|intermittently|patchy|spotty|temperamental|unstable|unresponsive|unavailable|nonexistent|non-existent|non existent', ['Facilities', 'Staff', 'Service'])
    add('bad', 'dilapidated|run-down|run down|worn-out|worn out|threadbare|tattered|shabby|unmaintained|neglected|poorly-maintained|poorly maintained|substandard|sub-standard|subpar|sub-par', ['Room', 'Facilities', 'Cleanliness'])

    # Explicit inflections; no unrestricted stemming or automatic polarity flips.
    for canonical, forms in {
        'kind': 'kinder|kindest|kindly', 'friendly': 'friendlier|friendliest',
        'helpful': 'helpfully|helpfulness', 'comfortable': 'comfiest|comfier|coziest|cozier|cosiest|cosier',
        'clean': 'cleanly', 'dirty': 'dirtier|dirtiest', 'beautiful': 'beautifully',
        'lovely': 'lovelier|loveliest', 'pleasant': 'pleasantly|pleasanter|pleasantest',
        'rude': 'ruder|rudest|rudely|rudeness', 'slow': 'slower|slowest|sluggish|sluggishly',
        'easy': 'easier|easiest', 'difficult': 'tricky|trickier|trickiest',
        'excellent': 'excelent|exellent', 'amazing': 'amazin', 'delicious': 'delicous',
    }.items(): add(canonical, forms, ALL, 'Explicit reviewed inflection or spelling variant')

    inventory = ROOT / 'output/experiments/2026-10-18/booking-vocabulary/before/adjective_inventory.csv'
    observed = {}
    if inventory.exists():
        with inventory.open(encoding='utf-8-sig', newline='') as f: observed = {r['term']: r for r in csv.DictReader(f)}
    for word, entry in aliases.items():
        row = observed.get(word, {})
        entry['observed_adjective_occurrences'] = int(row.get('occurrences', 0))
        entry['example_source_row'] = int(row['example_source_row']) if row else None
    result = {
        'version': 'hotel-vocabulary-2026-10-18',
        'scope': 'Independent hybrid only. Six categories, fusion weights, bands and existing context-rule values unchanged.',
        'provenance': 'Project-reviewed lexical synonyms, explicit forms and hotel aspect phrases, guided by the supplied 4367-row Crawlfeeds Booking Italy vocabulary audit. No ratings, positive/negative field headings or gold sentiment labels used.',
        'normalization_policy': 'Only native-unknown expressions are canonicalized in a separate scoring copy. Category guards apply. Native and effective scoring evidence are retained. Generic hotel/location/price terms are not forced into the six categories.',
        'aspect_additions': {k: sorted(set(v.split('|'))) for k, v in ASPECTS.items()},
        'excluded_aspect_phrases': ['water taxi', 'water taxis'],
        'lexical_aliases': dict(sorted(aliases.items())),
    }
    path = ROOT / 'hotel_compiler/resources/hybrid_vocabulary.json'
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'{len(aliases)} lexical forms; {sum(len(v) for v in result["aspect_additions"].values())} aspect additions before deduplication.')


if __name__ == '__main__': build()
