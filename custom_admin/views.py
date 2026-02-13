from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import timedelta
from decimal import Decimal

from users.models import User, SellerProfile
from store.models import Product, Category, Review, Wishlist
from orders.models import Order, OrderItem
from notifications.models import Notification
from chat.models import Conversation, Message


def is_admin(user):
    """Check if user is superuser/staff"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


@login_required
@user_passes_test(is_admin)
def dashboard(request):
    """Admin dashboard with key metrics"""
    today = timezone.now().date()
    this_week = today - timedelta(days=7)
    this_month = today - timedelta(days=30)
    
    # User Statistics
    total_users = User.objects.count()
    total_buyers = User.objects.filter(is_buyer=True).count()
    total_sellers = User.objects.filter(is_seller=True).count()
    new_users_today = User.objects.filter(date_joined__date=today).count()
    new_users_week = User.objects.filter(date_joined__date__gte=this_week).count()
    
    # Seller Statistics
    verified_sellers = SellerProfile.objects.filter(is_verified=True).count()
    pending_verification = SellerProfile.objects.filter(is_verified=False).count()
    
    # Product Statistics
    total_products = Product.objects.count()
    live_products = Product.objects.filter(is_live=True).count()
    out_of_stock = Product.objects.filter(stocks_kg__lte=0).count()
    low_stock = Product.objects.filter(stocks_kg__gt=0, stocks_kg__lte=5).count()
    
    # Order Statistics
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='pending').count()
    completed_orders = Order.objects.filter(status='completed').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    
    # Revenue Statistics
    total_revenue = Order.objects.filter(
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    today_revenue = Order.objects.filter(
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed'],
        created_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    week_revenue = Order.objects.filter(
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed'],
        created_at__date__gte=this_week
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    month_revenue = Order.objects.filter(
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed'],
        created_at__date__gte=this_month
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Recent Orders
    recent_orders = Order.objects.select_related('buyer', 'seller').order_by('-created_at')[:10]
    
    # Recent Users
    recent_users = User.objects.order_by('-date_joined')[:10]
    
    # Orders by Status for Chart
    orders_by_status = Order.objects.values('status').annotate(count=Count('id'))
    
    # Daily orders for last 7 days
    daily_orders = Order.objects.filter(
        created_at__date__gte=this_week
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id'),
        revenue=Sum('total_amount')
    ).order_by('date')
    
    # Top Sellers
    top_sellers = User.objects.filter(is_seller=True).annotate(
        order_count=Count('received_orders'),
        total_sales=Sum('received_orders__total_amount')
    ).order_by('-total_sales')[:5]
    
    # Top Products
    top_products = Product.objects.annotate(
        order_count=Count('orderitem'),
        total_sold=Sum('orderitem__quantity_kg')
    ).order_by('-order_count')[:5]
    
    # Category Distribution
    category_stats = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count')
    
    context = {
        # User Stats
        'total_users': total_users,
        'total_buyers': total_buyers,
        'total_sellers': total_sellers,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'verified_sellers': verified_sellers,
        'pending_verification': pending_verification,
        
        # Product Stats
        'total_products': total_products,
        'live_products': live_products,
        'out_of_stock': out_of_stock,
        'low_stock': low_stock,
        
        # Order Stats
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
        'cancelled_orders': cancelled_orders,
        
        # Revenue Stats
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        
        # Recent Data
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        
        # Charts Data
        'orders_by_status': list(orders_by_status),
        'daily_orders': list(daily_orders),
        'top_sellers': top_sellers,
        'top_products': top_products,
        'category_stats': category_stats,
    }
    
    return render(request, 'custom_admin/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def user_list(request):
    """List all users with filtering"""
    users = User.objects.all().order_by('-date_joined')
    
    # Filtering
    user_type = request.GET.get('type')
    if user_type == 'buyers':
        users = users.filter(is_buyer=True)
    elif user_type == 'sellers':
        users = users.filter(is_seller=True)
    elif user_type == 'staff':
        users = users.filter(Q(is_staff=True) | Q(is_superuser=True))
    
    # Search
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    paginator = Paginator(users, 20)
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    context = {
        'users': users,
        'user_type': user_type,
        'search': search or '',
    }
    return render(request, 'custom_admin/user_list.html', context)


@login_required
@user_passes_test(is_admin)
def user_detail(request, user_id):
    """View/Edit user details"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'toggle_active':
            user.is_active = not user.is_active
            user.save()
            status = 'activated' if user.is_active else 'deactivated'
            messages.success(request, f'User {user.username} has been {status}.')
        
        elif action == 'make_staff':
            user.is_staff = True
            user.save()
            messages.success(request, f'{user.username} is now a staff member.')
        
        elif action == 'remove_staff':
            user.is_staff = False
            user.save()
            messages.success(request, f'{user.username} is no longer a staff member.')
        
        return redirect('custom_admin:user_detail', user_id=user_id)
    
    # Get user's orders if buyer
    orders = Order.objects.filter(buyer=user).order_by('-created_at')[:10] if user.is_buyer else None
    
    # Get seller profile and stats if seller
    seller_profile = None
    seller_stats = None
    if user.is_seller:
        try:
            seller_profile = user.seller_profile
            seller_stats = {
                'total_products': Product.objects.filter(seller=user).count(),
                'total_orders': Order.objects.filter(seller=user).count(),
                'total_revenue': Order.objects.filter(
                    seller=user,
                    status__in=['paid', 'preparing', 'out_for_delivery', 'completed']
                ).aggregate(total=Sum('total_amount'))['total'] or 0,
            }
        except SellerProfile.DoesNotExist:
            pass
    
    context = {
        'user_obj': user,
        'orders': orders,
        'seller_profile': seller_profile,
        'seller_stats': seller_stats,
    }
    return render(request, 'custom_admin/user_detail.html', context)


