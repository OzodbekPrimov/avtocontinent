from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.csrf import csrf_exempt
from ..utils.address_utils import get_branches, get_regions

@require_GET
def get_regions_list(request):
    """API endpoint to get list of regions"""
    regions = get_regions()
    return JsonResponse({'regions': regions})

@require_GET
def get_branches_by_region(request, region):
    """API endpoint to get branches by region"""
    branches = get_branches(region=region)
    # Simplify the response data
    branches_data = [{
        'id': branch['id'],
        'name': branch['name'],
        'address': branch['address'],
        'landmark': branch['landmark'],
        'phone': branch['phone'],
        'delivery_time': branch['delivery_time']
    } for branch in branches]
    return JsonResponse({'branches': branches_data})
