from .models import Product, Category, Supplier
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product, Supplier, Category, StockTransaction


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(
        attrs={'class': 'form-control'}))

    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to all fields
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class ProductForm(forms.Form):
    name = forms.CharField(max_length=100)
    category = forms.ModelChoiceField(queryset=Category.objects.all(),required=False,to_field_name='name')
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all(),required=False,to_field_name='name')
    sku = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))
    price = forms.DecimalField(min_value=0, decimal_places=2)
    stock_quantity = forms.IntegerField(min_value=0)
    reorder_level = forms.IntegerField(min_value=0)
    image = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make some fields required
        self.fields['sku'].required = True
        self.fields['description'].required = True

        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

        # Add placeholders
        self.fields['name'].widget.attrs['placeholder'] = 'Enter product name'
        self.fields['sku'].widget.attrs['placeholder'] = 'Enter SKU'
        self.fields['description'].widget.attrs['placeholder'] = 'Enter product description'

        # Add help text
        self.fields['reorder_level'].help_text = 'Minimum stock level before reorder alert'
        self.fields['image'].help_text = 'Upload product image (optional)'


class SupplierForm(forms.Form):
    name = forms.CharField(max_length=100)
    contact_person = forms.CharField(max_length=100)
    email = forms.EmailField()
    phone = forms.CharField(max_length=15)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'


class StockTransactionForm(forms.Form):
    product = forms.ModelChoiceField(queryset=Product.objects.all(), to_field_name='name')
    transaction_type = forms.ChoiceField(choices=StockTransaction.TRANSACTION_TYPES)
    quantity = forms.IntegerField(min_value=1)
    notes = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'


class CategoryForm(forms.Form):
    name = forms.CharField(max_length=100)
    description = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