@login_required
@user_passes_test(is_admin)
def seller_list(request):
    """List all sellers with verification status"""
    sellers = SellerProfile.objects.select_related('user').order_by('-user__date_joined')
    
    # Filtering
    status = request.GET.get('status')
    if status == 'verified':
        sellers = sellers.filter(is_verified=True)
    elif status == 'pending':
        sellers = sellers.filter(is_verified=False)
    
    location = request.GET.get('location')
    if location:
        sellers = sellers.filter(municipality=location)
    
    # Search
    search = request.GET.get('search')
    if search:
        sellers = sellers.filter(
            Q(shop_name__icontains=search) |
            Q(user__username__icontains=search)
        )
    
    paginator = Paginator(sellers, 20)
    page = request.GET.get('page')
    sellers = paginator.get_page(page)
    
    context = {
        'sellers': sellers,
        'status': status,
        'location': location,
        'search': search or '',
    }
    return render(request, 'custom_admin/seller_list.html', context)


@login_required
@user_passes_test(is_admin)
def verify_seller(request, seller_id):
    """Toggle seller verification"""
    seller = get_object_or_404(SellerProfile, id=seller_id)
    seller.is_verified = not seller.is_verified
    seller.save()
    
    status = 'verified' if seller.is_verified else 'unverified'
    messages.success(request, f'{seller.shop_name} has been {status}.')
    
    # Create notification for seller
    Notification.objects.create(
        recipient=seller.user,
        notification_type='order_status',
        title='Verification Status Updated',
        message=f'Your seller account has been {status} by admin.',
        link='/users/dashboard/'
    )
    
    return redirect('custom_admin:seller_list')


@login_required
@user_passes_test(is_admin)
def product_list(request):
    """List all products"""
    products = Product.objects.select_related('seller', 'category').order_by('-created_at')
    
    # Filtering
    status = request.GET.get('status')
    if status == 'live':
        products = products.filter(is_live=True)
    elif status == 'hidden':
        products = products.filter(is_live=False)
    elif status == 'out_of_stock':
        products = products.filter(stocks_kg__lte=0)
    elif status == 'low_stock':
        products = products.filter(stocks_kg__gt=0, stocks_kg__lte=5)
    
    category = request.GET.get('category')
    if category:
        products = products.filter(category__slug=category)
    
    # Search
    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(seller__username__icontains=search)
        )
    
    categories = Category.objects.all()
    
    paginator = Paginator(products, 20)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    context = {
        'products': products,
        'categories': categories,
        'status': status,
        'category': category,
        'search': search or '',
    }
    return render(request, 'custom_admin/product_list.html', context)


@login_required
@user_passes_test(is_admin)
def product_toggle(request, product_id):
    """Toggle product live status"""
    product = get_object_or_404(Product, id=product_id)
    product.is_live = not product.is_live
    product.save()
    
    status = 'live' if product.is_live else 'hidden'
    messages.success(request, f'{product.name} is now {status}.')
    
    return redirect('custom_admin:product_list')


@login_required
@user_passes_test(is_admin)
def category_list(request):
    """Manage categories"""
    categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'create':
            name = request.POST.get('name')
            slug = request.POST.get('slug')
            icon = request.POST.get('icon', '🐟')
            description = request.POST.get('description', '')
            
            Category.objects.create(
                name=name,
                slug=slug,
                icon=icon,
                description=description
            )
            messages.success(request, f'Category "{name}" created successfully.')
        
        elif action == 'delete':
            cat_id = request.POST.get('category_id')
            cat = get_object_or_404(Category, id=cat_id)
            cat_name = cat.name
            cat.delete()
            messages.success(request, f'Category "{cat_name}" deleted.')
        
        return redirect('custom_admin:category_list')
    
    context = {
        'categories': categories,
    }
    return render(request, 'custom_admin/category_list.html', context)


