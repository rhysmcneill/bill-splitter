# Fetches the business slug
def current_business(request):
    business = getattr(request, 'business', None)
    if business and getattr(business, 'slug', None):
        return {'current_business': business}
    return {'current_business': None}
