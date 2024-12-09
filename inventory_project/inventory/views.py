from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from .forms import *
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from pymongo import MongoClient
import uuid
import os
from django.http import Http404
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['inventory']


def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful.")
            return redirect('dashboard')  # Changed from 'home' to 'dashboard'
        else:
            messages.error(
                request, "Unsuccessful registration. Invalid information.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                # Changed from 'home' to 'dashboard'
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('dashboard')  # Changed from 'home' to 'dashboard'

@login_required
def dashboard(request):
    # Categories with product count
    categories_pipeline = [
        {'$match': {'active': True}},
        {
            '$lookup': {
                'from': 'inventory_product',
                'localField': 'id',
                'foreignField': 'category_id',
                'as': 'products'
            }
        },
        {
            '$project': {
                'name': 1,
                'product_count': {'$size': '$products'}
            }
        },
        {'$sort': {'name': 1}}
    ]

    # Total inventory value
    value_pipeline = [
        {'$match': {'active': True}},
        {
            '$group': {
                '_id': None,
                'total_value': {
                    '$sum': {'$multiply': ['$stock_quantity', '$price']}
                }
            }
        }
    ]

    pipeline = [
        {
            '$match': {
                '$expr': {  # Use $expr to compare fields within the same document
                    '$lte': ['$stock_quantity', '$reorder_level']
                }
            }
        }
    ]

    context = {
        'products_count': db.inventory_product.count_documents({'active': True}),
        'low_stock_products': list(db.inventory_product.aggregate(pipeline)),
        'suppliers_count': db.inventory_supplier.count_documents({'active': True}),
        'recent_transactions': list(db.inventory_stocktransaction.find().sort('transaction_date', -1).limit(5)),
        'categories': list(db.inventory_category.aggregate(categories_pipeline)),
        'recent_suppliers': list(db.inventory_supplier.find().sort('created_at', -1).limit(5)),
        'total_value': next(db.inventory_product.aggregate(value_pipeline), {}).get('total_value', 0)
    }
    print(context)
    return render(request, 'inventory/dashboard.html', context)




@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product_data = form.cleaned_data
            product_data['id'] = str(uuid.uuid4())
            product_data['active'] = True
            product_data['created_at'] = timezone.now()
            product_data['category'] = form.cleaned_data['category'].name
            product_data['supplier'] = form.cleaned_data['supplier'].name
            # Handle image upload
            if request.FILES.get('image'):
                image = request.FILES['image']
                image_name = f"{product_data['id']}_{image.name}"
                image_path = os.path.join('products', image_name)
                full_path = os.path.join(settings.MEDIA_ROOT, image_path)

                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb+') as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)

                product_data['image'] = image_path

            # Convert decimal to float for MongoDB
            product_data['price'] = float(product_data['price'])

            # Insert into MongoDB
            db.inventory_product.insert_one(product_data)
            messages.success(request, 'Product created successfully.')
            return redirect('product_detail', pk=product_data['id'])
    else:
        form = ProductForm()

    return render(request, 'inventory/product_form.html', {'form': form, 'title': 'Add Product'})


@login_required
def product_list(request):
    query = {'active': True}

    # Handle search
    search_query = request.GET.get('search')
    if search_query:
        query['$or'] = [
            {'name': {'$regex': search_query, '$options': 'i'}},
            {'sku': {'$regex': search_query, '$options': 'i'}}
        ]

    # Handle category filter
    category_id = request.GET.get('category')
    if category_id:
        query['category_id'] = category_id

    # Get all products
    products = list(db.inventory_product.find(query))

    # Ensure each product has an ID
    for product in products:
        if '_id' in product and not product.get('id'):
            product['id'] = str(product['_id'])

    # Get categories
    categories = list(db.inventory_category.find({'active': True}))

    # Debug print
    print("Sample product:", products[0] if products else "No products found")

    return render(request, 'inventory/product_list.html', {
        'products': products,
        'categories': categories
    })


@login_required
def product_detail(request, pk):
    # First try to find by id field
    product = db.inventory_product.find_one({'id': pk, 'active': True})

    if not product:
        # Try to find by _id if not found by id
        product = db.inventory_product.find_one({'_id': pk, 'active': True})

    if not product:
        raise Http404("Product not found")

    if '_id' in product and not product.get('id'):
        product['id'] = str(product['_id'])
        db.inventory_product.update_one(
            {'_id': product['_id']},
            {'$set': {'id': str(product['_id'])}}
        )

    transactions = list(db.inventory_stocktransaction.find(
        {'product_id': pk}).sort('transaction_date', -1))

    if request.method == 'POST':
        form = StockTransactionForm(request.POST)
        if form.is_valid():
            transaction_data = form.cleaned_data
            transaction_data['product_id'] = pk
            transaction_data['created_by_id'] = request.user.id
            transaction_data['transaction_date'] = timezone.now()
            transaction_data['id'] = str(uuid.uuid4())


            print("Transaction data:", transaction_data)
            transaction_data['product'] = form.cleaned_data['product'].name

            # Update stock quantity
            new_quantity = (
                int(product['stock_quantity']) + int(transaction_data['quantity'])
                if transaction_data['transaction_type'] == 'IN'
                else product['stock_quantity'] - transaction_data['quantity']
            )

            if new_quantity < 0:
                messages.error(request, 'Insufficient stock available.')
                return redirect('product_detail', pk=pk)

            # Update product stock
            db.inventory_product.update_one(
                {'id': pk},
                {'$set': {'stock_quantity': new_quantity}}
            )

            # Insert transaction
            db.inventory_stocktransaction.insert_one(transaction_data)
            messages.success(request, 'Stock updated successfully.')
            return redirect('product_detail', pk=pk)
    else:
        form = StockTransactionForm()

    context = {
        'product': product,
        'transactions': transactions,
        'form': form
    }
    return render(request, 'inventory/product_detail.html', context)

@login_required
def product_update(request, pk):
    product = db.inventory_product.find_one({'id': pk, 'active': True})
    if not product:
        raise Http404("Product not found")

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            update_data = form.cleaned_data
            update_data['updated_at'] = timezone.now()

            # Handle image upload
            if request.FILES.get('image'):
                # Delete old image if exists
                if product.get('image'):
                    old_image_path = os.path.join(
                        settings.MEDIA_ROOT, product['image'])
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)

                image = request.FILES['image']
                image_name = f"{pk}_{image.name}"
                image_path = os.path.join('products', image_name)
                full_path = os.path.join(settings.MEDIA_ROOT, image_path)

                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'wb+') as destination:
                    for chunk in image.chunks():
                        destination.write(chunk)

                update_data['image'] = image_path

            # Convert decimal to float for MongoDB
            update_data['price'] = float(update_data['price'])

            db.inventory_product.update_one(
                {'id': pk},
                {'$set': update_data}
            )
            messages.success(request, 'Product updated successfully.')
            return redirect('product_detail', pk=pk)
    else:
        form = ProductForm(initial=product)

    return render(request, 'inventory/product_form.html', {
        'form': form,
        'title': f'Edit {product.get("name")}'
    })


