import os.path
import re

import pandas as pd
from django.template import loader
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from .models import *
from django.db.models import Q
from django.shortcuts import redirect
from collections import defaultdict
from django.contrib import messages
from datetime import datetime, timedelta
import midtransclient
import uuid
from itertools import chain
import json
import requests
import numpy as np

# Create your views here.
SIZE_DICT = {'S': 'Small', 'M': 'Medium', 'L': 'Large', 'XL': 'Extra Large', 'XXL': 'Extra Extra Large'}
PATH = os.path.dirname(__file__)


def index(request):
    context = {}

    # total product in cart
    context['total_in_cart'] = total_product_in_cart(request)
    context['total_in_profile'] = total_product_buy(request)

    # update status order
    if request.GET.get('status_code'):
        unique_code = request.GET.get('order_id')
        update_status_order = Order.objects.get(unique_code=unique_code)
        update_status_order.status = request.GET.get('transaction_status')
        update_status_order.updated_at = datetime.now()
        update_status_order.save()

    #
    #  ------------------ Categori ------------------
    half_face = Products.objects.filter(category=2).values('name', 'image', 'category__name')[:1]
    full_face = Products.objects.filter(category=1).values('name', 'image', 'category__name')[:2]

    product_category = list(chain(half_face, full_face))

    context['product_category'] = product_category

    #  ------------------ End Categori ------------------

    #  ------------------ Featured ------------------
    featured = Products.objects.values('name', 'price',
                                       'desc', 'image')[:3]
    for item in featured:
        item['price'] = f"{int(item['price']):,}"

    context['featured'] = featured
    #  ------------------ End Featured ------------------

    #  ------------------ if any Search ------------------
    if request.GET.get('q'):
        list_product = query_get_product(param=request.GET.get('q'))
        context['list_product'] = list_product
        load_template = 'shop.html'

        context['segment'] = load_template
        html_template = loader.get_template(load_template)
        return HttpResponse(html_template.render(context, request))
    #  ------------------ end Search ------------------

    html_template = loader.get_template('index.html')
    return HttpResponse(html_template.render(context, request))


