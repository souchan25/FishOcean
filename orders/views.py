from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from .models import Order, OrderItem
from store.models import Product
from store.cart import Cart
import requests
import base64

@login_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    # Security: Ensure only the assigned seller can update
    if order.seller != request.user:
        messages.error(request, "Access denied. You are not the seller.")
        return redirect('users:seller_dashboard')
        
    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = [s[0] for s in Order.STATUS_CHOICES]
        
        if new_status in valid_statuses:
            order.status = new_status
            order.save()
            messages.success(request, f"Order #{order.id} is now {order.get_status_display()}.")
        else:
            messages.error(request, "Invalid status update.")
            
    return redirect('users:seller_dashboard')

@login_required
def order_detail(request, order_id):
    """View order details - accessible by buyer or seller"""
    order = get_object_or_404(Order, id=order_id)
    
    # Security check: only buyer or seller can view
    if request.user not in [order.buyer, order.seller]:
        messages.error(request, "Access denied.")
        return redirect('store:product_list')
    
    return render(request, 'orders/order_detail.html', {'order': order})

@login_required
def order_history(request):
    """Buyer order history with filtering"""
    orders = Order.objects.filter(buyer=request.user).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Filter by seller
    seller_filter = request.GET.get('seller')
    if seller_filter:
        orders = orders.filter(seller__id=seller_filter)
    
    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'current_status': status_filter,
    }
    return render(request, 'orders/order_history.html', context)

@login_required
def reorder(request, order_id):
    """Reorder - add all items from a previous order to cart"""
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    cart = Cart(request)
    
    # Clear existing cart
    cart.clear()
    
    # Add all items from the order
    try:
        for item in order.items.all():
            if item.product and item.product.is_available:
                cart.add(product=item.product, quantity_kg=item.quantity_kg)
        messages.success(request, f"Added {order.items.count()} items from Order #{order.id} to your cart.")
    except ValueError as e:
        messages.error(request, str(e))
    
    return redirect('store:cart_detail')

@login_required
def payment_upload(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    if order.payment_method not in ['direct_gcash', 'direct_maya']:
        messages.error(request, "This order does not require manual payment proof.")
        return redirect('orders:order_detail', order_id=order.id)
    
    if request.method == 'POST':
        if 'proof' in request.FILES:
            order.proof_of_payment = request.FILES['proof']
            order.save()
            messages.success(request, "Proof of payment uploaded. Waiting for seller verification.")
            return redirect('orders:order_detail', order_id=order.id)
            
    return render(request, 'orders/payment_upload.html', {'order': order})

@login_required
def paymongo_init(request, order_id):
    order = get_object_or_404(Order, id=order_id, buyer=request.user)
    if order.payment_method != 'paymongo':
        messages.error(request, "This order is not set for PayMongo payment.")
        return redirect('orders:order_detail', order_id=order.id)
    
    # Simple PayMongo Link Creation
    url = "https://api.paymongo.com/v1/links"
    
    auth_token = base64.b64encode(settings.PAYMONGO_SECRET_KEY.encode()).decode()
    
    payload = {
        "data": {
            "attributes": {
                "amount": int(order.total_amount * 100), # Amount in centavos
                "description": f"Payment for Order #{order.id}",
                "remarks": f"FishCurrent Order {order.id}"
            }
        }
    }
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": "Basic " + auth_token
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            checkout_url = data['data']['attributes']['checkout_url']
            reference_number = data['data']['attributes']['reference_number']
            
            # Save reference
            order.paymongo_checkout_id = reference_number
            order.save()
            
            return redirect(checkout_url)
        else:
            messages.error(request, f"PayMongo Error: {response.text}")
    except Exception as e:
        messages.error(request, str(e))
        
    return redirect('orders:order_detail', order_id=order.id)

