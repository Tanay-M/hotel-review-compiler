"""Deterministic grammar extension with bounded, source-spanned recovery.

No TextBlob/VADER calls. Recognized fragments remain partial when any material
language is unexplained. Pronouns require one unambiguous preceding target.
"""
from dataclasses import replace
from .models import Clause, Diagnostic, ReviewAST, Token
from .vocabulary import load_vocabulary

OPINIONS = {'OPINION', 'FUNCTION_VERB', 'LEXICAL_VERB'}
BRIDGE = {'COPULA', 'AUXILIARY', 'DETERMINER', 'INTENSIFIER', 'NEGATION', 'ADVERB',
          'POST_MODIFIER', 'EMPHASIS', 'CONTEXT', 'INTRODUCTION', 'PRONOUN'}
STRUCTURAL_WORDS = {'i','we','you','he','she','me','us','them','is','are','was','were','be','been',
                    'being','also','only','still','always','just','really','very','not','no',
                    'both','all','some','any','each','every','another','other','two','three',
                    'one','four','five','six','seven','eight','nine','ten'}
SUBJECT_VERBS = {'verb_help','verb_assist','verb_ignore','verb_disappoint','verb_impress'}


def _bridge(tokens, *, adjectives=False):
    return all(t.kind in BRIDGE or adjectives and t.kind == 'OPINION' or
               t.kind in {'COMMA','CONNECTOR'} and t.value in {',','and','but','however'} or
               t.kind == 'WORD' and t.value in STRUCTURAL_WORDS or
               t.kind == 'PUNCTUATION' and t.value in {':','-','"',"'"} for t in tokens)


def _modifiers(tokens, index):
    negation = None; degree = None; context = []
    for token in reversed(tokens[max(0,index-4):index]):
        if token.kind == 'INTENSIFIER' and degree is None: degree = token
        elif token.kind == 'NEGATION':
            # 'not only ... but also' does not negate the following adjective.
            following = [t.value for t in tokens if token.end <= t.start < tokens[index].start]
            if following and following[0] == 'only': context.append(token); continue
            if negation is not None: return None, degree, context, True
            negation = token
        elif token.kind in {'COPULA','AUXILIARY'}: continue
        elif token.value in {'only','also'}: context.append(token)
        else: break
    return negation, degree, context, False


def _subjects_before(tokens, index):
    candidates = [i for i,t in enumerate(tokens[:index]) if t.kind == 'ASPECT']
    if not candidates: return []
    last = candidates[-1]
    if index-last > 9 or not _bridge(tokens[last+1:index]): return []
    result = [tokens[last]]
    for previous in reversed(candidates[:-1]):
        between = tokens[previous+1:last]
        if not between or not all(t.kind in {'DETERMINER','COMMA'} or t.kind == 'CONNECTOR' and t.value == 'and' for t in between): break
        result.insert(0,tokens[previous]); last = previous
    return result


def _targets_after(tokens, index):
    for end in range(index+1,min(len(tokens), index+9)):
        if tokens[end].kind == 'ASPECT':
            return [tokens[end]] if _bridge(tokens[index+1:end], adjectives=True) else []
        if tokens[end].kind in {'COPULA','AUXILIARY','LEXICAL_VERB','END'}: break
    return []


