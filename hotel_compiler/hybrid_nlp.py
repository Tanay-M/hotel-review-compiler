"""Independent TextBlob Pattern grammar front end; no SentiWordNet vocabulary.

The bundled Pattern parser supplies POS and shallow phrase chunks. This is
rule-based attachment, not dependency parsing or unrestricted understanding.
Noun phrases come from its NP chunks (no Brown-corpus training/download).
"""
from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib.resources import files
import json
import re
from .hybrid_vocabulary import vocabulary

MAX_REVIEW_LENGTH = 10_000


@lru_cache(maxsize=1)
def domain():
    result = json.loads(files('hotel_compiler').joinpath('resources/hybrid_domain.json').read_text(encoding='utf-8'))
    overlay = vocabulary()
    for category, phrases in overlay['aspect_additions'].items():
        if category not in result['categories']:
            raise ValueError('Vocabulary expansion must preserve the six categories.')
        result['aspects'][category] = list(dict.fromkeys(result['aspects'][category] + phrases))
    result['vocabulary_version'] = overlay['version']
    return result


@dataclass(frozen=True)
class NLPToken:
    text: str
    pos: str
    chunk: str
    preposition: str
    start: int
    end: int
    sentence: int


@dataclass(frozen=True)
class Mention:
    category: str
    text: str
    start: int
    end: int
    first: int
    last: int


@dataclass(frozen=True)
class Candidate:
    category: str
    aspect: str
    context: str
    start: int
    end: int
    aspect_start: int
    aspect_end: int
    pattern: str
    inherited: bool = False


@dataclass(frozen=True)
class NLPDiagnostic:
    code: str
    message: str
    start: int
    end: int
    stage: str = 'hybrid_nlp'


@dataclass(frozen=True)
class NLPAnalysis:
    tokens: tuple[NLPToken, ...]
    noun_phrases: tuple[dict, ...]
    segments: tuple[dict, ...]
    candidates: tuple[Candidate, ...]
    diagnostics: tuple[NLPDiagnostic, ...]

    def to_dict(self):
        return asdict(self)


CONTRACTIONS = {
    "can't": 'can not', "cannot": 'can not', "won't": 'will not',
    "shan't": 'shall not', "isn't": 'is not', "aren't": 'are not',
    "wasn't": 'was not', "weren't": 'were not', "don't": 'do not',
    "doesn't": 'does not', "didn't": 'did not', "couldn't": 'could not',
    "wouldn't": 'would not', "shouldn't": 'should not', "hasn't": 'has not',
    "haven't": 'have not', "hadn't": 'had not', "it's": 'it is',
    "they're": 'they are', "we're": 'we are', "that's": 'that is',
    "i'm": 'I am', "i've": 'I have', "we've": 'we have',
    "there's": 'there is', "it'd": 'it would', "they've": 'they have',
}
_CONTRACTION_RE = re.compile(r"\b(?:"+'|'.join(map(re.escape, sorted(CONTRACTIONS,key=len,reverse=True)))+r")\b", re.I)
AUXILIARIES = frozenset('be am is are was were been being feel feels felt seem seems seemed look looks looked have has had do does did can could will would should may might must get gets got'.split())
MODIFIERS = frozenset('not never no very really extremely quite so too slightly rather fairly incredibly absolutely exceptionally hardly barely almost also just still only much more most less least'.split())
CONTRAST = frozenset(('but','however','yet','although','whereas','nevertheless','though'))


def prepare_text(text):
    """Expand contractions in a working copy and retain original character spans."""
    normalized = text.translate(str.maketrans({'’': "'", '‘': "'", '“': '"', '”': '"', '–': '-', '—': '-'}))
    output=[]; offsets=[]; cursor=0
    for match in _CONTRACTION_RE.finditer(normalized):
        output.append(normalized[cursor:match.start()]);offsets.extend((i,i+1) for i in range(cursor,match.start()))
        replacement=CONTRACTIONS[match.group().lower()]
        if match.group().isupper():replacement=replacement.upper()
        elif match.group()[0].isupper():replacement=replacement[0].upper()+replacement[1:]
        output.append(replacement);offsets.extend((match.start(),match.end()) for _ in replacement)
        cursor=match.end()
    output.append(normalized[cursor:]);offsets.extend((i,i+1) for i in range(cursor,len(text)))
    return ''.join(output), offsets


@lru_cache(maxsize=512)
def _phrase_pattern(phrase):
    return re.compile(r'(?<!\w)'+r'[\s\-–—]+'.join(map(re.escape,re.split(r'[\s-]+',phrase)))+r'(?!\w)',re.I)


@lru_cache(maxsize=1)
def _aspect_patterns():
    return sorted(((category,_phrase_pattern(phrase)) for category,phrases in domain()['aspects'].items()
                   for phrase in phrases), key=lambda item:len(item[1].pattern),reverse=True)


