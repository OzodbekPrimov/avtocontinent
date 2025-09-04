from django.urls import path
from . import api_views

urlpatterns = [
    path('regions/', api_views.get_delivery_regions, name='api_delivery_regions'),
    path('regions/<int:region_id>/branches/', api_views.get_region_branches, name='api_region_branches'),
    path('branches/<int:branch_id>/details/', api_views.get_branch_details, name='api_branch_details'),
]