def recover(tokens, previous, *, allow_shared=True):
    clauses=[];diagnostics=[];used=set()
    for i, opinion in enumerate(tokens):
        if opinion.kind not in OPINIONS: continue
        targets=[];form='expanded_subject_predicate'
        if opinion.kind == 'LEXICAL_VERB':
            targets = _subjects_before(tokens,i) if opinion.value in SUBJECT_VERBS else _targets_after(tokens,i)
            form = 'native_verb_subject' if opinion.value in SUBJECT_VERBS else 'native_verb_object'
        else:
            # An immediately following noun wins for attributive adjectives.
            targets = _targets_after(tokens,i)
            if targets: form='expanded_attributive'
            else: targets = _subjects_before(tokens,i)
        if not targets and any(t.kind == 'PRONOUN' for t in tokens[:i]) and len(previous)==1 and _bridge(tokens[:i]):
            targets=previous;form='resolved_pronoun_predicate'
        if not targets and allow_shared and len(previous)==1 and _bridge(tokens[:i]) and not any(t.kind=='ASPECT' for t in tokens[:i]):
            targets=previous;form='expanded_shared_predicate'
        if not targets: continue
        prefix=[t.value for t in tokens[:i]]
        if any(prefix[j]=='not' and prefix[j+1] in {'all','every','both'} for j in range(len(prefix)-1)):
            diagnostics.append(Diagnostic('COMPLEX_NEGATION','Quantified negation requires inspection; no blanket sentiment is assigned.',tokens[0].start,opinion.end,'syntax'))
            continue
        negation, degree, context, complex_negation = _modifiers(tokens,i)
        if opinion.value=='available' and len(targets)==1 and targets[0] in tokens:
            target_index=tokens.index(targets[0])
            if target_index and tokens[target_index-1].value in {'no','without'}:
                t=tokens[target_index-1];negation=Token('NEGATION','not',t.text,t.start,t.end)
        if complex_negation:
            diagnostics.append(Diagnostic('COMPLEX_NEGATION','Multiple negators need inspection; no score is invented.',tokens[0].start,opinion.end,'syntax'))
            continue
        start=(negation or degree or opinion).start
        for subject in targets:
            clauses.append(Clause(subject, opinion, negation, degree, None,
                           min(subject.start,start) if form!='resolved_pronoun_predicate' else tokens[0].start,
                           max(subject.end,opinion.end), opinion_start=start,opinion_end=opinion.end,
                           form=form,context=tuple(context)))
            used.add(subject.start)
        used.add(opinion.start)
        for t in (negation,degree):
            if t: used.add(t.start)
    # Explicit absence of a named facility is a negated availability predicate.
    v=load_vocabulary()
    for i,t in enumerate(tokens):
        if t.value not in {'no','without'}: continue
        tail=tokens[i+1:i+4]
        target=next((a for a in tail if a.kind=='ASPECT'),None)
        if target is None or v['aspects'][target.value]['category']!='Facilities': continue
        if any(a.kind not in {'DETERMINER','ASPECT'} for a in tail[:tail.index(target)]): continue
        if any(c.subject==target for c in clauses): continue
        remaining=tokens[tokens.index(target)+1:]
        if any(a.kind in OPINIONS for a in remaining): continue
        op=Token('OPINION','available',target.text,target.start,target.end,'absence:explicit_not_available')
        neg=Token('NEGATION','not',t.text,t.start,t.end)
        clauses.append(Clause(target,op,neg,None,None,t.start,target.end,opinion_start=t.start,
                              opinion_end=target.end,form='explicit_facility_absence',context=(t,)))
        used.update([t.start,target.start])
    unexplained=[t for t in tokens if t.start not in used and not (
                 t.kind in BRIDGE|{'COMMA','CONNECTOR','RELATION','POSSESSION','END'} or
                 t.kind=='WORD' and t.value in STRUCTURAL_WORDS or
                 t.kind=='PUNCTUATION' and t.value in {'"',"'",'(',')',':','-'} or
                 t.kind=='OPINION' and t.value in {'only','also','still','other','one'})]
    if unexplained:
        diagnostics.append(Diagnostic('UNRESOLVED_CLAUSE','Retained recognized opinions; remaining language requires inspection.',
                                      unexplained[0].start,unexplained[-1].end,'syntax'))
    return clauses,diagnostics


def parse_expanded(tokens, strict_parser):
    original, errors = strict_parser(tokens).parse()
    clauses=list(original.clauses);diagnostics=[]
    for error in errors:
        if error.code!='UNSUPPORTED_CLAUSE': diagnostics.append(error);continue
        fragment=[t for t in tokens if error.start <= t.start and t.end <= error.end]
        preceding=[c for c in clauses if c.end<=error.start]
        previous=[];allow_shared=True
        if preceding:
            last=max(preceding,key=lambda c:c.end)
            gap=[t for t in tokens if last.end<=t.start<error.start]
            ends=sum(t.kind=='END' for t in gap)
            if ends<=1 and all(t.kind in {'END','COMMA','CONNECTOR'} for t in gap):
                group=[c.subject for c in preceding if c.subject and c.start==last.start and c.end==last.end]
                previous=list({s.value:s for s in group}.values())
                allow_shared=not ends
        recovered, extra = recover(fragment,previous,allow_shared=allow_shared)
        if recovered: clauses.extend(recovered);diagnostics.extend(extra)
        else: diagnostics.append(error)
    clauses.sort(key=lambda c:(c.start,c.opinion.start,c.subject.start if c.subject else -1))
    # Comma/adjective lists share explicit targets; pronouns remain unambiguous.
    resolved=[];previous=[];last_span=None
    for c in clauses:
        if c.subject is None and c.connector=='recovery' and previous and last_span:
            gap=[t for t in tokens if last_span[1]<=t.start<c.start]
            bad=any(last_span[0]<=d.start<c.start for d in diagnostics)
            if gap and not bad and all(t.kind in {'COMMA','CONNECTOR'} for t in gap):
                c=replace(c,connector='comma')
        if c.subject is None and c.connector in {'comma','and','but','however'} and previous:
            resolved.extend(replace(c,subject=s,form='expanded_shared_predicate') for s in previous)
            continue
        resolved.append(c)
        if c.subject:
            span=(c.start,c.end)
            if c.form=='coordinated_subjects' and span==last_span:
                previous=list({s.value:s for s in [*previous,c.subject]}.values())
            else: previous=[c.subject]
            last_span=span
        elif c.connector in {'sentence_end','recovery'}:previous=[]
    return ReviewAST(tuple(resolved)),tuple(diagnostics)
