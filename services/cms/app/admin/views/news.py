"""sqladmin ModelView for News."""

from sqladmin import ModelView

from app.models.news import News


class NewsAdmin(ModelView, model=News):
    column_list = [
        News.id,
        News.title,
        News.slug,
        News.category,
        News.published,
        News.published_at,
        News.created_at,
    ]
    column_searchable_list = [News.title, News.slug]
    column_sortable_list = [
        News.id,
        News.title,
        News.published,
        News.published_at,
        News.created_at,
    ]
    column_default_sort = ("created_at", True)
    page_size = 25
    name = "News"
    name_plural = "News"
    icon = "fa-solid fa-newspaper"
