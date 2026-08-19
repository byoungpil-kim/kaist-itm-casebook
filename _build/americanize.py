# -*- coding: utf-8 -*-
"""영문판 철자 미국식 통일.

번역 본문이 영국식(-ise, centre, programme...)으로 작성되어 meta_en.json의 분류명·제목
(미국식)과 한 페이지 안에서 혼용되던 것을 미국식으로 통일한다. KAIST 공식 영문 표기와
한국 기관 영문 명칭(Defense Acquisition Program Administration 등)이 모두 미국식이다.

주의: 목록 기반 치환만 한다. rise/wise/franchise/expertise류 -ise 어미와
Nutzerorganisation(독일 고유명사), Airbus Skywise는 건드리지 않는다.
"""
import io, re, glob, sys
sys.stdout.reconfigure(encoding='utf-8')

# -is → -iz 어간 (파생형 -e/-es/-ed/-ing/-ation 모두 커버)
STEMS = ['cannibalis', 'capitalis', 'characteris', 'commercialis', 'conceptualis',
         'digitalis', 'epitomis', 'externalis', 'galvanis', 'generalis', 'hospitalis',
         'immortalis', 'informatis', 'internalis', 'localis', 'maximis', 'mechanis',
         'minimis', 'modularis', 'monetis', 'monopolis', 'neutralis', 'operationalis',
         'optimis', 'personalis', 'popularis', 'pressuris', 'prioritis', 'privatis',
         'productis', 'recognis', 'reorganis', 'romanis', 'serialis', 'smartis',
         'socialis', 'specialis', 'stabilis', 'standardis', 'sterilis', 'subsidis',
         'systematis', 'urbanis', 'utilis', 'vaporis', 'visualis', 'volatilis', 'weaponis']
# 완전 단어 치환 (어간 치환이 위험한 것: realistic, emphasis 명사 등)
WORDS = [('realise', 'realize'), ('realised', 'realized'), ('realising', 'realizing'),
         ('realisation', 'realization'), ('emphasise', 'emphasize'), ('emphasised', 'emphasized'),
         ('emphasises', 'emphasizes'), ('analyse', 'analyze'), ('analysed', 'analyzed'),
         ('analyses', 'analyzes'), ('analysing', 'analyzing'), ('practised', 'practiced'),
         ('practising', 'practicing'), ('centre', 'center'), ('centres', 'centers'),
         ('centred', 'centered'), ('programme', 'program'), ('programmes', 'programs'),
         ('defence', 'defense'), ('litre', 'liter'), ('litres', 'liters'),
         ('metre', 'meter'), ('metres', 'meters'), ('labelled', 'labeled'),
         ('cancelled', 'canceled'), ('licence', 'license'), ('licences', 'licenses'),
         ('labour', 'labor'), ('colour', 'color'), ('colours', 'colors'),
         ('behaviour', 'behavior'), ('behaviours', 'behaviors'),
         ('favourable', 'favorable'), ('favourably', 'favorably'),
         ('manoeuvre', 'maneuver'), ('manoeuvres', 'maneuvers'),
         ('manoeuvrability', 'maneuverability'), ('manoeuvrable', 'maneuverable'),
         ('fulfilment', 'fulfillment'), ('catalogue', 'catalog'), ('catalogues', 'catalogs')]


def fix(t):
    for stem in STEMS:
        # Nutzerorganisation 보존을 위해 organis는 단어 경계 시작에서만
        t = re.sub(r'\b' + stem, stem[:-1] + 'z', t)
        t = re.sub(r'\b' + stem[0].upper() + stem[1:], stem[0].upper() + stem[1:-1] + 'z', t)
    # organis: 별도 처리 (Nutzerorganisation은 단어 중간이라 \b로 보호됨)
    t = re.sub(r'\borganis', 'organiz', t)
    t = re.sub(r'\bOrganis', 'Organiz', t)
    for a, b in WORDS:
        t = re.sub(r'\b' + a + r'\b', b, t)
        t = re.sub(r'\b' + a[0].upper() + a[1:] + r'\b', b[0].upper() + b[1:], t)
    return t


if __name__ == '__main__':
    targets = (['en/index.html'] + sorted(glob.glob('en/cases/*.html'))
               + sorted(glob.glob('_build/cases_en/*.html')) + ['_build/build_en.py'])
    n = 0
    for p in targets:
        t = io.open(p, encoding='utf-8').read()
        f = fix(t)
        if f != t:
            io.open(p, 'w', encoding='utf-8', newline='').write(f)
            n += 1
    print(f'{n}개 파일 갱신')
