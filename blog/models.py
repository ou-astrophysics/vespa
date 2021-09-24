from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from markdown import markdown


class Category(models.Model):
    name = models.CharField(max_length=250, null=False, blank=False)
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ('name',)

    def __str__(self):
        return self.name


class Article(models.Model):
    title = models.CharField(max_length=250, null=False, blank=False)
    slug = models.SlugField(unique_for_date="date_created")
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='articles', editable=False)
    body = models.TextField()

    categories = models.ManyToManyField(Category)

    date_created = models.DateTimeField(auto_now_add=True)
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-date_created',)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_article_detail', kwargs={
            'year': self.date_created.strftime("%Y"),
            'month': self.date_created.strftime("%b"), 
            'day': self.date_created.strftime("%d"),
            'slug': self.slug,
        })

    @property
    def body_html(self):
        return markdown(self.body)

    @property
    def next(self):
        return Article.objects.filter(
                date_created__gt=self.date_created,
        ).order_by('date_created')

    @property
    def prev(self):
        return Article.objects.filter(
                date_created__lt=self.date_created,
        ).order_by('-date_created')