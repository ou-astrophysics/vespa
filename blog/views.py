from typing import List
from django.shortcuts import render

from django.views.generic.list import ListView

from blog.models import Article, Category


class CategoryListView(ListView):
    model = Article
    template_name = 'blog/article_category.html'

    def get_queryset(self):
        return self.model.objects.filter(categories__slug=self.kwargs['category'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = Category.objects.get(slug=self.kwargs['category'])
        return context