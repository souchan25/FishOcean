from django.shortcuts import render
from store.models import Product
from users.models import SellerProfile

def landing_page(request):
    """
    Landing page with hero section, featured products, and CTAs
    """
    featured_products = Product.objects.filter(is_live=True, stocks_kg__gt=0).order_by('-created_at')[:6]
    featured_sellers = SellerProfile.objects.filter(user__is_active=True)[:3]
    
    context = {
        'featured_products': featured_products,
        'featured_sellers': featured_sellers,
    }
    return render(request, 'core/landing.html', context)

def about_us(request):
    """
    About Us page with mission and impact
    """
    return render(request, 'core/about.html')

def contact_us(request):
    """
    Contact page
    """
    return render(request, 'core/contact.html')

