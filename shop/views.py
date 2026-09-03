from decimal import Decimal
import requests
import uuid

from django.conf import settings
from django.contrib import messages


from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)
from django.utils import timezone
from .models import (
    Product,
    Category,
    CartItem,
    Order,
    OrderItem
)

from .forms import RegisterForm, CheckoutForm


def home(request):
    products = Product.objects.filter(
        available=True
    ).order_by('-created_at')

    category = request.GET.get('category')
    search = request.GET.get('search')

    if category:
        products = products.filter(
            category__name=category
        )

    if search:
        products = products.filter(
            name__icontains=search
        )

    featured_products = Product.objects.filter(
        available=True,
        featured=True
    )[:8]

    context = {
        'products': products,
        'featured_products': featured_products,
        'selected_category': category,
    }

    return render(
        request,
        'shop/home.html',
        context
    )


def product_detail(request, slug):
    product = get_object_or_404(
        Product,
        slug=slug,
        available=True
    )

    related_products = Product.objects.filter(
        category=product.category,
        available=True
    ).exclude(
        id=product.id
    )[:4]

    return render(
        request,
        'shop/product_detail.html',
        {
            'product': product,
            'related_products': related_products
        }
    )


def register_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()

            login(request, user)

            messages.success(
                request,
                "Welcome to Angel's Klassiks! Your account has been created."
            )

            return redirect('home')

    else:
        form = RegisterForm()

    return render(
        request,
        'shop/register.html',
        {'form': form}
    )


@login_required
def add_to_cart(request, product_id):

    product = get_object_or_404(
        Product,
        id=product_id,
        available=True
    )

    if request.method == 'POST':

        if product.stock < 1:
            messages.error(
                request,
                "Sorry, this product is currently out of stock."
            )

            return redirect(
                'product_detail',
                slug=product.slug
            )

        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product
        )

        if not created:

            if cart_item.quantity < product.stock:
                cart_item.quantity += 1
                cart_item.save()
            else:
                messages.warning(
                    request,
                    "You cannot add more than the available stock."
                )

                return redirect('cart')

        messages.success(
            request,
            f"{product.name} was added to your cart."
        )

    return redirect('cart')


@login_required
def cart(request):

    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('product')

    total = sum(
        item.subtotal for item in cart_items
    )

    return render(
        request,
        'shop/cart.html',
        {
            'cart_items': cart_items,
            'total': total
        }
    )


@login_required
def update_cart(request, item_id):

    item = get_object_or_404(
        CartItem,
        id=item_id,
        user=request.user
    )

    if request.method == 'POST':

        try:
            quantity = int(
                request.POST.get('quantity', 1)
            )
        except ValueError:
            quantity = 1

        if quantity <= 0:
            item.delete()

        elif quantity <= item.product.stock:
            item.quantity = quantity
            item.save()

        else:
            messages.error(
                request,
                f"Only {item.product.stock} item(s) are available."
            )

    return redirect('cart')


@login_required
def remove_from_cart(request, item_id):

    item = get_object_or_404(
        CartItem,
        id=item_id,
        user=request.user
    )

    if request.method == 'POST':
        item.delete()

        messages.success(
            request,
            "Product removed from cart."
        )

    return redirect('cart')