def pages(request):
    context = {}

    load_template = request.path.split('/')[-1]
    # MENU ADMIN
    if load_template == 'admin':
        return HttpResponseRedirect(reverse('admin:index'))

    # total product in cart
    context['total_in_cart'] = total_product_in_cart(request)
    context['total_in_profile'] = total_product_buy(request)

    # ====== check if any search ======
    if request.GET.get('q'):
        list_product = query_get_product(param=request.GET.get('q'))
        context['list_product'] = list_product
        load_template = 'shop.html'

        context['segment'] = load_template
        html_template = loader.get_template(load_template)
        return HttpResponse(html_template.render(context, request))
    # ====== end check ======

    # ====== SHOP MENU ======

    if load_template == 'shop.html':
        # filtering
        context['type'] = Categories.objects.values('name')
        context['brands'] = Brands.objects.values('name')
        context['size'] = [{'code': item['name'], 'name': SIZE_DICT[item['name']]} for item in
                           Sizes.objects.values('name')]
        context['size_categories'] = SizeCategories.objects.values('name')

        if request.GET.get('type'):
            list_product = query_get_product(param=request.GET.get('type'), field='category__name')
        elif request.GET.get('brand'):
            list_product = query_get_product(param=request.GET.get('brand'), field='brand__name')
        elif request.GET.get('size'):
            list_product = query_get_product(param=request.GET.get('size'), field='size__name')
        elif request.GET.get('size_categories'):
            list_product = query_get_product(param=request.GET.get('size_categories'),
                                             field='size__size_category__name')
        else:
            list_product = query_get_product()
        context['list_product'] = list_product

        if request.GET.get('product_id'):

            # === insert product to cart model ===
            product_id = request.GET.get('product_id')
            try:
                cart = Cart.objects.get(product=product_id, user=request.user)
                update_cart_model(req=request, cart=cart, product=Products.objects.get(product_id=product_id))
                msg = 'Cart update success!'
            except Cart.DoesNotExist:
                product = Products.objects.get(product_id=product_id)
                add_to_cart_model(req=request, product=product)
                msg = 'Add to cart success!'

            # === end insert product ===
            messages.success(request, msg)

            return redirect('/shop.html')

    # ====== END SHOP MENU ======

    # ====== shop-single ======
    if load_template == 'shop-single.html':

        # delete session variable cart_id in shop-single page
        if request.session.get('cart_id'):
            del request.session['cart_id']

        if request.GET.get('name'):

            # General shop-single
            name_product = request.GET.get('name')
            context['name'] = name_product

            raw_detail = details_product(name_product)
            context.update(item_shop_single(raw_detail))

            # End general shop-single

            if request.GET.get('size'):
                for key, value in raw_detail.items():
                    if request.GET.get('size') in value.get('size'):
                        i = value.get('size').index(request.GET.get('size'))  # index of size
                        raw_detail_filter_size = {key: {key: [value[i]] for key, value in value.items()}}
                        context.update(item_shop_single(raw_detail_filter_size))

        if request.POST:
            if not request.user.is_authenticated:
                return login_sek(request)

            if request.POST.get('buy'):
                data = [{
                    'id': request.POST.get('product_id'),
                    'name': request.POST.get('product-title'),
                    'price': request.POST.get('product-price'),
                    'size': request.POST.get('product-size'),
                    'quantity': request.POST.get('product-quanity'),
                    'img': request.POST.get('product-img')
                }]

                total = int(request.POST.get('product-quanity')) * int(
                    request.POST.get('product-price').replace(',', ''))

                request.session['total'] = f'{total:,}'
                request.session['quantity'] = request.POST.get('product-quanity')
                request.session['data'] = data

                return redirect('/checkout.html')
            else:
                product_id = request.POST.get('product_id')
                try:
                    cart = Cart.objects.get(product=product_id, user=request.user)
                    update_cart_model(req=request, cart=cart, product=Products.objects.get(product_id=product_id))
                    msg = 'Cart update success!'
                except Cart.DoesNotExist:
                    product = Products.objects.get(product_id=product_id)
                    add_to_cart_model(req=request, product=product)
                    msg = 'Add to cart success!'

                messages.success(request, msg)
                return redirect('/shop.html')

    # ====== end shop-single ======

    # ====== cart ======
    if load_template == 'cart.html':
        if not request.user.is_authenticated:
            return login_sek(request)

        cart = Cart.objects.filter(user=request.user).values('cart_id', 'product__name', 'product',
                                                             'product__price', 'product__image',
                                                             'quantity', 'price_total',
                                                             'product__size__name')

        for item in cart:
            item['price_total'] = f"{int(item['price_total']):,}"
            item['product__price'] = f"{int(item['product__price']):,}"

        context['cart_info'] = cart
        if request.POST:
            if 'delete_cart' in request.POST:
                cart_id = request.POST.get('delete_cart')
                cart = Cart.objects.get(cart_id=cart_id)
                cart.delete()
                return redirect('/cart.html')

            if 'buy' in request.POST:
                data = request.POST
                data_list, items, price = [], [], []

                for item in data.getlist('checkbox'):
                    index = data.getlist('product_id').index(item)

                    items.append(int(data.getlist('product-quanity')[index]))
                    price.append(int(data.getlist('product-price')[index].replace(',', '')))

                    data_list.append(
                        {
                            'id': data.getlist('product_id')[index],
                            'name': data.getlist('product-title')[index],
                            'cart_id': data.getlist('cart-id')[index],
                            'price': data.getlist('product-price')[index],
                            'size': data.getlist('product-size')[index],
                            'quantity': data.getlist('product-quanity')[index],
                            'img': data.getlist('product-img')[index],
                        }
                    )

                request.session['data'] = data_list
                request.session['quantity'] = sum(items)
                request.session['total'] = f"{np.multiply(price, items).sum():,}"

                return redirect('/checkout.html')
    # ============ end cart =================

    # ====================== checkout ====================
    if load_template == 'checkout.html':
        if request.POST:

            unique_code = uuid.uuid1()
            # ---------- raja ongkir ----------
            # print(request.POST)

            with open(os.path.join(PATH, 'raja_ongkir_city/raja_ongkir_city.json')) as file:
                city_data = json.load(file)

            city = request.POST.get('city').lower()
            province = request.POST.get('province').lower()

            city_id = None
            for item in city_data['rajaongkir']['results']:
                if item.get('city_name').lower() == city and item.get('province').lower() == province:
                    city_id = item.get('city_id')

            service = None
            description = None
            cost = 0
            etd = None

            if city_id:
                # it from api
                # header = {'key': '4184d0c19d63cd3002f41c9f6fec9c9b',
                #           'content-type': "application/x-www-form-urlencoded"}
                # payload = f"origin=501&destination={city_id}&weight=1700&courier=jne"
                #
                # response_cost = requests.post('http://api.rajaongkir.com/starter/cost', data=payload, headers=header)
                # data = response_cost.json()

                # detail_data = data['rajaongkir']['results'][0]['costs'][1]

                data = check_ongkir(city_id)[0]

                # print(response_cost.status_code)

                detail_data = data['costs'][1] if len(data['costs']) > 0 else data.get('costs')[0]

                service = detail_data.get('service')
                description = detail_data.get('description')
                cost = detail_data['cost'][0].get('value')
                etd = detail_data['cost'][0].get('etd')

            # ---------- end raja ongkir ----------

            # ---------- sandbox midtrans ----------
            transaction = get_midtrans(request, cost, order_id=unique_code)
            # status_response = api_client.transactions.notification(mock_notification)
            # ---------- end midtrans ----------

            # ------------ save to order model ------------
            for i, item in enumerate(request.POST.getlist('product-id')):
                product = Products.objects.get(product_id=item)
                price = int(request.POST.getlist('product-price')[i].replace(',', ''))
                qty = int(request.POST.getlist('product-qty')[i])

                save_order = Order(
                    product=product,
                    user=request.user,
                    unique_code=unique_code,
                    quantity=request.POST.getlist('product-qty')[i],
                    gross_amount=(price * qty),
                    status='pending'
                )
                save_order.save()
                # ------------ end save ------------

                # ------------ update stock product ------------
                product.stock = product.stock - qty
                product.save()
                # ------------ end update stock product ------------

                # ------------ save to Shipment model ------------
                Shipment.objects.create(
                    user=request.user,
                    city=request.POST.get('city'),
                    product_order=save_order,
                    service=service,
                    description=description,
                    cost=cost,
                    etd=etd
                )
                # ------------ end save ------------

                # ------------ delete cart ------------
                if 'cart-id' in request.POST:
                    delete_cart = Cart.objects.get(cart_id=request.POST.getlist('cart-id')[i])
                    delete_cart.delete()
                # ------------ end delete cart ------------

            return redirect(transaction['redirect_url'])

            # ---- load by javascript ----------
            # request.session['transaction_token'] = transaction['token']
            # return redirect('/midtrans-test.html')

    # ====================== end checkout ====================
    # ====================== Profile ====================
    if load_template == 'profile.html':
        if not request.user.is_authenticated:
            return login_sek(request)

        if request.POST:
            info_user = CustomUser.objects.get(username=request.user)
            data = request.POST

            info_user.first_name = data.get('first_name')
            info_user.last_name = data.get('last_name')
            info_user.full_name = data.get('full_name')
            info_user.phone_number = data.get('phone_number')
            info_user.email = data.get('email')
            info_user.address = data.get('address')
            info_user.city = data.get('city')
            info_user.province = data.get('province')
            info_user.zip_code = data.get('zip_code')
            info_user.country = data.get('country')

            info_user.save()

            msg = 'Edit Profile Success!'
            messages.success(request, msg)
            return redirect('/profile.html')

    # ====================== End Profile ====================
    # ====================== Order ====================
    if load_template == 'order.html':
        if not request.user.is_authenticated:
            return login_sek(request)

        # update status every load this page

        unique_code = Order.objects.filter(user=request.user).order_by('-order_id').values('unique_code',
                                                                                           'order_id',
                                                                                           'product__name', 'quantity',
                                                                                           'gross_amount',
                                                                                           'payment__gross_amount',
                                                                                           'product__image',
                                                                                           'product__price',
                                                                                           'product__brand__name',
                                                                                           'status',
                                                                                           'product__size__name',
                                                                                           'product__category__name',
                                                                                           'shipment__city',
                                                                                           'shipment__service',
                                                                                           'shipment__cost',
                                                                                           'shipment__etd',
                                                                                           'payment__transaction_time',
                                                                                           'payment__payment_type',
                                                                                           )

        testing = defaultdict(list)
        for item in unique_code:

            testing[item['unique_code']].append(
                {
                    'order_id': item['order_id'],
                    'product__brand__name': item['product__brand__name'],
                    'product__category__name': item['product__category__name'],
                    'product__image': item['product__image'],
                    'product__name': item['product__name'],
                    'product__size__name': item['product__size__name'],
                    'quantity': item['quantity'],
                    'product__price': item['product__price'],
                }
            )

            try:
                api_client = midtransclient.CoreApi(
                    is_production=False,
                    server_key='SB-Mid-server-PWpPema0nMJ82yYKbWIoYvA2',
                    client_key='SB-Mid-client-7OJDLb4f29FXBV4o'
                )

                # udpate total price
                # status_response = api_client.transactions.status(item['unique_code'])
                # update_order = Order.objects.get(order_id=item['order_id'])
                # update_order.gross_amount = int(status_response.get('gross_amount'))
                # update_order.save()
                # end update

                if item['status'] == 'pending':

                    status_response = api_client.transactions.status(item['unique_code'])

                    # update status base on midtrans
                    update_order = Order.objects.get(order_id=item['order_id'])
                    update_order.status = status_response.get('transaction_status')
                    update_order.save()

                    # update or create transaction payment on model
                    obj, created = Payment.objects.update_or_create(
                        order=Order.objects.get(order_id=item['order_id']),
                        defaults={
                            'transaction_time': status_response.get('transaction_time'),
                            'gross_amount': int(status_response.get('gross_amount').replace('.00', '')),
                            'payment_type': status_response.get('payment_type')
                        }
                    )

                    item['gross_amount'] = f"{item['gross_amount']:,}"
                    item['short_unique_code'] = item['unique_code'][:8] + "..."
                    item['transaction_time'] = status_response['transaction_time']
                    item['payment_type'] = status_response['payment_type']
                    item['product__price'] = f"{int(item['product__price']):,}"


            except Exception as e:
                err = e

        for item in unique_code:

            unique = item['unique_code']
            item['object'] = testing[unique]

        df_unique_code = pd.DataFrame(unique_code)
        df_unique_code.drop_duplicates(subset='unique_code', inplace=True)
        df_unique_code.fillna(" ", inplace=True)

        custom_unique_code = df_unique_code.to_dict(orient='records')

        context['profile_detail'] = custom_unique_code

        context['filter'] = set([item['status'] for item in unique_code])

        if request.GET.get('filter'):
            query = request.GET.get('filter')
            context['profile_detail'] = [item for item in unique_code if item['status'] == query]

        if 'exportPDF' in request.GET:
            load_template = f'report/cetak_laporan_customer.html'
            id_order = request.GET.get('exportPDF')
            data = None

            for item in custom_unique_code:
                if item.get('unique_code') == id_order:
                    data = item

            context['profile_detail'] = data

            context['segment'] = load_template
            html_template = loader.get_template(load_template)
            return HttpResponse(html_template.render(context, request))

        # check if user click buy again this product
        if 'product_name' in request.GET:
            product_name = request.GET.get('product_name')
            list_product = query_get_product(param=product_name)
            context['list_product'] = list_product
            load_template = 'shop.html'

        # ------------- refund product --------------
        # refund a transaction (not all payment channel allow refund via API)
        if 'refund' in request.POST:
            unique_code = request.POST.get('id_refund')

            # data_harga = request.POST.get('price_refund')
            # price = re.sub(r',|\.', '', data_harga)
            reason = request.POST.get('reason')

            try:
                order = Order.objects.filter(unique_code=unique_code).values('order_id',
                                                                             'product__price')

            except Exception as e:
                err = e
                print(err)
            else:
                for item in order:
                    obj_order = Order.objects.get(order_id=item['order_id'])
                    refund = RefundProduct(
                        order=obj_order,
                        price=item['product__price'],
                        reason=reason,
                    )
                    refund.save()
                    obj_order.status = 'refunded'
                    obj_order.save()

                link = request.build_absolute_uri('/contact.html')
                msg = "Produk bisa dikembalikan langsung pada toko Pritohelmet. " \
                      f"<a href='{link}'>Detail alamat</a>"
                messages.success(request, msg)

            return redirect('/order.html')

    context['segment'] = load_template
    html_template = loader.get_template(load_template)
    return HttpResponse(html_template.render(context, request))