def _mentions(text,tokens):
    found=[]
    excluded = [match.span() for phrase in vocabulary().get('excluded_aspect_phrases', [])
                for match in _phrase_pattern(phrase).finditer(text)]
    for category,pattern in _aspect_patterns():
        for match in pattern.finditer(text):
            if any(match.start() < end and match.end() > start for start, end in excluded):continue
            if any(match.start()<m.end and match.end()>m.start for m in found):continue
            indexes=[i for i,t in enumerate(tokens) if t.start<match.end() and t.end>match.start()]
            # Preserve noun/adjective distinctions for ambiguous aspect words:
            # "the cleaner was helpful" versus "the room was cleaner".
            if match.group().lower() in {'safe','cleaner','light'} and indexes and tokens[indexes[0]].pos.startswith('JJ'):
                following = indexes[-1] + 1
                nominal_subject = following < len(tokens) and tokens[following].pos.startswith('VB')
                if not nominal_subject:continue
            if indexes:found.append(Mention(category,match.group(),match.start(),match.end(),indexes[0],indexes[-1]))
    return sorted(found,key=lambda m:m.start)


def domain_adjustment(category, text):
    """Return a documented contextual rule; raw library scores remain available.

    Multiple rules with opposite signs abstain from overriding a mixed context.
    Local negation changes a domain rule once; analyzers' scores are untouched.
    """
    working,_=prepare_text(text);matches=[]
    for rule in domain()['rules']:
        if category not in rule['categories']:continue
        for match in re.finditer(rule['pattern'],working,re.I):
            score=rule['score']
            prefix=re.findall(r"\b\w+\b",working[max(0,match.start()-35):match.start()].lower())[-3:]
            if not rule.get('literal_negation') and any(w in {'not','never','no','without','hardly'} for w in prefix):
                score=-score
            matches.append((rule['id'],score,match.group()))
    if not matches:return None
    if any(s>0 for _,s,_ in matches) and any(s<0 for _,s,_ in matches):return None
    # Most specific configured rule first; e.g. explicit failure before success.
    identifier,score,matched=matches[0]
    return {'rule_id':identifier,'score':score,'matched':matched}


def _opinion_indexes(tokens, indexes, mentions, has_lexical):
    occupied={i for m in mentions for i in range(m.first,m.last+1)}
    result=[]
    for i in indexes:
        token=tokens[i];word=token.text.lower()
        if i in occupied or word in AUXILIARIES or word in MODIFIERS or word in CONTRAST:continue
        if token.pos.startswith('JJ') or (token.pos.startswith(('VB','NN','RB','SYM')) and has_lexical(word)):
            result.append(i)
    return result


def _segments(tokens,mentions,has_lexical):
    """Split contrasts and coordinated predicates, retain coordinated subjects."""
    groups=[];current=[];closed=False
    for i,t in enumerate(tokens):
        terminal=t.text in {'.','!','?',';'}
        closing=t.pos=='SYM' or t.text in {'"',"'",')',']'}
        if current and not terminal and not closing and (closed or t.sentence!=tokens[current[0]].sentence):
            groups.append(current);current=[];closed=False
        current.append(i)
        if terminal:closed=True
    if current:groups.append(current)
    output=[]
    for group in groups:
        left=[]
        for offset,i in enumerate(group):
            word=tokens[i].text.lower();right=group[offset+1:]
            lm=[m for m in mentions if m.first in left]
            rm=[m for m in mentions if m.first in right]
            left_op=_opinion_indexes(tokens,left,lm,has_lexical)
            right_op=_opinion_indexes(tokens,right,rm,has_lexical)
            # A functional verb is a predicate even when neither lexicon knows it.
            left_pred=left_op or any(tokens[j].pos.startswith('VB') for j in left)
            split=(word in CONTRAST or
                   (word in {'and','&',','} and left_pred and (rm or right_op)))
            if split and left:
                output.append(left);left=[]
            else:left.append(i)
        if left:output.append(left)
    return output


