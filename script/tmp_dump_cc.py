import sys, json
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file
codes = ['EJDR','HQCH','JATL','JFTS','MHNG','MSUZ','MTRS','MVOL','SVIR']
for c in codes:
    g = load_json_file(f'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/conditions/conditions_crime_{c}.json')
    print('====', c, len(g))
    for e in g:
        print(e['strName'], '|', e.get('strNameFriendly'), '|', e.get('strDesc'))
