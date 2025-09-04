"""
SEO utilities for Avtokontinent website
Helps optimize search visibility for both 'avtokontinent' and 'автоконтинент'
"""




def get_seo_keywords():
    """Return comprehensive list of SEO keywords for the brand"""
    return [
        # Primary brand keywords
        'avtokontinent',
        'автоконтинент', 
        'avtokontinent.uz',
        'автоконтинент.уз',
        
        # Brand variations
        'avto kontinent',
        'авто континент',
        'avtokontinent uz',
        'автоконтинент уз',
        
        # Location-based brand searches
        'avtokontinent uzbekistan',
        'автоконтинент узбекистан',
        'avtokontinent toshkent',
        'автоконтинент ташкент',
        'avtokontinent zarafshon',
        'автоконтинент зарафшан',
        'avtokontinent navoiy',
        'автоконтинент навои',
        
        # Service-based brand searches
        'avtokontinent online',
        'автоконтинент онлайн',
        'avtokontinent do\'kon',
        'автоконтинент магазин',
        'avtokontinent katalog',
        'автоконтинент каталог',
        'avtokontinent sotib olish',
        'автоконтинент купить',
        'avtokontinent narxlar',
        'автоконтинент цены',
        'avtokontinent yetkazib berish',
        'автоконтинент доставка',
        
        # Quality indicators with brand
        'avtokontinent original',
        'автоконтинент оригинальные',
        'avtokontinent sifatli',
        'автоконтинент качественные',
        'avtokontinent ishonchli',
        'автоконтинент надежные',
        'avtokontinent arzon',
        'автоконтинент дешевые',
        'avtokontinent tezkor',
        'автоконтинент быстрые',
        
        # Business keywords in Uzbek
        'avtomobil ehtiyot qismlar',
        'avtomobil qismlar',
        'auto parts uzbekistan',
        'vakum nasos',
        'babina',
        'tormoz qismlari',
        'avtomobil do\'koni',
        'original qismlar',
        'ehtiyot qismlar sotib olish',
        
        # Business keywords in Russian
        'автозапчасти узбекистан',
        'автозапчасти ташкент',
        'вакуумный насос',
        'катушка зажигания',
        'тормозные детали',
        'магазин автозапчастей',
        'оригинальные запчасти',
        'купить автозапчасти',
        
        # Location keywords
        'toshkent avtomobil qismlar',
        'ташкент автозапчасти',
        'uzbekistan auto parts',
        'zarafshon avtomobil',
        'зарафшан автозапчасти',
        'samarqand avtomobil qismlar',
        'самарканд автозапчасти',
        'buxoro avtomobil qismlar',
        'бухара автозапчасти',
        'farg\'ona avtomobil qismlar',
        'фергана автозапчасти',
        'andijon avtomobil qismlar',
        'андижан автозапчасти',
        
        # Car brand combinations
        'toyota qismlar avtokontinent',
        'hyundai qismlar avtokontinent',
        'chevrolet qismlar avtokontinent',
        'kia qismlar avtokontinent',
        'daewoo qismlar avtokontinent',
        'тойота запчасти автоконтинент',
        'хендай запчасти автоконтинент',
        'шевроле запчасти автоконтинент',
        'киа запчасти автоконтинент',
        'дэу запчасти автоконтинент'
    ]

def get_meta_description(language='uz'):
    """Get optimized meta description for different languages"""
    descriptions = {
        'uz': "Avtokontinent.uz (Автоконтинент.уз) - O'zbekistondagi eng yaxshi avtomobil ehtiyot qismlari do'koni. Barcha brendlar uchun original qismlar: vakum nasos, babina, tormoz qismlari. Toshkent, Samarqand, Buxoro bo'ylab tezkor yetkazib berish.",
        'ru': "Автоконтинент.уз (Avtokontinent.uz) - Лучший магазин автозапчастей в Узбекистане. Оригинальные запчасти для всех марок: вакуумный насос, катушка, тормозные детали. Быстрая доставка по Ташкенту, Самарканду, Бухаре.",
        'cyrl': "Автоконтинент.уз (Avtokontinent.uz) - Ўзбекистондаги энг яхши автомобил эҳтиёт қисмлари дўкони. Барча брендлар учун оригинал қисмлар: вакум насос, бобина, тормоз қисмлари."
    }
    return descriptions.get(language, descriptions['uz'])

def get_page_title(page_type='home', language='uz'):
    """Get optimized page titles for different pages and languages"""
    titles = {
        'home': {
            'uz': "Avtokontinent.uz (Автоконтинент.уз) - Avtomobil Ehtiyot Qismlari | Auto Parts Uzbekistan",
            'ru': "Автоконтинент.уз (Avtokontinent.uz) - Автозапчасти Узбекистан | Магазин Автозапчастей",
            'cyrl': "Автоконтинент.уз (Avtokontinent.uz) - Автомобил Эҳтиёт Қисмлари | Авто Қисмлар"
        },
        'products': {
            'uz': "Avtomobil Qismlar - Avtokontinent.uz | Автозапчасти - Автоконтинент.уз",
            'ru': "Автозапчасти - Автоконтинент.уз | Avtomobil Qismlar - Avtokontinent.uz",
            'cyrl': "Автомобил Қисмлар - Автоконтинент.уз | Avtokontinent.uz"
        },
        'brands': {
            'uz': "Avtomobil Brendlar - Avtokontinent.uz | Марки Авто - Автоконтинент.уз",
            'ru': "Марки Автомобилей - Автоконтинент.уз | Avtomobil Brendlar - Avtokontinent.uz",
            'cyrl': "Автомобил Брендлар - Автоконтинент.уз | Avtokontinent.uz"
        }
    }
    return titles.get(page_type, titles['home']).get(language, titles['home']['uz'])

def get_structured_data_keywords():
    """Return structured data keywords for JSON-LD"""
    return "avtokontinent, автоконтинент, avtomobil qismlar, автозапчасти, auto parts, ehtiyot qismlar, vakum nasos, вакуумный насос, babina, катушка, tormoz qismlari, тормозные детали, O'zbekiston, Узбекистан, Toshkent, Ташкент"
