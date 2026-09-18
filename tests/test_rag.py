from copy import deepcopy
import pytest
from aquarium.catalog import load_catalog
from aquarium.rag import compatibility, evaluate


def animal(id='a',**facts):
    base={'ph':[6,8],'temperature':[24,28],'water':['fresh'],'temperament':'peaceful','diet':'omnivore','size_cm':5};base.update(facts)
    return {'id':id,'name':id,'url':'https://example.com/'+id,'kind':'fish','facts':base,'issues':[]}

def test_common_ranges():
    result=compatibility([animal(),animal('b',ph=[7,9])])
    assert result['status']=='compatible';assert result['ranges']['ph']['min']==7

def test_no_overlap():
    result=compatibility([animal(),animal('b',temperature=[16,20])])
    assert result['status']=='incompatible';assert result['warnings'][0]['code']=='disjoint_temperature'

def test_global_intersection_and_boundary():
    assert compatibility([animal(),animal('b',ph=[8,9])])['ranges']['ph']['overlap']
    assert compatibility([animal(),animal('b',ph=[7,9]),animal('c',ph=[8.1,9])])['status']=='incompatible'

def test_water_and_temperament():
    assert compatibility([animal(),animal('b',water=['marine'])])['status']=='incompatible'
    assert compatibility([animal(),animal('b',temperament='risk')])['status']=='uncertain'

def test_missing_is_never_green():
    assert compatibility([animal(water=None)])['status']=='uncertain'
    assert compatibility([animal(temperature=None)])['ranges']=={'ph':{'min':6,'max':8,'complete':True,'overlap':True}}

def test_predation_and_plant_grazing():
    result=compatibility([animal(size_cm=30),animal('b',size_cm=2)])
    assert any(w['code']=='predation_risk' for w in result['warnings'])
    plant=animal('plant');plant['kind']='plant'
    assert any(w['code']=='plant_grazing' for w in compatibility([animal(diet='herbivore'),plant])['warnings'])

def test_scraping_error_quarantined():
    catalog=load_catalog();goby=catalog[0]
    assert goby['facts']['temperature'] is None and goby['facts']['water'] is None
    assert goby['facts']['ph'] is None  # A point recommendation is not a tolerance interval.
    assert goby['raw']['temp_min_c']==7
    assert sum(i['eligible'] for i in catalog)==603

def test_selected_ids_always_retrieved():
    class Index:
        def retrieve(self,ids):assert ids==['a','b'];return [animal(),animal('b',ph=[9,10])]
        def search(self,query,k,ids):return []
    assert evaluate(Index(),['a','b','a'])['status']=='incompatible'