# -------------------------- function preprocessing data --------------------------

def query_get_product(param=None, field=None):
    """
    param : brand name, size name, etc
    field : field / column name
    """

    # get data from model (database)
    if param is not None and field is not None:

        if field == 'category__name':
            data_raw = Products.objects.filter(category__name=param).values('product_id', 'name', 'price', 'size__name',
                                                                            'image')
        elif field == 'brand__name':
            data_raw = Products.objects.filter(brand__name=param).values('product_id', 'name', 'price', 'size__name',
                                                                         'image')
        elif field == 'size__name':
            data_raw = Products.objects.filter(size__name=param).values('product_id', 'name', 'price', 'size__name',
                                                                        'image')
        elif field == 'size__size_category__name':
            data_raw = Products.objects.filter(size__size_category__name=param).values('product_id', 'name', 'price',
                                                                                       'size__name',
                                                                                       'image')

    elif param is not None and field is None:
        data_raw = Products.objects.filter(Q(name__icontains=param) |
                                           Q(price__icontains=param) |
                                           Q(desc__icontains=param) |
                                           Q(size__size_category__name__icontains=param)).values('name', 'product_id',
                                                                                                 'price',
                                                                                                 'size__name', 'image')

    else:
        data_raw = Products.objects.values('product_id', 'name', 'price', 'size__name', 'image')

    # preprocess data raw to clean
    list_product = defaultdict(lambda: defaultdict(list))
    for item in data_raw:
        list_product[item['name']]['product_id'].append(item['product_id'])
        list_product[item['name']]['price'].append(int(item['price']))
        list_product[item['name']]['size'].append(item['size__name'])
        list_product[item['name']]['image'].append(item['image'])

    # preprocess clean data for send to view
    output = [{'name': key, 'product_id': ' '.join(str(item) for item in value.get('product_id')),
               'price': f'{sorted(value.get("price"))[0]:,} s/d {sorted(value.get("price"))[-1]:,}' if len(
                   value.get('price')) > 1 else f'{sorted(value.get("price"))[0]:,}',
               'size': '/'.join(sorted(value.get('size'))),
               'image': value.get('image')[0]} for key, value in list_product.items()]
    return output


