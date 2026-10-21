"""Explicit denominators and abstention-aware research classification metrics."""
import random

LABELS = ('Negative', 'Neutral', 'Positive')


def classification_metrics(rows):
    """Rows have gold/prediction; None/Unanalyzed/Mixed are incorrect abstentions.

    Fixed three-class macro-F1 includes missing predictions as false negatives.
    Conditional accuracy is secondary to correct/all eligible gold cases.
    """
    n = len(rows)
    correct = sum(r['gold'] == r['prediction'] for r in rows)
    scored = sum(r['prediction'] in LABELS for r in rows)
    classes = []
    for label in LABELS:
        tp = sum(r['gold'] == label == r['prediction'] for r in rows)
        fp = sum(r['prediction'] == label and r['gold'] != label for r in rows)
        fn = sum(r['gold'] == label and r['prediction'] != label for r in rows)
        classes.append({'label':label,'support':sum(r['gold']==label for r in rows),
                        'precision':tp/(tp+fp) if tp+fp else 0.0,
                        'recall':tp/(tp+fn) if tp+fn else 0.0,
                        'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0})
    return {'cases':n,'correct':correct,'scored':scored,
            'accuracy':correct/n if n else None,'coverage':scored/n if n else None,
            'conditional_accuracy':correct/scored if scored else None,
            'macro_f1':sum(r['f1'] for r in classes)/3 if n else None,
            'classes':classes}


def clustered_accuracy_interval(rows, *, seed=17, repeats=1000):
    """Percentile bootstrap by source review; preserves correlated sentences."""
    if not isinstance(repeats,int) or isinstance(repeats,bool) or repeats<2:
        raise ValueError('Bootstrap repeats must be an integer >= 2.')
    grouped = {}
    for row in rows:
        grouped.setdefault(row['parent_id'], []).append(row)
    groups = list(grouped.values())
    if len(groups)<2:
        return None, None
    rng = random.Random(seed); values=[]
    for _ in range(repeats):
        sample=[r for _ in groups for r in groups[rng.randrange(len(groups))]]
        values.append(sum(r['gold']==r['prediction'] for r in sample)/len(sample))
    values.sort()
    return values[int(.025*(repeats-1))], values[int(.975*(repeats-1))]


def coarse_category(category):
    return 'Service' if category=='Staff' else category


def map_semeval_category(category):
    entity, attribute = category.split('#',1)
    if attribute=='PRICES' or entity=='LOCATION':
        return None
    if entity=='HOTEL':
        return 'Cleanliness' if attribute=='CLEANLINESS' else None
    return {'ROOMS':'Room','FACILITIES':'Facilities','ROOMS_AMENITIES':'Facilities',
            'SERVICE':'Service','FOOD_DRINKS':'Food'}.get(entity)
