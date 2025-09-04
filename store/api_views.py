from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .utils import get_regions, get_branches_by_region, get_branch_by_id


@require_http_methods(["GET"])
def get_delivery_regions(request):
    """Get all delivery regions from CSV"""
    regions = get_regions()
    return JsonResponse({
        'success': True,
        'regions': regions
    })


@require_http_methods(["GET"])
def get_region_branches(request, region_id):
    """Get all branches for a specific region from CSV"""
    try:
        regions = get_regions()
        if region_id > len(regions):
            return JsonResponse({
                'success': False,
                'error': 'Region not found'
            }, status=404)

        region_name = regions[region_id - 1]['name']  # region_id is 1-based
        branches = get_branches_by_region(region_name)

        # Format branches for frontend
        formatted_branches = []
        for branch in branches:
            formatted_branches.append({
                'id': branch['id'],
                'name': branch['name'],
                'city_district': branch['city_district'],
                'address': branch['address'],
                'landmark': branch['landmark']
            })

        return JsonResponse({
            'success': True,
            'region_name': region_name,
            'branches': formatted_branches
        })
    except (IndexError, KeyError):
        return JsonResponse({
            'success': False,
            'error': 'Region not found'
        }, status=404)


@require_http_methods(["GET"])
def get_branch_details(request, branch_id):
    """Get detailed information about a specific branch from CSV"""
    branch = get_branch_by_id(branch_id)

    if not branch:
        return JsonResponse({
            'success': False,
            'error': 'Branch not found'
        }, status=404)

    return JsonResponse({
        'success': True,
        'branch': branch
    })