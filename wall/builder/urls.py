from django.urls import path

from . import views


app_name = 'builder'
urlpatterns = [
    path('profiles/<int:profile>/days/<int:day>/',
         views.ProfileIceAmountPerDay.as_view(), name='amount_per_profile_per_day'),
    path('profiles/<int:profile>/overview/<int:day>/',
         views.ProfilePricePerDay.as_view(), name='price_per_profile_per_day'),
    path('profiles/overview/<int:day>/',
         views.PricePerDay.as_view(), name='price_per_day'),
    path('profiles/overview/', views.PriceTotal.as_view(), name='overall'),
]
