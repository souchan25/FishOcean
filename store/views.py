from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from decimal import Decimal
from .models import Product, Category, Review, ProductImage, Wishlist
from .cart import Cart
from django.contrib import messages
from orders.models import Order, OrderItem
# import requests # for later paymongo

def product_list(request):
    products = Product.objects.filter(is_live=True, stocks_kg__gt=0).select_related(
        'seller', 'seller__seller_profile', 'category'
    ).prefetch_related('reviews')
    
    # Search
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(seller__seller_profile__shop_name__icontains=query)
        )
        
    # Filter by Category
    category_slug = request.GET.get('category')
    if category_slug:
        products = products.filter(category__slug=category_slug)
        
    # Filter by Location
    location = request.GET.get('location')
    if location:
        products = products.filter(seller__seller_profile__municipality=location)

    # Filter by Price Range
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price_per_kg__gte=min_price)
    if max_price:
        products = products.filter(price_per_kg__lte=max_price)
    
    # Filter by tags
    filter_tag = request.GET.get('filter')
    if filter_tag == 'fresh':
        products = products.filter(is_fresh_catch=True)
    elif filter_tag == 'bestseller':
        products = products.filter(is_bestseller=True)
    elif filter_tag == 'discount':
        products = products.filter(original_price__isnull=False)

    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price_per_kg')
    elif sort_by == 'price_high':
        products = products.order_by('-price_per_kg')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    elif sort_by == 'popular':
        products = products.annotate(review_count=Count('reviews')).order_by('-review_count')
    else:  # newest
        products = products.order_by('-created_at')

    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page = request.GET.get('page', 1)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    # Get user's wishlist if authenticated
    user_wishlist = []
    if request.user.is_authenticated:
        user_wishlist = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    categories = Category.objects.all()
    
    return render(request, 'store/product_list.html', {
        'products': products,
        'categories': categories,
        'current_location': location,
        'current_category': category_slug,
        'current_sort': sort_by,
        'current_filter': filter_tag,
        'min_price': min_price,
        'max_price': max_price,
        'search_query': query,
        'user_wishlist': user_wishlist,
        'total_count': paginator.count,
    })

def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    # Get quantity from form, default to 1 if not present (e.g. via direct link)
    quantity = Decimal(request.POST.get('quantity', 1))
    try:
        cart.add(product=product, quantity_kg=quantity)
        messages.success(request, f"Added {product.name} to cart.")
    except ValueError as e:
        messages.error(request, str(e))
    # Redirect back to where they came from if possible
    return redirect(request.META.get('HTTP_REFERER', 'store:product_list'))

def cart_clear(request):
    cart = Cart(request)
    cart.clear()
    return redirect('store:cart_detail')

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'store/cart_detail.html', {'cart': cart})

@login_required
def checkout(request):
    cart = Cart(request)
    if not cart.cart:
        return redirect('store:product_list')
    
    # Identify Seller (All items are from same seller due to logic)
    seller_id = cart.seller_id
    from users.models import User
    seller = User.objects.get(id=seller_id) if seller_id else None
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        delivery_address = request.POST.get('delivery_address')
        contact_number = request.POST.get('contact_number')
        valid_payment_methods = [m[0] for m in Order.PAYMENT_METHOD_CHOICES]
        if payment_method not in valid_payment_methods:
            messages.error(request, "Please choose a valid payment method.")
            return redirect('store:checkout')
        
        if not delivery_address or not contact_number:
            messages.error(request, "Please provide delivery address and contact number.")
            return redirect('store:checkout')

        try:
            with transaction.atomic():
                # 1. Create Order Placeholder
                order = Order(
                    buyer=request.user,
                    seller=seller,
                    payment_method=payment_method,
                    total_amount=cart.get_total_price(),
                    delivery_address=delivery_address,
                    contact_number=contact_number
                )
                
                # 2. Validate Stock & Deduct
                for item in cart:
                    product = item['product']
                    # Convert to Decimal for calculation
                    quantity_needed = Decimal(str(item['quantity']))
                    
                    # Lock row for update
                    product_obj = Product.objects.select_for_update().get(id=product.id)
                    
                    if product_obj.stocks_kg < quantity_needed:
                        raise ValueError(f"Insufficient stock for {product.name}. Available: {product_obj.stocks_kg}kg")
                    
                    product_obj.stocks_kg -= quantity_needed
                    # Auto-set live status off if stock hits 0
                    if product_obj.stocks_kg <= 0:
                        product_obj.is_live = False
                    product_obj.save()
                
                # 3. Save Order and Items if all stocks strictly available
                order.save()
                
                for item in cart:
                    # We iterate again or could have stored obj, but this is fine for small carts
                    OrderItem.objects.create(
                        order=order,
                        product=item['product'],
                        quantity_kg=item['quantity'],
                        price_at_purchase=item['price']
                    )
                    
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('store:cart_detail')
            
        cart.clear()

        if payment_method in ['direct_gcash', 'direct_maya']:
            return redirect('orders:payment_upload', order_id=order.id)
        if payment_method == 'paymongo':
            return redirect('orders:paymongo_init', order_id=order.id)

        return redirect('orders:order_detail', order_id=order.id)

    return render(request, 'store/checkout.html', {'cart': cart, 'seller': seller})