@login_required
def checkout(request):

    cart_items = CartItem.objects.filter(
        user=request.user
    ).select_related('product')

    if not cart_items.exists():
        messages.warning(
            request,
            "Your cart is empty."
        )
        return redirect('home')

    total = sum(
        item.subtotal for item in cart_items
    )

    initial = {
        'full_name':
            f"{request.user.first_name} {request.user.last_name}".strip(),

        'email':
            request.user.email
    }

    if request.method == 'POST':

        form = CheckoutForm(request.POST)

        if form.is_valid():

            # Check stock before starting payment
            for item in cart_items:

                if item.quantity > item.product.stock:

                    messages.error(
                        request,
                        f"Sorry, only {item.product.stock} "
                        f"{item.product.name}(s) are left."
                    )

                    return redirect('cart')

            # Create the order but DO NOT reduce stock yet
            order = form.save(commit=False)

            order.user = request.user
            order.total_amount = total
            order.payment_status = 'unpaid'

            # Create a unique payment reference
            order.payment_reference = (
                f"AK-{uuid.uuid4().hex[:20].upper()}"
            )

            order.save()

            # Save the products in the order
            for item in cart_items:

                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.name,
                    price=item.product.price,
                    quantity=item.quantity
                )

            # Paystack amount is in kobo
            amount_in_kobo = int(
                Decimal(total) * 100
            )

            headers = {
                "Authorization":
                    f"Bearer {settings.PAYSTACK_SECRET_KEY}",

                "Content-Type":
                    "application/json"
            }

            data = {
                "email": order.email,

                "amount": amount_in_kobo,

                "currency": "NGN",

                "reference":
                    order.payment_reference,

                "callback_url":
                    request.build_absolute_uri(
                        '/payment/callback/'
                    ),

                "metadata": {
                    "order_id": order.id,
                    "customer_name": order.full_name
                }
            }

            try:

                response = requests.post(
                    "https://api.paystack.co/transaction/initialize",
                    json=data,
                    headers=headers,
                    timeout=30
                )

                result = response.json()

            except requests.RequestException:

                order.delete()

                messages.error(
                    request,
                    "Unable to connect to the payment system. "
                    "Please try again."
                )

                return redirect('checkout')

            if result.get('status'):

                payment_url = result['data']['authorization_url']

                return redirect(payment_url)

            order.delete()

            messages.error(
                request,
                "Payment could not be started. Please try again."
            )

            return redirect('checkout')

    else:

        form = CheckoutForm(
            initial=initial
        )

    return render(
        request,
        'shop/checkout.html',
        {
            'form': form,
            'cart_items': cart_items,
            'total': total
        }
    )
@login_required
@transaction.atomic
def payment_callback(request):

    reference = request.GET.get('reference')

    if not reference:
        messages.error(
            request,
            "Payment reference was not found."
        )

        return redirect('cart')

    order = get_object_or_404(
        Order,
        payment_reference=reference,
        user=request.user
    )

    # Don't process an order twice
    if order.payment_status == 'paid':

        return redirect(
            'order_success',
            order_id=order.id
        )

    headers = {
        "Authorization":
            f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    }

    try:

        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers,
            timeout=30
        )

        result = response.json()

    except requests.RequestException:

        messages.error(
            request,
            "We could not verify your payment. "
            "Please contact us if money was deducted."
        )

        return redirect('cart')

    if not result.get('status'):

        order.payment_status = 'failed'
        order.save()

        messages.error(
            request,
            "Payment verification failed."
        )

        return redirect('cart')

    payment = result.get('data', {})

    payment_status = payment.get('status')
    payment_amount = payment.get('amount')
    payment_currency = payment.get('currency')

    expected_amount = int(
        Decimal(order.total_amount) * 100
    )

    # Check that payment was successful
    if (
        payment_status == 'success'
        and payment_amount == expected_amount
        and payment_currency == 'NGN'
    ):

        # Check stock again before completing the order
        for item in order.items.select_related('product'):

            if item.product is None:
                continue

            if item.quantity > item.product.stock:

                order.payment_status = 'paid'
                order.status = 'pending'
                order.save()

                messages.error(
                    request,
                    "Your payment was successful, but some "
                    "items are no longer available. "
                    "Please contact Angel's Klassiks."
                )

                return redirect(
                    'order_success',
                    order_id=order.id
                )

        # Payment is confirmed
        order.payment_status = 'paid'
        order.status = 'confirmed'

        order.paid_at = timezone.now()

        order.save()

        # Now reduce stock
        for item in order.items.select_related('product'):

            if item.product:

                product = item.product

                product.stock -= item.quantity

                if product.stock <= 0:

                    product.stock = 0
                    product.available = False

                product.save()

        # Clear customer's cart
        CartItem.objects.filter(
            user=request.user
        ).delete()

        messages.success(
            request,
            "Payment successful! Your order has been confirmed."
        )

        return redirect(
            'order_success',
            order_id=order.id
        )

    # Payment was not successful
    order.payment_status = 'failed'
    order.save()

    messages.error(
        request,
        "Payment was not successful. Your order has not been completed."
    )

    return redirect('cart')

@login_required
def order_success(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(
        request,
        'shop/order_success.html',
        {'order': order}
    )


# Create your views here.
