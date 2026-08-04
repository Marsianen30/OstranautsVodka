import sys, json, io
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

codes = ['BCER','EJDR','HQCH','JATL','JFTS','MHNG','MSUZ','MTRS','MVOL','SVIR']
G = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/interactions/interactions_crime_{}.json'
out = io.open('script/tmp_ic_all.txt', 'w', encoding='utf-8')
for code in codes:
    g = load_json_file(G.format(code))
    out.write(f'===== {code} ({len(g)}) =====\n')
    for e in g:
        out.write(f"{e['strName']} | TITLE: {e.get('strTitle')!r} | DESC: {e.get('strDesc')!r}\n")
    out.write('\n')
out.close()
print('done')
