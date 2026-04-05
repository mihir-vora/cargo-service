from django.urls import path

from allocation.views import InputView, OptimizeView, ResultsView

urlpatterns = [
    path("input", InputView.as_view()),
    path("optimize", OptimizeView.as_view()),
    path("results", ResultsView.as_view()),
]