def analyze_language(text, parser, has_lexical):
    working, offsets=prepare_text(text)
    parsed=parser.parse(working)
    tokens=[];cursor=0
    for sentence,line in enumerate(str(parsed).splitlines()):
        for item in line.split():
            word,pos,chunk,preposition=item.rsplit('/',3)
            word=word.replace('&slash;','/');start=working.find(word,cursor)
            if start<0:raise ValueError(f'TextBlob token could not be aligned to the input: {word!r}')
            end=start+len(word);cursor=end
            tokens.append(NLPToken(word,pos,chunk,preposition,offsets[start][0],offsets[end-1][1],sentence))
    tokens=tuple(tokens);mentions=_mentions(text,tokens);phrases=[];np=[]
    for token in tokens:
        if token.chunk=='B-NP' or not token.chunk.endswith('NP'):
            if np:phrases.append({'text':text[np[0].start:np[-1].end],'start':np[0].start,'end':np[-1].end});np=[]
        if token.chunk.endswith('NP'):np.append(token)
    if np:phrases.append({'text':text[np[0].start:np[-1].end],'start':np[0].start,'end':np[-1].end})
    candidates=[];diagnostics=[];segments=[];last_mentions=[];last_sentence=-1
    for indexes in _segments(tokens,mentions,has_lexical):
        start,end=tokens[indexes[0]].start,tokens[indexes[-1]].end
        context=text[start:end];sentence=tokens[indexes[0]].sentence
        local=[m for m in mentions if m.first in indexes];inherited=False
        outside=any(_phrase_pattern(p).search(context) for p in domain()['out_of_scope'])
        if outside:diagnostics.append(NLPDiagnostic('OUT_OF_SCOPE','Contains a Location/Price/Value topic outside the six categories.',start,end))
        # Scope inheritance is limited to an explicit same-sentence continuation
        # or an immediately following it/they sentence with one previous target.
        words=[tokens[i].text.lower() for i in indexes]
        if not local and not outside and last_mentions:
            continuation=sentence==last_sentence
            pronoun=words[0] in {'it','they','this','these'} and sentence==last_sentence+1 and len(last_mentions)==1
            if continuation or pronoun:local=last_mentions;inherited=True
        opinions=_opinion_indexes(tokens,indexes,[m for m in local if not inherited],has_lexical)
        price_opinions={i for i in opinions if tokens[i].text.lower() in domain()['price_opinions']}
        if price_opinions:
            diagnostics.append(NLPDiagnostic('OUT_OF_SCOPE_PRICE_OPINION','Price/value opinion is outside the six categories.',start,end))
            opinions=[i for i in opinions if i not in price_opinions]
        if re.search(r'\bnot\s+only\b',context,re.I):
            diagnostics.append(NLPDiagnostic('COMPLEX_NEGATION','Not-only construction requires inspection; no completeness claim.',start,end))
        by_target={}
        for opinion in opinions:
            if not local:continue
            preceding=[m for m in local if m.last<opinion]
            following=[m for m in local if m.first>opinion]
            if inherited:targets=local;pattern='shared_subject'
            elif following and (not preceding or (tokens[opinion].pos.startswith('JJ') and tokens[opinion].chunk.endswith('NP'))):
                targets=[min(following,key=lambda m:m.first-opinion)];pattern='opinion_verb_object' if tokens[opinion].pos.startswith('VB') else 'attributive'
            else:
                target=max(preceding,key=lambda m:m.last) if preceding else local[0]
                targets=[target];pattern='aspect_predicate'
                # Share a trailing predicate across noun subjects joined by and.
                for previous in reversed(preceding[:-1]):
                    gap=range(previous.last+1,targets[0].first)
                    if any(tokens[j].text.lower() in {'and','&',','} for j in gap) and not any(tokens[j].pos.startswith(('JJ','VB')) for j in gap):targets.insert(0,previous)
                    else:break
            for target in targets:
                key=(target.category,target.start,target.end)
                entry=by_target.setdefault(key,[target,[],pattern]);entry[1].append(opinion)
        # Functional failures and unknown predicates survive lexical scoring gates.
        for mention in local:
            key=(mention.category,mention.start,mention.end)
            if key not in by_target and not price_opinions and (domain_adjustment(mention.category,context) or
                (len(local)==1 and any(tokens[i].pos.startswith('VB') for i in indexes))):
                by_target[key]=[mention,[],'functional_or_unresolved_predicate']
        emitted=[]
        for target,attached,pattern in by_target.values():
            a,b=start,end
            if len(by_target)>1 and attached:
                first,last=min(attached),max(attached)
                if not inherited:
                    first=min(first,target.first);last=max(last,target.last)
                # Include modifiers immediately before the local phrase.
                while first>indexes[0] and (tokens[first-1].pos in {'RB','RBR','RBS','DT'} or tokens[first-1].text.lower() in MODIFIERS):first-=1
                a,b=tokens[first].start,tokens[last].end
            candidate=Candidate(target.category,target.text,text[a:b],a,b,target.start,target.end,pattern,inherited)
            candidates.append(candidate);emitted.append(len(candidates)-1)
        if not emitted and any(t not in {'.',',','!','?',';',':','"',"'"} for t in words):
            diagnostics.append(NLPDiagnostic('UNRESOLVED_CLAUSE','No supported aspect/opinion attachment; original text retained.',start,end))
        segments.append({'text':context,'start':start,'end':end,'sentence':sentence,'candidate_indexes':emitted})
        if not inherited:
            last_mentions=local;last_sentence=sentence
        elif sentence!=last_sentence:last_sentence=sentence
        if outside and not local:last_mentions=[]
    return NLPAnalysis(tokens,tuple(phrases),tuple(segments),tuple(candidates),tuple(diagnostics))