@login_required
def product_delete(request, pk):
    product = db.inventory_product.find_one({'id': pk, 'active': True})
    if not product:
        raise Http404("Product not found")

    if request.method == 'POST':
        db.inventory_product.update_one(
            {'id': pk},
            {
                '$set': {
                    'active': False,
                    'updated_at': timezone.now()
                }
            }
        )
        messages.success(request, 'Product deleted successfully.')
        return redirect('product_list')

    return render(request, 'inventory/product_delete.html', {'product': product})


# @login_required
# def category_list(request):
#     pipeline = [
#         {'$match': {'active': True}},
#         {
#             '$lookup': {
#                 'from': 'inventory_product',
#                 'localField': 'id',
#                 'foreignField': 'category_id',
#                 'as': 'products'
#             }
#         },
#         {
#             '$project': {
#                 'name': 1,
#                 'description': 1,
#                 'product_count': {'$size': '$products'}
#             }
#         }
#     ]
#     categories = list(db.inventory_category.aggregate(pipeline))
#     return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category_data = form.cleaned_data
            category_data['id'] = str(uuid.uuid4())
            category_data['active'] = True
            category_data['created_at'] = timezone.now()

            # Check for existing category
            existing = db.inventory_category.find_one({
                'name': category_data['name'],
                'active': True
            })

            if existing:
                messages.error(
                    request, 'Category with this name already exists.')
            else:
                db.inventory_category.insert_one(category_data)
                messages.success(request, 'Category created successfully.')
                return redirect('category_list')
    else:
        form = CategoryForm()

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'title': 'Create Category'
    })


