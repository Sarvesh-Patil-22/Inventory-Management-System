from djongo import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        if self.stock_quantity < 0:
            raise ValidationError('Stock quantity cannot be negative.')


class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    transaction_type = models.CharField(
        max_length=3, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    transaction_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True)

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError('Quantity must be greater than zero.')

        if self.transaction_type == 'OUT' and self.product.stock_quantity < self.quantity:
            raise ValidationError('Insufficient stock available.')

    def save(self, *args, **kwargs):
        if self.transaction_type == 'IN':
            self.product.stock_quantity += self.quantity
        else:
            self.product.stock_quantity -= self.quantity

        self.product.save()
        super().save(*args, **kwargs)


