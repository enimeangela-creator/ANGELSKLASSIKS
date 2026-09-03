from django.contrib import admin
from .models import (
    Category,
    Product,
    CartItem,
    Order,
    OrderItem
)


admin.site.site_header = "Angel's Klassiks Administration"
admin.site.site_title = "Angel's Klassiks Admin"
admin.site.index_title = "Store Management"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = [
        'name',
        'category',
        'price',
        'stock',
        'available',
        'featured',
        'created_at'
    ]

    list_filter = [
        'category',
        'available',
        'featured',
        'created_at'
    ]

    search_fields = [
        'name',
        'description'
    ]

    prepopulated_fields = {
        'slug': ('name',)
    }

    list_editable = [
        'price',
        'stock',
        'available',
        'featured'
    ]


class OrderItemInline(admin.TabularInline):

    model = OrderItem

    extra = 0

    readonly_fields = [
        'product_name',
        'price',
        'quantity'
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'full_name',
        'phone_number',
        'total_amount',
        'payment_status',
        'status',
        'payment_reference',
        'created_at'
    ]

    list_filter = [
        'payment_status',
        'status',
        'state',
        'created_at'
    ]

    search_fields = [
        'full_name',
        'email',
        'phone_number',
        'payment_reference'
    ]

    list_editable = [
        'payment_status',
        'status'
    ]

    readonly_fields = [
        'user',
        'total_amount',
        'payment_reference',
        'paid_at',
        'created_at'
    ]

    inlines = [
        OrderItemInline
    ]

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):

    list_display = [
        'user',
        'product',
        'quantity',
        'created_at'
    ]
# Register your models here.
