"""Extract the 81 built-in recipes out of Recipes.java into data/builtins.json.

Source of truth: E:\\pmca-lut-rl\\src\\com\\lutlab\\pmca\\Recipes.java
We rebuild the constant table here (instead of importing Java) so the JSON stays
independent of the fork and can be regenerated after any upstream sync.
"""
import json
import os
import re

SRC = r'E:\pmca-lut-rl\src\com\lutlab\pmca\Recipes.java'
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'builtins.json')

# --- constants mirroring Recipes.java -------------------------------------------------
STYLES = {'STD': 1, 'VIVID': 2, 'NEUTRAL': 3, 'PORTRAIT': 4, 'LANDSCAPE': 5, 'MONO': 6,
          'CLEAR': 7, 'DEEP': 8, 'LIGHT': 9, 'SUNSET': 10, 'NIGHT': 11, 'AUTUMN': 12, 'SEPIA': 14}
GROUPS = ['Sony', 'Fuji Sim', 'Fuji Film', 'Kodak', 'Cine', 'Ricoh GR', 'Leica',
          'Hasselblad', 'Canon / Nikon', 'Pana / Olympus', 'Other Stocks', 'Ilford']
GROUP_IDS = {'SONY': 0, 'FSIM': 1, 'FFILM': 2, 'KODAK': 3, 'CINE': 4, 'RICOH': 5,
             'LEICA': 6, 'HASSEL': 7, 'CANIK': 8, 'PANOLY': 9, 'OTHER': 10, 'ILFORD': 11}
SPECIAL = {'AUTO': 1, 'K': 14, 'DRO_OFF': 0, 'DRO_AUTO': 6}


def num(token):
    if token in STYLES:
        return STYLES[token]
    if token in GROUP_IDS:
        return GROUP_IDS[token]
    if token in SPECIAL:
        return SPECIAL[token]
    return int(token)


def main():
    src = open(SRC, encoding='utf-8', errors='replace').read()
    body = src.split('public static final Recipe[] ALL = {', 1)[1].split('};', 1)[0]
    # keep only lines that actually declare a recipe (skip the group comment lines)
    recipes = []
    for m in re.finditer(
            r'new Recipe\(\s*([A-Z_]+)\s*,\s*"([^"]*)"\s*,([^;]*?)\)\s*,?', body, re.S):
        gtok, name, tail = m.group(1), m.group(2), m.group(3)
        args = [a.strip() for a in tail.split(',') if a.strip()]
        v = [num(a) for a in args]
        # ctor defaults: options after the shared 8 args are pe, ev, dro, sub
        while len(v) < 12:
            v.append(0)
        pe, ev, dro, sub = v[8], v[9], v[10], v[11]
        # the 8-arg ctor leaves dro at the DRO_AUTO default, not 0
        if len(args) == 8:
            dro = 6
        recipes.append({
            'group': GROUP_IDS[gtok],
            'group_name': GROUPS[GROUP_IDS[gtok]],
            'name': name,
            'style': v[0], 'sat': v[1], 'con': v[2], 'sharp': v[3],
            'wb_mode': v[4], 'kelvin': v[5], 'ab': v[6], 'gm': v[7],
            'pe': pe, 'ev': ev, 'dro': dro, 'sub': sub,
        })

    for i, r in enumerate(recipes):
        r['index'] = i

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump({'groups': GROUPS, 'recipes': recipes}, f, indent=2, ensure_ascii=False)

    print('wrote', OUT)
    print('recipes:', len(recipes))
    by = {}
    for r in recipes:
        by[r['group_name']] = by.get(r['group_name'], 0) + 1
    for g in GROUPS:
        print('  %-16s %d' % (g, by.get(g, 0)))


if __name__ == '__main__':
    main()
