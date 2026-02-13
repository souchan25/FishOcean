from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .forms import BuyerRegistrationForm, SellerRegistrationForm
from store.models import Product, Category, ProductImage
from orders.models import Order

def register_buyer(request):
    if request.method == 'POST':
        form = BuyerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('store:product_list')
    else:
        form = BuyerRegistrationForm()
    return render(request, 'users/register_buyer.html', {'form': form})

def register_seller(request):
    if request.method == 'POST':
        form = SellerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('users:seller_dashboard')
    else:
        form = SellerRegistrationForm()
    return render(request, 'users/register_seller.html', {'form': form})

# --- SELLER DASHBOARD VIEWS ---

def seller_required(user):
    return user.is_authenticated and user.is_seller

@login_required
@user_passes_test(seller_required)
def seller_dashboard(request):
    seller_profile = request.user.seller_profile
    
    # Overview
    products = Product.objects.filter(seller=request.user)
    incoming_orders = Order.objects.filter(seller=request.user).order_by('-created_at')
    
    # Analytics
    now = timezone.now()
    today = now.date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Sales metrics
    total_revenue = Order.objects.filter(
        seller=request.user, 
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    today_revenue = Order.objects.filter(
        seller=request.user,
        created_at__date=today,
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    weekly_revenue = Order.objects.filter(
        seller=request.user,
        created_at__date__gte=week_ago,
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    monthly_revenue = Order.objects.filter(
        seller=request.user,
        created_at__date__gte=month_ago,
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    today_orders = Order.objects.filter(
        seller=request.user,
        created_at__date=today,
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).count()

    weekly_orders = Order.objects.filter(
        seller=request.user,
        created_at__date__gte=week_ago,
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).count()

    monthly_orders = Order.objects.filter(
        seller=request.user,
        created_at__date__gte=month_ago,
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).count()
    
    # Order counts
    total_orders = Order.objects.filter(seller=request.user).count()
    pending_orders = Order.objects.filter(seller=request.user, status='pending').count()
    completed_orders = Order.objects.filter(seller=request.user, status='completed').count()
    
    # Low stock products (< 5kg)
    LOW_STOCK_THRESHOLD = 5
    low_stock_products = products.filter(
        stocks_kg__lt=LOW_STOCK_THRESHOLD, 
        stocks_kg__gt=0,
        is_live=True
    )
    
    # Best selling products (by quantity sold)
    from orders.models import OrderItem
    best_sellers = OrderItem.objects.filter(
        order__seller=request.user,
        order__status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).values('product__name', 'product__id').annotate(
        total_qty=Sum('quantity_kg'),
        total_revenue=Sum('price_at_purchase')
    ).order_by('-total_qty')[:5]
    
    # Customer insights
    unique_customers = Order.objects.filter(
        seller=request.user,
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).values('buyer').distinct().count()
    
    avg_order_value = Order.objects.filter(
        seller=request.user,
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).aggregate(avg=Avg('total_amount'))['avg'] or Decimal('0')
    
    # Recent reviews
    from store.models import Review
    recent_reviews = Review.objects.filter(product__seller=request.user).order_by('-created_at')[:5]
    
    context = {
        'seller': seller_profile,
        'products': products,
        'orders': incoming_orders[:10],  # Show recent 10
        'categories': Category.objects.all(),
        
        # Analytics
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'weekly_revenue': weekly_revenue,
        'monthly_revenue': monthly_revenue,
        'today_orders': today_orders,
        'weekly_orders': weekly_orders,
        'monthly_orders': monthly_orders,
        'report_today': today,
        'report_week_start': week_ago,
        'report_month_start': month_ago,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'low_stock_products': low_stock_products,
        'best_sellers': best_sellers,
        'unique_customers': unique_customers,
        'avg_order_value': avg_order_value,
        'recent_reviews': recent_reviews,
    }
    return render(request, 'users/seller_dashboard.html', context)

@login_required
@user_passes_test(seller_required)
def add_product(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        stocks = request.POST.get('stocks')
        category_id = request.POST.get('category')
        image = request.FILES.get('image')
        description = request.POST.get('description', '')
        
        if not category_id:
             messages.error(request, "Please select a category.")
             return redirect('users:seller_dashboard')

        category = get_object_or_404(Category, id=category_id)

        try:
            price = Decimal(price)
            stocks = Decimal(stocks)
        except (TypeError, ValueError):
            messages.error(request, "Please enter valid numbers for price and stocks.")
            return redirect('users:seller_dashboard')
        
        product = Product.objects.create(
            seller=request.user,
            name=name,
            description=description,
            price_per_kg=price,
            stocks_kg=stocks,
            category=category,
            image=image,
            is_live=True
        )
        for img in request.FILES.getlist('images'):
            ProductImage.objects.create(product=product, image=img)
        messages.success(request, "Product added successfully!")
    return redirect('users:seller_dashboard')

@login_required
@user_passes_test(seller_required)
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    product.is_live = not product.is_live
    product.save()
    status = "Active" if product.is_live else "Inactive"
    messages.info(request, f"Product {product.name} is now {status}")
    return redirect('users:seller_dashboard')

@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.phone_number = request.POST.get('phone_number')
        user.save()
        
        if user.is_seller:
            profile = user.seller_profile
            profile.shop_name = request.POST.get('shop_name')
            profile.municipality = request.POST.get('municipality')
            profile.address = request.POST.get('address')
            
            if request.FILES.get('gcash_qr'):
                 profile.gcash_qr_image = request.FILES.get('gcash_qr')
            if request.FILES.get('maya_qr'):
                 profile.maya_qr_image = request.FILES.get('maya_qr')
            
            profile.save()
            
        messages.success(request, "Profile updated successfully.")
        return redirect('users:edit_profile')
        
    return render(request, 'users/edit_profile.html')