def details_product(param):
    raw_detail_product = Products.objects.filter(name=param).values('name', 'product_id', 'price', 'stock', 'desc',
                                                                    'size__name', 'category__name',
                                                                    'brand__name', 'image')
    # preprocess data raw to clean
    list_product = defaultdict(lambda: defaultdict(list))
    for item in raw_detail_product:
        list_product[item['name']]['price'].append(int(item['price']))
        list_product[item['name']]['product_id'].append(item['product_id'])
        list_product[item['name']]['stock'].append(item['stock'])
        list_product[item['name']]['desc'].append(item['desc'])
        list_product[item['name']]['size'].append(item['size__name'])
        list_product[item['name']]['category'].append(item['category__name'])
        list_product[item['name']]['brand'].append(item['brand__name'])
        list_product[item['name']]['image'].append(item['image'])
    return list_product


def item_shop_single(raw_detail, related_product=True):
    img = [image for key, value in raw_detail.items() for image in value.get('image')]
    context = {'available_size': [{'size': item} for key, value in raw_detail.items() for item in value.get('size')],
               'images': [img[i:i + 3] for i in range(0, len(img), 3)],
               'product_id': [item.get('product_id')[0] for item in raw_detail.values()][0],
               'brand': [item.get('brand')[0] for item in raw_detail.values()][0],
               'price': [f'{sorted(value["price"])[0]:,} s/d {sorted(value["price"])[-1]:,}'
                         if len(value['price']) > 1 else f'{sorted(value["price"])[0]:,}'
                         for key, value in raw_detail.items()][0],
               'description': [item.get('desc')[0] for item in raw_detail.values()][0],
               'available_stock': ' / '.join([f'{SIZE_DICT[size]} : {stock}' for key, value in raw_detail.items()
                                              for size, stock in zip(value.get('size'), value.get('stock'))])}

    if related_product:
        context['related_product'] = query_get_product(list(raw_detail.keys())[0].split(' ')[0])

    return context