@login_required
@user_passes_test(is_admin)
def order_list(request):
    """List all orders"""
    orders = Order.objects.select_related('buyer', 'seller').order_by('-created_at')
    
    # Filtering
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    payment = request.GET.get('payment')
    if payment:
        orders = orders.filter(payment_method=payment)
    
    # Search
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(id__icontains=search) |
            Q(buyer__username__icontains=search) |
            Q(seller__username__icontains=search)
        )
    
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'status': status,
        'payment': payment,
        'search': search or '',
        'status_choices': Order.STATUS_CHOICES,
        'payment_choices': Order.PAYMENT_METHOD_CHOICES,
    }
    return render(request, 'custom_admin/order_list.html', context)


@login_required
@user_passes_test(is_admin)
def order_detail(request, order_id):
    """View order details"""
    order = get_object_or_404(Order.objects.select_related('buyer', 'seller'), id=order_id)
    items = order.items.select_related('product').all()
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status != order.status:
            old_status = order.get_status_display()
            order.status = new_status
            order.save()
            
            # Notify buyer
            Notification.objects.create(
                recipient=order.buyer,
                notification_type='order_status',
                title=f'Order #{order.id} Status Updated',
                message=f'Your order status changed from {old_status} to {order.get_status_display()}',
                link=f'/orders/{order.id}/'
            )
            
            messages.success(request, f'Order status updated to {order.get_status_display()}.')
        
        return redirect('custom_admin:order_detail', order_id=order_id)
    
    context = {
        'order': order,
        'items': items,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'custom_admin/order_detail.html', context)


@login_required
@user_passes_test(is_admin)
def review_list(request):
    """List all reviews"""
    reviews = Review.objects.select_related('product', 'user').order_by('-created_at')
    
    # Filtering by rating
    rating = request.GET.get('rating')
    if rating:
        reviews = reviews.filter(rating=rating)
    
    paginator = Paginator(reviews, 20)
    page = request.GET.get('page')
    reviews = paginator.get_page(page)
    
    context = {
        'reviews': reviews,
        'rating': rating,
    }
    return render(request, 'custom_admin/review_list.html', context)


@login_required
@user_passes_test(is_admin)
def delete_review(request, review_id):
    """Delete a review"""
    review = get_object_or_404(Review, id=review_id)
    review.delete()
    messages.success(request, 'Review deleted successfully.')
    return redirect('custom_admin:review_list')


@login_required
@user_passes_test(is_admin)
def reports(request):
    """Analytics and reports"""
    today = timezone.now().date()
    this_month = today - timedelta(days=30)
    
    # Monthly revenue trend
    monthly_revenue = Order.objects.filter(
        status__in=['paid', 'preparing', 'out_for_delivery', 'completed'],
        created_at__date__gte=today - timedelta(days=180)
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        revenue=Sum('total_amount'),
        orders=Count('id')
    ).order_by('month')
    
    # Top selling products
    top_products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity_kg'),
        revenue=Sum('orderitem__price_at_purchase')
    ).filter(total_sold__isnull=False).order_by('-total_sold')[:10]
    
    # Top sellers by revenue
    top_sellers = SellerProfile.objects.annotate(
        total_orders=Count('user__received_orders'),
        total_revenue=Sum('user__received_orders__total_amount')
    ).filter(total_revenue__isnull=False).order_by('-total_revenue')[:10]
    
    # Orders by payment method
    orders_by_payment = Order.objects.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('total_amount')
    )
    
    # Orders by location
    orders_by_location = SellerProfile.objects.values('municipality').annotate(
        orders=Count('user__received_orders'),
        revenue=Sum('user__received_orders__total_amount')
    )
    
    # User growth
    user_growth = User.objects.filter(
        date_joined__date__gte=today - timedelta(days=30)
    ).annotate(
        date=TruncDate('date_joined')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    context = {
        'monthly_revenue': list(monthly_revenue),
        'top_products': top_products,
        'top_sellers': top_sellers,
        'orders_by_payment': list(orders_by_payment),
        'orders_by_location': list(orders_by_location),
        'user_growth': list(user_growth),
    }
    return render(request, 'custom_admin/reports.html', context)


@login_required
@user_passes_test(is_admin)
def send_notification(request):
    """Send notification to users"""
    if request.method == 'POST':
        recipient_type = request.POST.get('recipient_type')
        title = request.POST.get('title')
        message = request.POST.get('message')
        
        if recipient_type == 'all':
            recipients = User.objects.all()
        elif recipient_type == 'buyers':
            recipients = User.objects.filter(is_buyer=True)
        elif recipient_type == 'sellers':
            recipients = User.objects.filter(is_seller=True)
        else:
            recipients = User.objects.none()
        
        for user in recipients:
            Notification.objects.create(
                recipient=user,
                notification_type='order_status',
                title=title,
                message=message
            )
        
        messages.success(request, f'Notification sent to {recipients.count()} users.')
        return redirect('custom_admin:dashboard')
    
    return render(request, 'custom_admin/send_notification.html')
