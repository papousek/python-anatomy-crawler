from .crawler import load_transformed_triples
from collections import defaultdict
from copy import deepcopy
from spiderpig import spiderpig
import pandas


def extract_relation_triples(ontology):
    result = []
    subclasses = defaultdict(list)
    relation_froms = defaultdict(set)
    relation_tos = defaultdict(set)
    for term_key, term_data in ontology['terms'].items():
        for relation, relation_data in term_data.get('relations', {}).items():
            for term_id in relation_data:
                term_data_to = None if relation in {
                    'http://purl.org/sig/ont/fma/physical_state',
                    'http://purl.org/sig/ont/fma/has_dimension',
                    'http://purl.org/sig/ont/fma/has_boundary',
                    'http://purl.org/sig/ont/fma/dimension',
                    'http://purl.org/sig/ont/fma/has_direct_number_of_pairs_per_nucleus',
                    'http://purl.org/sig/ont/fma/days_post-fertilization',
                    'http://purl.org/sig/ont/fma/has_inherent_3-D_shape',
                    'http://purl.org/sig/ont/fma/has_direct_ploidy',
                    'http://purl.org/sig/ont/fma/state_of_determination',
                    'http://purl.org/sig/ont/fma/cell_appendage_type',
                    'http://purl.org/sig/ont/fma/polarity',
                    'http://purl.org/sig/ont/fma/has_direct_shape_type',
                    'http://purl.org/sig/ont/fma/has_mass',
                    'http://purl.org/sig/ont/fma/has_direct_cell_layer',
                    'http://purl.org/sig/ont/fma/species',
                } else ontology['terms'][term_id]
                relation_tuple = term_data['info']['http://purl.org/sig/ont/fma/FMAID'][0], relation.replace('http://purl.org/sig/ont/fma/', ''), '' if term_data_to is None else term_data_to['info']['http://purl.org/sig/ont/fma/FMAID'][0]
                relation_froms[term_key].add(relation_tuple)
                relation_tos[term_id].add(relation_tuple)
        for c in term_data.get('info', {}).get('http://www.w3.org/2000/01/rdf-schema#subClassOf', []):
            if 'relations' in ontology['terms'].get(c, {}):
                subclasses[term_key].append(c)

    changed = True
    while changed:
        prev_length = sum([len(vs) for vs in relation_froms.values()])
        # print(prev_length)
        changed = False
        for term_id, scs in subclasses.items():
            term_data = ontology['terms'][term_id]
            term_fmaid = term_data['info']['http://purl.org/sig/ont/fma/FMAID'][0]
            for subclass in scs:
                for _, relation, fmaid_to in relation_froms[subclass]:
                    relation_tuple = term_fmaid, relation, fmaid_to
                    relation_froms[term_id].add(relation_tuple)
                    relation_tos['http://purl.org/sig/ont/fma/fma{}'.format(fmaid_to)].add(relation_tuple)
                for fmaid_from, relation, _ in relation_tos[subclass]:
                    relation_tuple = fmaid_from, relation, term_fmaid
                    relation_tos[term_id].add(relation_tuple)
                    relation_froms['http://purl.org/sig/ont/fma/fma{}'.format(fmaid_from)].add(relation_tuple)
        after_length = sum([len(vs) for vs in relation_froms.values()])
        changed = prev_length != after_length

    result = []
    for term_id, relations in relation_froms.items():
        if term_id not in ontology['terms']:
            continue
        for fmaid_from, relation, fmaid_to in relations:
            term_data = ontology['terms'][term_id]
            term_to_id = 'http://purl.org/sig/ont/fma/fma{}'.format(fmaid_to)
            if relation in {
                'physical_state',
                'has_dimension',
                'has_boundary',
                'dimension',
                'has_direct_number_of_pairs_per_nucleus',
                'days_post-fertilization',
                'has_inherent_3-D_shape',
                'has_direct_ploidy',
                'state_of_determination',
                'cell_appendage_type',
                'polarity',
                'has_direct_shape_type',
                'has_mass',
                'has_direct_cell_layer',
                'species',
            }:
                term_data_to = None
            else:
                if term_to_id not in ontology['terms']:
                    continue
                term_data_to = ontology['terms'][term_to_id]
            result.append({
                'fmaid_from': fmaid_from,
                'fmaid_to': fmaid_to,
                'relation': relation,
                'name_from': term_data['info']['http://www.w3.org/2000/01/rdf-schema#label'][0],
                'taid_from': term_data['info'].get('http://purl.org/sig/ont/fma/TA_ID', [''])[0],
                'name_to': term_to_id if term_data_to is None else term_data_to['info']['http://www.w3.org/2000/01/rdf-schema#label'][0],
                'taid_to': '' if term_data_to is None else term_data_to['info'].get('http://purl.org/sig/ont/fma/TA_ID', [''])[0],
            })
    result = pandas.DataFrame(result)
    result['fmaid_from'] = result['fmaid_from'].astype(str)
    result['fmaid_to'] = result['fmaid_to'].astype(str)

    return result.drop_duplicates(['fmaid_from', 'fmaid_to', 'relation'])


