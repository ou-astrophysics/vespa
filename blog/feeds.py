from django.contrib.syndication.views import Feed
from blog.models import Article

class ArticlesFeed(Feed):
    title = "SuperWASP Blog"
    link = "/blog/"
    description = "The SuperWASP Blog"

    def items(self):
        return Article.objects.order_by('-date_created')[:100]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.body_html