@login_required
def category_update(request, pk):
    category = db.inventory_category.find_one({'id': pk})
    if not category:
        raise Http404("Category not found")

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            update_data = form.cleaned_data
            update_data['updated_at'] = timezone.now()

            db.inventory_category.update_one(
                {'id': pk},
                {'$set': update_data}
            )
            messages.success(request, 'Category updated successfully.')
            return redirect('category_list')
    else:
        form = CategoryForm(initial=category)

    return render(request, 'inventory/category_form.html', {
        'form': form,
        'title': f'Edit {category.get("name")}'
    })


@login_required
def category_delete(request, pk):
    category = db.inventory_category.find_one({'id': pk})
    if not category:
        raise Http404("Category not found")

    if request.method == 'POST':
        db.inventory_category.update_one(
            {'id': pk},
            {
                '$set': {
                    'active': False,
                    'updated_at': timezone.now()
                }
            }
        )
        messages.success(request, 'Category deleted successfully.')
        return redirect('category_list')

    return render(request, 'inventory/category_confirm_delete.html', {'category': category})


# @login_required
# def supplier_list(request):
#     query = {'active': True}

#     # Handle search
#     search_query = request.GET.get('search')
#     if search_query:
#         query['$or'] = [
#             {'name': {'$regex': search_query, '$options': 'i'}},
#             {'contact_person': {'$regex': search_query, '$options': 'i'}},
#             {'email': {'$regex': search_query, '$options': 'i'}}
#         ]

#     pipeline = [
#         {'$match': query},
#         {
#             '$lookup': {
#                 'from': 'inventory_product',
#                 'localField': 'id',
#                 'foreignField': 'supplier_id',
#                 'as': 'products'
#             }
#         },
#         {
#             '$project': {
#                 'name': 1,
#                 'contact_person': 1,
#                 'email': 1,
#                 'phone': 1,
#                 'product_count': {'$size': '$products'}
#             }
#         }
#     ]

#     suppliers = list(db.inventory_supplier.aggregate(pipeline))
#     return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier_data = form.cleaned_data
            supplier_data['id'] = str(uuid.uuid4())
            supplier_data['active'] = True
            supplier_data['created_at'] = timezone.now()

            # Check for existing supplier
            existing = db.inventory_supplier.find_one({
                'name': supplier_data['name'],
                'active': True
            })

            if existing:
                messages.error(
                    request, 'Supplier with this name already exists.')
            else:
                db.inventory_supplier.insert_one(supplier_data)
                messages.success(request, 'Supplier created successfully.')
                return redirect('supplier_list')
    else:
        form = SupplierForm()

    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'title': 'Create Supplier'
    })