@spiderpig()
def load_ontology(taids_only=True):
    ontology = deepcopy(load_raw_ontology())
    if taids_only:
        to_remove = {t_id for t_id, t_data in ontology['terms'].items() if 'http://purl.org/sig/ont/fma/TA_ID' not in t_data['info']}
        ontology['terms'] = {t_id: t_data for t_id, t_data in ontology['terms'].items() if t_id not in to_remove}
        for t_data in ontology['terms'].values():
            for rel_type in ['info', 'relations']:
                for rel_name in t_data.get(rel_type, {}).keys():
                    t_data[rel_type][rel_name] = list(set(t_data[rel_type][rel_name]) - to_remove)
                if rel_type in t_data:
                    t_data[rel_type] = {rel_name: rel_data for rel_name, rel_data in t_data[rel_type].items() if len(rel_data) > 0}
    return {
        'terms': ontology['terms'],
        'relation-names': sorted({rel for data in ontology['terms'].values() for rel in data.get('relations', {}).keys()}),
        'info-names': sorted({rel for data in ontology['terms'].values() for rel in data['info'].keys()}),
    }


@spiderpig()
def load_terminology():
    result = []
    for term, term_data in load_ontology()['terms'].items():
        info_data = term_data['info']
        result.append({
            'FMA': term.replace('http://purl.org/sig/ont/fma/', '').upper(),
            'TA': info_data.get('http://purl.org/sig/ont/fma/TA_ID', [None])[0],
            'RADLEX': info_data.get('http://purl.org/sig/ont/fma/RadLex_ID', [None])[0],
            'english_name': info_data.get('http://purl.org/sig/ont/fma/preferred_name', [None])[0],
            'latin_name': names_list(info_data.get('http://purl.org/sig/ont/fma/non-English_equivalent_Latin', None))
        })
    return pandas.DataFrame(result)


@spiderpig()
def load_raw_ontology():
    to_export = defaultdict(lambda: defaultdict(set))
    for t in [t for t in load_transformed_triples() if t[0].startswith('http://purl.org/sig/ont/fma/fma')]:
        if t[1].startswith('transformed/'):
            to_export[t[0]]['relations'].add((t[1].replace('transformed/', ''), t[2]))
        else:
            to_export[t[0]]['info'].add((t[1], t[2]))
    for term, data in to_export.items():
        if 'relations' in data:
            orig = data['relations']
            data['relations'] = defaultdict(list)
            for name, value in orig:
                data['relations'][name].append(value)
        orig = data['info']
        data['info'] = defaultdict(list)
        for name, value in orig:
            data['info'][name].append(value)

    relation_names = set([k for term in to_export.values() for k in term.get('relations', {}).keys()])
    info_names = set([k for term in to_export.values() for k in term.get('info', {}).keys()])
    return {
        'terms': {t_id: {key: values for key, values in t_values.items()} for t_id, t_values in to_export.items()},
        'relation-names': sorted(relation_names),
        'info-names': sorted(info_names),
    }


def names_list(val):
    if val is None:
        return None
    return '|'.join(val)
