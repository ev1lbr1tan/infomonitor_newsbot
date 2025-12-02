import feedparser
import requests
from datetime import datetime, timedelta
import re
from typing import List, Dict, Optional

class NewsCollector:
    """Класс для сбора новостей из RSS источников"""
    
    def __init__(self):
        self.news_sources = {
            # Политика
            'ria': {'url': 'https://ria.ru/export/rss2/news/index.xml', 'categories': ['politics']},
            'tass': {'url': 'https://tass.ru/rss/v2.xml', 'categories': ['politics']},
            'izvestia': {'url': 'https://iz.ru/xml/rss/all.xml', 'categories': ['politics']},
            'gazeta': {'url': 'https://www.gazeta.ru/export/rss/lenta.xml', 'categories': ['politics']},
            'rt': {'url': 'https://russian.rt.com/rss', 'categories': ['politics', 'entertainment']},
            'interfax': {'url': 'https://www.interfax.ru/rss.asp', 'categories': ['politics', 'business']},
            'regnum': {'url': 'https://regnum.ru/rss', 'categories': ['politics']},
            'ng': {'url': 'https://www.ng.ru/rss/', 'categories': ['politics']},

            # Бизнес и технологии
            'vedomosti': {'url': 'https://www.vedomosti.ru/rss/news.xml', 'categories': ['business', 'politics']},
            'rbc': {'url': 'https://rssexport.rbc.ru/news/20/5001001/full.rss', 'categories': ['business', 'tech']},
            'kommersant': {'url': 'https://www.kommersant.ru/rss', 'categories': ['business', 'politics']},
            'forklog': {'url': 'https://forklog.com/news/feed/', 'categories': ['tech']},
            'bits_media': {'url': 'https://bits.media/rss/', 'categories': ['tech']},
            'habr': {'url': 'https://habr.com/ru/rss/hubs/all/', 'categories': ['tech']},

            # Развлечения (Кино и Видеоигры)
            'lenta': {'url': 'https://lenta.ru/rss/news', 'categories': ['entertainment', 'politics']},
            'afisha': {'url': 'https://www.afisha.ru/rss/news/', 'categories': ['entertainment']},
            'kanobu': {'url': 'https://kanobu.ru/rss/', 'categories': ['entertainment']},
            'igromania': {'url': 'https://www.igromania.ru/rss/news/', 'categories': ['entertainment']},
            'stopgame': {'url': 'https://stopgame.ru/rss/news.xml', 'categories': ['entertainment']},
            'gamer': {'url': 'https://www.gamer.ru/rss/news', 'categories': ['entertainment']},
            'dtf': {'url': 'https://dtf.ru/rss/all', 'categories': ['entertainment', 'tech']}
        }

        self.categories = {
            'politics': 'Политика',
            'entertainment': 'Кино и Видеоигры',
            'tech': 'Технологии',
            'business': 'Бизнес'
        }
    
    def clean_text(self, text: str, max_length: int = 200) -> str:
        """Очистка текста от HTML тегов и ограничение длины"""
        # Удаление HTML тегов
        clean = re.sub('<[^<]+?>', '', text)
        # Удаление лишних пробелов
        clean = re.sub(r'\s+', ' ', clean).strip()
        # Ограничение длины
        if len(clean) > max_length:
            clean = clean[:max_length].rsplit(' ', 1)[0] + '...'
        return clean
    
    def get_latest_news(self, limit: int = 10, category: Optional[str] = None) -> List[Dict]:
        """Получение последних новостей из всех источников или по категории"""
        all_news = []

        for source_name, source_data in self.news_sources.items():
            # Если указана категория, проверяем, относится ли источник к ней
            if category and category not in source_data['categories']:
                continue

            try:
                feed = feedparser.parse(source_data['url'])
                if feed.bozo == 0 and feed.entries:
                    for entry in feed.entries[:3]:  # Берем по 3 новости с каждого источника
                        news_item = {
                            'title': self.clean_text(entry.get('title', 'Без заголовка')),
                            'description': self.clean_text(entry.get('description', 'Описание отсутствует')),
                            'link': entry.get('link', ''),
                            'source': source_name.upper(),
                            'published': entry.get('published', ''),
                            'published_parsed': entry.get('published_parsed', None)
                        }
                        all_news.append(news_item)
            except Exception as e:
                print(f"Ошибка при получении новостей из {source_name}: {e}")

        # Сортируем по дате публикации (если есть)
        all_news.sort(key=lambda x: x.get('published_parsed') or (0, 0, 0, 0, 0, 0), reverse=True)

        return all_news[:limit]
    
    def format_news_message(self, news_list: List[Dict]) -> str:
        """Форматирование новостей для отправки в Telegram"""
        if not news_list:
            return "😔 К сожалению, не удалось получить новости. Попробуйте позже."

        message = "📰 *ТОП НОВОСТИ*\n\n"

        for i, news in enumerate(news_list, 1):
            message += f"*{i}. {news['title']}*\n"
            message += f"📝 {news['description']}\n"
            message += f"🔗 [Читать полностью]({news['link']})\n"
            message += f"📰 Источник: {news['source']}\n"
            if news['published']:
                message += f"🕐 {news['published']}\n"
            message += "\n" + "─" * 50 + "\n\n"

        message += f"📊 Показано новостей: {len(news_list)}"
        return message

    def format_single_news(self, news: Dict, index: int, total: int) -> str:
        """Форматирование одной новости для отображения с навигацией"""
        message = f"📰 *{news['title']}*\n\n"
        message += f"📝 {news['description']}\n"
        message += f"🔗 [Читать полностью]({news['link']})\n"
        message += f"📰 Источник: {news['source']}\n"
        if news['published']:
            message += f"🕐 {news['published']}\n"
        message += f"\n📊 Новость {index + 1} из {total}"
        return message