@login_required
def supplier_update(request, pk):
    supplier = db.inventory_supplier.find_one({'id': pk, 'active': True})
    if not supplier:
        raise Http404("Supplier not found")

    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            update_data = form.cleaned_data
            update_data['updated_at'] = timezone.now()

            # Check for name uniqueness if name is being changed
            if update_data['name'] != supplier['name']:
                existing = db.inventory_supplier.find_one({
                    'name': update_data['name'],
                    'active': True,
                    'id': {'$ne': pk}
                })
                if existing:
                    messages.error(
                        request, 'Supplier with this name already exists.')
                    return render(request, 'inventory/supplier_form.html', {
                        'form': form,
                        'title': f'Edit {supplier["name"]}'
                    })

            db.inventory_supplier.update_one(
                {'id': pk},
                {'$set': update_data}
            )
            messages.success(request, 'Supplier updated successfully.')
            return redirect('supplier_list')
    else:
        form = SupplierForm(initial=supplier)

    return render(request, 'inventory/supplier_form.html', {
        'form': form,
        'title': f'Edit {supplier.get("name")}'
    })


@login_required
def supplier_detail(request, pk):
    pipeline = [
        {'$match': {'id': pk, 'active': True}},
        {
            '$lookup': {
                'from': 'inventory_product',
                'localField': 'id',
                'foreignField': 'supplier_id',
                'as': 'products'
            }
        },
        {
            '$lookup': {
                'from': 'inventory_stocktransaction',
                'localField': 'products.id',
                'foreignField': 'product_id',
                'as': 'transactions'
            }
        }
    ]

    supplier_data = list(db.inventory_supplier.aggregate(pipeline))
    if not supplier_data:
        raise Http404("Supplier not found")

    supplier = supplier_data[0]

    # Get recent transactions
    recent_transactions = list(db.inventory_stocktransaction.find({
        'product_id': {'$in': [p['id'] for p in supplier['products']]}
    }).sort('transaction_date', -1).limit(5))

    context = {
        'supplier': supplier,
        'products': supplier.get('products', []),
        'recent_transactions': recent_transactions,
        'total_products': len(supplier.get('products', [])),
        'total_value': sum(float(p.get('price', 0)) * p.get('stock_quantity', 0)
                           for p in supplier.get('products', []))
    }

    return render(request, 'inventory/supplier_detail.html', context)


@login_required
def supplier_delete(request, pk):
    supplier = db.inventory_supplier.find_one({'id': pk, 'active': True})
    if not supplier:
        raise Http404("Supplier not found")

    if request.method == 'POST':
        # Check if supplier has active products
        products_count = db.inventory_product.count_documents({
            'supplier_id': pk,
            'active': True
        })

        if products_count > 0:
            messages.error(request,
                           'Cannot delete supplier with active products. Please reassign or delete the products first.')
            return redirect('supplier_detail', pk=pk)

        # Soft delete the supplier
        db.inventory_supplier.update_one(
            {'id': pk},
            {
                '$set': {
                    'active': False,
                    'updated_at': timezone.now()
                }
            }
        )
        messages.success(request, 'Supplier deleted successfully.')
        return redirect('supplier_list')

    return render(request, 'inventory/supplier_confirm_delete.html', {
        'supplier': supplier,
        'products_count': db.inventory_product.count_documents({
            'supplier_id': pk,
            'active': True
        })
    })


