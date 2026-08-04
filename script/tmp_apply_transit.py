# -*- coding: utf-8 -*-
import sys, json, io, copy
sys.path.insert(0, 'script/ostranauts_tools')
from json_utils import load_json_file

G = 'D:/SteamLibrary/steamapps/common/Ostranauts/Ostranauts_Data/StreamingAssets/data/transit/transit.json'
OUT = 'ostranautsRuNss/data/transit/transit.json'

TR = {
    'Arsia Mons Landing Zone': 'Посадочная зона Арсия Монс',
    'Arsia Mons Space Elevator': 'Космический лифт Арсия Монс',
    'Atlantis Landing Zone': 'Посадочная зона Атлантис',
    'Azikiwe Commercial Station': 'Коммерческая станция Азикиве',
    'Azikiwe Estates Transfer Station': 'Пересадочная станция «Азикиве Эстейтс»',
    'Capitol District': 'Капитолийский район',
    'Cloudbreak Port Level': 'Портовый уровень Клаудбрейка',
    'Customs and Immigration (Invite Only)': 'Таможня и иммиграция (только по приглашению)',
    'Data & Command Level': 'Уровень данных и командования',
    'Duanqiao Lounge 断桥酒廊': 'Лаунж «Дуаньцяо» 断桥酒廊',
    'Habitation Level': 'Жилой уровень',
    'Heifei District': 'Район Хэйфэй',
    'Lemuria Terminal': 'Терминал «Лемурия»',
    'Long Beach Terminal': 'Терминал «Лонг-Бич»',
    'MVOL_Lab': 'MVOL_Lab',
    'Maintenance Access': 'Технический доступ',
    'Noctis Regional Processing Facility': 'Региональный обрабатывающий комплекс «Ноктис»',
    'OKLG Sec': 'Служба безопасности OKLG',
    'Old Emporium Station': 'Станция «Старый Эмпориум»',
    'Port Azikiwe Station': 'Портовая станция Азикиве',
    'Port: Panmen 盘门': 'Порт: Паньмэнь 盘门',
    'Port: Qiantangmen 钱塘门': 'Порт: Цяньтанмэнь 钱塘门',
    'Porto Nuevo Terminal': 'Терминал «Порто-Нуэво»',
    'Porto do Encantado': 'Порто-ду-Энкантаду',
    'Private Residence': 'Частная резиденция',
    'Renbao Pavilion Seven 仁宝七号馆': 'Павильон Жэньбао, номер семь 仁宝七号馆',
    'Residences': 'Резиденции',
    'San Diego Mall': 'Торговый центр Сан-Диего',
    'Security Offices': 'Офисы безопасности',
    'Sol Vermelho Lounge': 'Лаунж «Sol Vermelho»',
    'Sol Vermelho: Green Room': 'Sol Vermelho: Зелёная комната',
    'Surface Access (Legal Residents Only)': 'Выход на поверхность (только для легальных резидентов)',
    'Tharsis Landing': 'Тарсис-Лэндинг',
    'The Labyrinth': 'Лабиринт',
    'Titan Shipyards': 'Верфи Титана',
    'Venus Orbital: Auxiliary': 'Венерианская орбитальная станция: вспомогательный модуль',
    'Venus Orbital: Habitation': 'Венерианская орбитальная станция: жилой модуль',
    'Venus Orbital: Port and Cargo': 'Венерианская орбитальная станция: порт и грузовой модуль',
}

d = load_json_file(G)
count = 0
for e in d:
    for c in e.get('aConnections', []):
        if 'strLabelNameOptional' in c:
            orig = c['strLabelNameOptional']
            c['strLabelNameOptional'] = TR[orig]
            count += 1

json.dump(d, io.open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('translated_occurrences', count, 'unique', len(TR))
