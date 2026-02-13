from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import Conversation, Message
from .forms import MessageForm

User = get_user_model()

@login_required
def chat_list(request):
    conversations = Conversation.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    )
    return render(request, 'chat/chat_list.html', {'conversations': conversations})

@login_required
def chat_detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk)
    
    # Security Check
    if request.user != conversation.buyer and request.user != conversation.seller:
        return redirect('chat:chat_list')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = request.user
            message.save()
            
            conversation.updated_at = message.timestamp
            conversation.save()
            return redirect('chat:chat_detail', pk=pk)
    else:
        form = MessageForm()

    # Mark as read Logic (Simplified)
    conversation.messages.exclude(sender=request.user).update(is_read=True)

    return render(request, 'chat/chat_detail.html', {
        'conversation': conversation,
        'messages': conversation.messages.all(),
        'form': form
    })

@login_required
def start_chat(request, seller_id):
    seller = get_object_or_404(User, id=seller_id)
    
    if request.user == seller:
        return redirect('store:product_list')
        
    # Logic: If user is seller, find conv with buyer? No, start_chat assumes Buyer initiates.
    # What if a seller clicks "Chat" on another seller? treated as buyer.
    
    # Determine roles strictly or loosely? Loosely: User1 & User2.
    # But model has Buyer/Seller fields.
    # Let's assume request.user is BUYER for this interaction.
    
    if request.user.is_seller and not request.user.is_buyer:
         # Edge case: Seller chatting another Seller?
         # Check if conversation exists as (buyer=me, seller=them) OR (buyer=them, seller=me)
         pass

    # Simplified: request.user acts as Buyer field usually
    conversation, created = Conversation.objects.get_or_create(
        buyer=request.user,
        seller=seller
    )
    return redirect('chat:chat_detail', pk=conversation.id)