@login_required
def stock_report(request):
    # Get all active products with their categories and suppliers
    pipeline = [
        {'$match': {'active': True}},
        {
            '$lookup': {
                'from': 'inventory_category',
                'localField': 'category_id',
                'foreignField': 'id',
                'as': 'category'
            }
        },
        {
            '$lookup': {
                'from': 'inventory_supplier',
                'localField': 'supplier_id',
                'foreignField': 'id',
                'as': 'supplier'
            }
        },
        {'$unwind': {'path': '$category', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$supplier', 'preserveNullAndEmptyArrays': True}}
    ]

    products = list(db.inventory_product.aggregate(pipeline))

    # Calculate total value
    total_value = sum(
        float(p['price']) * p['stock_quantity']
        for p in products
    )

    # Get low stock items
    low_stock = [p for p in products if p['stock_quantity']
                 <= p['reorder_level']]

    # Get top selling products (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    top_selling_pipeline = [
        {
            '$match': {
                'transaction_type': 'OUT',
                'transaction_date': {'$gte': thirty_days_ago}
            }
        },
        {
            '$group': {
                '_id': '$product_id',
                'total_quantity': {'$sum': '$quantity'}
            }
        },
        {'$sort': {'total_quantity': -1}},
        {'$limit': 5},
        {
            '$lookup': {
                'from': 'inventory_product',
                'localField': '_id',
                'foreignField': 'id',
                'as': 'product'
            }
        },
        {'$unwind': '$product'}
    ]

    top_selling = list(
        db.inventory_stocktransaction.aggregate(top_selling_pipeline))

    context = {
        'products': products,
        'total_value': total_value,
        'low_stock': low_stock,
        'low_stock_count': len(low_stock),
        'top_selling': top_selling,
        'total_products': len(products)
    }

    return render(request, 'inventory/stock_report.html', context)


@login_required
def supplier_list(request):
    query = {'active': True}

    # Handle search
    search_query = request.GET.get('search')
    if search_query:
        query['$or'] = [
            {'name': {'$regex': search_query, '$options': 'i'}},
            {'contact_person': {'$regex': search_query, '$options': 'i'}},
            {'email': {'$regex': search_query, '$options': 'i'}}
        ]

    # Get all suppliers
    suppliers = list(db.inventory_supplier.find(query))

    # Ensure each supplier has an ID
    for supplier in suppliers:
        if '_id' in supplier and not supplier.get('id'):
            supplier['id'] = str(supplier['_id'])

    # Get product counts
    for supplier in suppliers:
        supplier['product_count'] = db.inventory_product.count_documents({
            'supplier_id': supplier['id'],
            'active': True
        })

    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_detail(request, pk):
    # First try to find by id field
    supplier = db.inventory_supplier.find_one({'id': pk, 'active': True})

    if not supplier:
        # Try to find by _id if not found by id
        supplier = db.inventory_supplier.find_one({'_id': pk, 'active': True})

    if not supplier:
        raise Http404("Supplier not found")

    if '_id' in supplier and not supplier.get('id'):
        supplier['id'] = str(supplier['_id'])
        db.inventory_supplier.update_one(
            {'_id': supplier['_id']},
            {'$set': {'id': str(supplier['_id'])}}
        )

    # Get related products
    products = list(db.inventory_product.find({
        'supplier_id': supplier['id'],
        'active': True
    }))

    context = {
        'supplier': supplier,
        'products': products,
        'total_products': len(products),
        'total_value': sum(float(p.get('price', 0)) * p.get('stock_quantity', 0) for p in products)
    }

    return render(request, 'inventory/supplier_detail.html', context)


@login_required
def category_list(request):
    # Get all categories
    categories = list(db.inventory_category.find({'active': True}))

    # Ensure each category has an ID
    for category in categories:
        if '_id' in category and not category.get('id'):
            category['id'] = str(category['_id'])

    # Get product counts for each category
    for category in categories:
        category['product_count'] = db.inventory_product.count_documents({
            'category_id': category['id'],
            'active': True
        })

    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
def category_detail(request, pk):
    # First try to find by id field
    category = db.inventory_category.find_one({'id': pk, 'active': True})

    if not category:
        # Try to find by _id if not found by id
        category = db.inventory_category.find_one({'_id': pk, 'active': True})

    if not category:
        raise Http404("Category not found")

    if '_id' in category and not category.get('id'):
        category['id'] = str(category['_id'])
        db.inventory_category.update_one(
            {'_id': category['_id']},
            {'$set': {'id': str(category['_id'])}}
        )

    # Get related products
    products = list(db.inventory_product.find({
        'category_id': category['id'],
        'active': True
    }))

    context = {
        'category': category,
        'products': products,
        'total_products': len(products)
    }

    return render(request, 'inventory/category_detail.html', context)