def add_to_cart_model(req, product):
    quantity = int(req.POST.get('product-quanity')) if req.POST else 1
    Cart.objects.create(
        product=Products.objects.get(product_id=product.product_id),
        user=req.user,
        quantity=quantity,
        date=datetime.now(),
        price_total=int(product.price) * quantity
    )


def update_cart_model(req, cart, product):
    quantity = int(req.POST.get('product-quanity')) if req.POST else 1
    cart.quantity = quantity
    cart.date = datetime.now()
    cart.price_total = int(product.price) * quantity
    cart.save()


def total_product_in_cart(request):
    if request.user.is_authenticated:
        return len(Cart.objects.filter(user=request.user))
    return 0


def total_product_buy(request):
    if request.user.is_authenticated:
        return len(Order.objects.filter(user=request.user))
    return 0


# payment gateway function
def get_midtrans(request, cost, order_id):
    snap = midtransclient.Snap(
        is_production=False,
        server_key='SB-Mid-server-PWpPema0nMJ82yYKbWIoYvA2',
        client_key='SB-Mid-client-7OJDLb4f29FXBV4o'
    )

    cost = 0 if cost is None else cost

    item_detail = [
        {
            "id": request.POST.getlist('product-id')[i],
            "price": int(request.POST.getlist('product-price')[i].replace(',', '')),
            "quantity": request.POST.getlist('product-qty')[i],
            "name": request.POST.getlist('product-name')[i],
            "brand": request.POST.getlist('product-price')[i],
        } for i in range(len(request.POST.getlist('product-id')))
    ]

    biaya_raja_ongkir = {
        "id": request.POST.get('product-id'),
        "price": cost,
        "quantity": 1,
        "name": 'JNE REG Shipment Cost',
    }
    item_detail.append(biaya_raja_ongkir)
    param = {
        "transaction_details": {
            "order_id": f"{order_id}",
            "gross_amount": int(request.POST.get('product-total').replace(',', '')) + cost
        }, "item_details": item_detail,
        "customer_details": {
            "first_name": request.POST.get('name'),
            "email": request.POST.get('email'),
            "billing_address": {
                "first_name": request.POST.get('name'),
                "email": request.POST.get('email'),
                "address": request.POST.get('address'),
                "postal_code": request.POST.get('zipcode'),
                "city": request.POST.get('city'),
                "province": request.POST.get('province'),
                "country_code": "IDN"
            },
            "shipping_address": {
                "first_name": request.POST.get('name'),
                "email": request.POST.get('email'),
                "address": request.POST.get('address'),
                "postal_code": request.POST.get('zipcode'),
                "city": request.POST.get('city'),
                "province": request.POST.get('province'),
                "country_code": "IDN"
            }
        },

        "enabled_payments": ["credit_card", "mandiri_clickpay", "cimb_clicks", "bca_klikbca", "bca_klikpay",
                             "bri_epay", "echannel", "indosat_dompetku", "mandiri_ecash", "permata_va",
                             "bca_va", "gopay",
                             "bni_va", "other_va", "kioson", "indomaret", "gci", "danamon_online"],
        "bca_va": {
            "va_number": "12345678911",
            "free_text": {
                "inquiry": [
                    {
                        "en": "text in English",
                        "id": "text in Bahasa Indonesia"
                    }
                ],
                "payment": [
                    {
                        "en": "text in English",
                        "id": "text in Bahasa Indonesia"
                    }
                ]
            }
        },
        "bni_va": {
            "va_number": "12345678"
        },
        "permata_va": {
            "va_number": "1234567890",
            "recipient_name": "SUDARSONO"
        },
        "callbacks": {
            "finish": request.build_absolute_uri('/shop.html')
        },
        "expiry": {
            "start_time": str(datetime.now().replace(microsecond=0)) + "+0700",
            "unit": "minute",
            "duration": 60 * 24
        },
    }
    # create transaction
    transaction = snap.create_transaction(param)
    return transaction


def login_sek(request):
    messages.info(request, 'You must login first for use this feature!')
    return redirect('login')


def check_ongkir(city_id):
    with open(os.path.join(PATH, 'raja_ongkir_city/shipment_cost_jogja_to_all.json')) as file:
        data = json.load(file)

        return data[city_id]

# -------------------------- end function preprocessing data --------------------------