@login_required
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # Check ownership
    if product.seller != request.user:
        messages.error(request, "You do not own this product.")
        return redirect('users:seller_dashboard')
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.price_per_kg = request.POST.get('price')
        product.stocks_kg = Decimal(request.POST.get('stocks'))
        cat_id = request.POST.get('category')
        if cat_id:
            product.category = get_object_or_404(Category, id=cat_id)
        
        if request.FILES.get('image'):
            product.image = request.FILES.get('image')

        for img in request.FILES.getlist('images'):
            ProductImage.objects.create(product=product, image=img)
            
        product.save()
        messages.success(request, "Product updated.")
        return redirect('users:seller_dashboard')
        
    return render(request, 'store/edit_product.html', {'product': product, 'categories': Category.objects.all()})

@login_required
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if product.seller == request.user:
        product.delete()
        messages.success(request, "Product deleted.")
    else:
        messages.error(request, "Permission denied.")
    return redirect('users:seller_dashboard')

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all()
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    user_has_reviewed = False
    if request.user.is_authenticated:
        user_has_reviewed = reviews.filter(user=request.user).exists()

    context = {
        'product': product,
        'reviews': reviews,
        'avg_rating': round(avg_rating, 1),
        'user_has_reviewed': user_has_reviewed,
        'range_5': range(1, 6), # Helper for star loops
    }
    return render(request, 'store/product_detail.html', context)

@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        content = request.POST.get('content')
        
        # Simple server-side validation
        if rating and content:
            # Check existing
            if Review.objects.filter(product=product, user=request.user).exists():
                 messages.error(request, "You have already reviewed this product.")
            else:
                Review.objects.create(
                    product=product,
                    user=request.user,
                    rating=rating,
                    content=content
                )
                messages.success(request, "Review submitted!")
        else:
            messages.error(request, "Please fill in all fields.")
            
    return redirect('store:product_detail', product_id=product.id)


# ============== WISHLIST VIEWS ==============

@login_required
def wishlist(request):
    """Display user's wishlist"""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related(
        'product', 'product__seller', 'product__seller__seller_profile', 'product__category'
    )
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})


@login_required
def toggle_wishlist(request, product_id):
    """Add or remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if not created:
        # Item already exists, remove it
        wishlist_item.delete()
        action = 'removed'
        messages.info(request, f"{product.name} removed from wishlist")
    else:
        action = 'added'
        messages.success(request, f"{product.name} added to wishlist")
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'action': action,
            'product_id': product_id
        })
    
    # Redirect back to referrer or product detail
    return redirect(request.META.get('HTTP_REFERER', 'store:product_detail'), product_id=product.id)


@login_required
def remove_from_wishlist(request, product_id):
    """Remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.filter(user=request.user, product=product).delete()
    messages.info(request, f"{product.name} removed from wishlist")
    return redirect('store:wishlist')

