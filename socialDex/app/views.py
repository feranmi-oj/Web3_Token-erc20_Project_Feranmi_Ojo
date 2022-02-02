from web3 import Web3
import json
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from .models import Order, Profile
from .forms import Order_Form
from bson import ObjectId



ganache_url='http://127.0.0.1:7545'
web3 = Web3(Web3.HTTPProvider(ganache_url))
web3.eth.defaultAccount= web3.eth.accounts[0]
print(web3.isConnected())

abi = json.loads('[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[],"name":"admin","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]')

address = Web3.toChecksumAddress('0x8247E9b38E5AcED0Ee4FBBc1dc9c26712372864B')

contract = web3.eth.contract(address=address,abi=abi)



def home_view(request):
    return render(request, 'app/base.html', )

@login_required()
def order_exchange_view(request):
    #I am calling the list of FeroToken purchases and sales that are open right now
    purchase_orders_list = Order.objects.filter(status='open',type='buy').order_by('-price')
    sale_orders_list = Order.objects.filter(status='open',type='sell').order_by('-price')
    # Orders lists
    if request.method == 'POST':
        if request.POST.get('buy'):

            # Buy Order
            form = Order_Form(request.POST or None)
            if form.is_valid():

                status='open'
                type='buy'
                price = form.cleaned_data.get('price')
                quantity = form.cleaned_data.get('quantity')
                profile_wallet = Profile.objects.get(user=request.user)

                if price <=0.0:
                    messages.error(request, 'Cannot put a price lower than 0')
                    return redirect('app:order')
                if quantity <= 0.0:
                    messages.error(request, 'Cannot put a quantity lower than 0')
                    return redirect('app:order')


                if profile_wallet.usd_amount >= price:
                    # Order creation
                    new_buy_order = Order.objects.create(profile=profile_wallet,
                                                         status=status,
                                                         token_address=profile_wallet.token_address,
                                                         type=type,
                                                         price=price,
                                                         quantity=quantity,
                                                         modified=timezone.now())
                    new_buy_order.save()
                    messages.success(request, f'Your  purchase order of {new_buy_order.quantity} FTN for {new_buy_order.price} ,  is successfully added to the Order Book! || Status: {new_buy_order.status}')
                    # Order matching
                    if sale_orders_list.exists():
                        for sale_order in sale_orders_list:
                                if sale_order.price <= new_buy_order.price :

                                    messages.info(request, f'Search for the best sales order')
                                    messages.info(request, f'Partner found! Tokenaddress:{sale_order.token_address}')
                                    messages.success(request,
                                                     f'He wants to sell {sale_order.quantity} FTN for {sale_order.price} $')
                                    messages.info(request, 'Start of the  exchange')

                                    if sale_order.quantity == new_buy_order.quantity:

                                        actual_ferotoken = profile_wallet.token_amount
                                        #Buy order close
                                        new_buy_order.quantity = sale_order.quantity
                                        new_buy_order.status='close'
                                        new_buy_order.save()
                                        #Transaction
                                        contract.functions.transfer(new_buy_order.token_address, new_buy_order.quantity).transact({'from': sale_order.token_address})
                                        profile_wallet.token_amount=contract.functions.balanceOf(new_buy_order.token_address).call()

                                        profile_wallet.usd_amount-=(sale_order.price*sale_order.quantity)
                                        profile_wallet.save()

                                        messages.success(request,f'Your buy order with Token address: {new_buy_order.token_address}. || Status: {new_buy_order.status}.')
                                        messages.success(request, f'|| FTN before exchange: {actual_ferotoken}; || FTNafter exchange: {profile_wallet.token_amount};')

                                        # Sell order can close.
                                        sell_order = Order.objects.get(_id=sale_order._id)
                                        profile_s= Profile.objects.get(user= sell_order.profile.user)
                                        profile_s.usd_amount+=(sale_order.price*sale_order.quantity)

                                        profile_s.save()
                                        sale_order.status = 'close'
                                        sale_order.save()

                                        messages.success(request, f'Sell order with Token address: {sale_order.token_address}. || Status: {sale_order.status}.')
                                        messages.success(request, f' The User who Sold has Received  successfully {sale_order.price}$ *{sale_order.quantity} .')
                                        messages.info(request, 'The FeroToken exchange has been totally executed! Congratulations!')
                                        return redirect('app:order')
                                    elif sale_order.quantity > new_buy_order.quantity :
                                        actual_ferotoken = profile_wallet.token_amount
                                        #Buy order close
                                        new_buy_order.price = sale_order.price
                                        new_buy_order.status = 'close'
                                        new_buy_order.save()
                                        #Transaction
                                        contract.functions.transfer(new_buy_order.token_address, new_buy_order.quantity).transact({'from': sale_order.token_address})
                                        profile_wallet.token_amount = contract.functions.balanceOf(new_buy_order.token_address).call()
                                        profile_wallet.usd_amount-=(new_buy_order.price*new_buy_order.quantity)
                                        profile_wallet.save()
                                        messages.success(request,
                                                         f'Your buy order with Token address: {new_buy_order.token_address}. || Status: {new_buy_order.status}.')
                                        messages.success(request,
                                                         f'|| FTN before exchange: {actual_ferotoken}; || FTN after exchange: {profile_wallet.token_amount};')

                                        sale_order.quantity-=new_buy_order.quantity
                                        sale_order.save()

                                        sell_order = Order.objects.get(_id=sale_order._id)
                                        profile_s = Profile.objects.get(user=sell_order.profile.user)
                                        profile_s.usd_amount += (new_buy_order.price*new_buy_order.quantity)

                                        profile_s.save()

                                        messages.success(request,
                                                         f'Sell order with Token address: {sale_order.token_address}. || Status: {sale_order.status}.')
                                        messages.success(request,
                                                         f' The User who Sold has Received  successfully {new_buy_order.price}$ *{new_buy_order.quantity}.')
                                        messages.info(request,
                                                      'The bitcoin exchange has been totally executed! Congratulations!')



                                    elif sale_order.quantity < new_buy_order.quantity:
                                        actual_ferotoken = profile_wallet.token_amount

                                        new_buy_order.quantity -= sale_order.quantity
                                        new_buy_order.save()
                                        #Transaction
                                        contract.functions.transfer(new_buy_order.token_address, sale_order.quantity).transact({'from': sale_order.token_address})
                                        profile_wallet.token_amount = contract.functions.balanceOf(new_buy_order.token_address).call()

                                        profile_wallet.usd_amount-=(sale_order.price*sale_order.quantity)
                                        profile_wallet.save()
                                        messages.success(request,
                                                         f'Your buy order with Token address: {new_buy_order.token_address}. || Status: {new_buy_order.status}.')
                                        messages.success(request,
                                                         f'|| FTN before exchange: {actual_ferotoken}; || FTN after exchange: {profile_wallet.token_amount};')

                                        sale_order.status= 'close'
                                        sale_order.save()

                                        sell_order = Order.objects.get(_id=sale_order._id)
                                        profile_s = Profile.objects.get(user=sell_order.profile.user)
                                        profile_s.usd_amount += (sale_order.price*sale_order.quantity)

                                        profile_s.save()

                                        messages.success(request,
                                                         f'Sell order with Token address: {sale_order.token_address}. || Status: {sale_order.status}.')
                                        messages.success(request,
                                                         f' The User who Sold has Received  successfully {sale_order.price} $ * {sale_order.quantity}.')
                                        messages.info(request,
                                                      'The bitcoin exchange has been totally executed! Congratulations!')


                                    else:
                                        return redirect('app:order')
                        return redirect('app:order')
                    else:
                        return redirect('app:order')
                else:
                    messages.error(request, 'Your balance is not enough.')
            else:
                messages.error(request, 'Order can not have negative values!')

        elif request.POST.get('sell'):
            form = Order_Form(request.POST or None)
            if form.is_valid():
                type='sell'
                status = 'open'
                price = form.cleaned_data.get('price')
                quantity = form.cleaned_data.get('quantity')
                profile_wallet = Profile.objects.get(user=request.user)

                if price <= 0.0:
                    messages.error(request, 'Cannot put a price lower than 0')
                    return redirect('app:order')
                if quantity <= 0.0:
                    messages.error(request, 'Cannot put a quantity lower than 0')
                    return redirect('app:order')

                if profile_wallet.token_amount >= quantity:
                    profile_wallet.save()
                    # Order creation
                    new_sell_order = Order.objects.create(profile=profile_wallet,
                                                          token_address=profile_wallet.token_address,
                                                          type=type,
                                                          status=status,
                                                          price=price,
                                                          quantity=quantity,
                                                          modified=timezone.now())
                    messages.success(request,
                                     f'Your sales order of {new_sell_order.quantity} FTN for {new_sell_order.price},  is successfully added to the Order Book! || Status:{new_sell_order.status}')
                    # Order matching
                    if purchase_orders_list.exists():

                        for buy_open_order in purchase_orders_list:
                                if buy_open_order.price >= new_sell_order.price :

                                    messages.info(request, f'Search for the best purchase order')
                                    messages.info(request, f'Partner found! purchase Token address:{buy_open_order._id}')
                                    messages.success(request,
                                                     f'He wants to buy {buy_open_order.quantity} FTN for {buy_open_order.price} $')
                                    messages.info(request, 'Start of the exchange')
                                    if buy_open_order.quantity == new_sell_order.quantity:
                                        # Sell order can close.
                                        actual_usd = profile_wallet.usd_amount
                                        new_sell_order.price = buy_open_order.price
                                        new_sell_order.status = 'close'
                                        new_sell_order.save()
                                        profile_wallet.usd_amount += (new_sell_order.price * new_sell_order.quantity)
                                        profile_wallet.save()

                                        messages.success(request,
                                                         f'Sell order with Token address: {new_sell_order.token_address}. || Status: {new_sell_order.status}.')
                                        messages.success(request,
                                                         f'|| USD before exchange: {actual_usd}; || USD after exchange: {profile_wallet.usd_amount};')

                                        profile_b = Profile.objects.get(user=buy_open_order.profile.user)
                                        #Transaction
                                        contract.functions.transfer(buy_open_order.token_address, new_sell_order.quantity).transact({'from': buy_open_order.token_address})
                                        profile_b.token_amount=contract.functions.balanceOf(buy_open_order.token_address).call()
                                        profile_b.usd_amount -= (buy_open_order.price * buy_open_order.quantity)
                                        profile_b.save()
                                        buy_open_order.status = 'close'
                                        buy_open_order.save()
                                        messages.success(request,
                                                         f'Buy order with Token address: {buy_open_order.token_address}. || Status: {buy_open_order.status}.')
                                        messages.success(request, f'The User who purchased has Received  successfully {new_sell_order.quantity} FTN in wei.')
                                        messages.info(request,
                                                      'The FeroToken exchange has been totally executed! Congratulations!')
                                        return redirect('app:order')

                                    elif buy_open_order.quantity > new_sell_order.quantity:
                                        actual_usd = profile_wallet.usd_amount
                                        new_sell_order.price = buy_open_order.price
                                        new_sell_order.status = 'close'
                                        new_sell_order.save()

                                        profile_wallet.usd_amount+=(new_sell_order.price*new_sell_order.quantity)
                                        profile_wallet.save()
                                        messages.success(request,
                                                         f'Sell order with Token address: {new_sell_order.token_address}. || Status: {new_sell_order.status}.')
                                        messages.success(request,
                                                         f'|| USD before exchange: {actual_usd}; || USD after exchange: {profile_wallet.usd_amount};')

                                        buy_open_order.quantity -= new_sell_order.quantity
                                        buy_open_order.save()
                                        if buy_open_order.quantity == 0.00:
                                            buy_open_order.status="close"
                                            buy_open_order.save()

                                        profile_b = Profile.objects.get(user=buy_open_order.profile.user)
                                        #transaction
                                        contract.functions.transfer(buy_open_order.token_address, new_sell_order.quantity).transact({'from': new_sell_order.token_address})
                                        profile_b.token_amount=contract.functions.balanceOf(buy_open_order.token_address).call()
                                        profile_b.usd_amount -= (buy_open_order.price*new_sell_order.quantity)
                                        profile_b.save()
                                        messages.success(request,
                                                         f'Buy order with Token address: {buy_open_order.token_address}. || Status: {buy_open_order.status}.')
                                        messages.success(request,
                                                         f'The User who purchased has Received  successfully {new_sell_order.quantity} FTN in Wei.')
                                        messages.info(request,
                                                      'The FeroToken exchange has been totally executed! Congratulations!')


                                    elif buy_open_order.quantity < new_sell_order.quantity:
                                        actual_usd= profile_wallet.usd_amount
                                        new_sell_order.quantity -= buy_open_order.quantity
                                        new_sell_order.save()
                                        if new_sell_order.quantity==0.00:
                                            new_sell_order.status= 'close'
                                            new_sell_order.save()
                                        profile_wallet.usd_amount += (buy_open_order.price *buy_open_order.quantity)
                                        profile_wallet.save()

                                        messages.success(request,
                                                         f'Sell order with Token address: {new_sell_order.token_address}. || Status: {new_sell_order.status}.')
                                        messages.success(request,
                                                         f'|| USD before exchange: {actual_usd}; || USD after exchange: {profile_wallet.usd_amount};')



                                        profile_b = Profile.objects.get(user=buy_open_order.profile.user)
                                        #transaction
                                        contract.functions.transfer(buy_open_order.token_address, buy_open_order.quantity).transact({'from': new_sell_order.token_address})
                                        profile_b.token_amount=contract.functions.balanceOf(buy_open_order.token_address).call()
                                        profile_b.usd_amount -= (buy_open_order.price *buy_open_order.quantity)
                                        profile_b.save()
                                        buy_open_order.status = 'close'
                                        buy_open_order.save()
                                        messages.success(request,
                                                         f'Buy order with Token address: {buy_open_order.token_address}. || Status: {buy_open_order.status}.')
                                        messages.success(request,
                                                         f'The User who purchased has Received  successfully {buy_open_order.quantity} FTN in Wei.')
                                        messages.info(request,
                                                      'The FeroToken exchange has been totally executed! Congratulations!')

                                    else:
                                        return redirect('app:order')
                        return redirect('app:order')
                    else:
                        return redirect('app:order')
                else:
                    messages.error(request, 'Your balance is not enough.')
            else:
                messages.error(request, 'Order can not have negative values!')

    form = Order_Form()
    profile_pocket= Profile.objects.get(user=request.user)
    return render(request, 'app/page_exchange.html', {'form': form,
                                                      'purchase_orders_list': purchase_orders_list,
                                                      'sale_orders_list': sale_orders_list,
                                                      'profile_pocket': profile_pocket,}
                                                     )


#Return file Json
def profit(request):
    response = []
    profile = Profile.objects.get(user=request.user)
    response.append(
        {
            'User ID': str(profile._id),
            'Name': profile.user.first_name,
            'Surname': profile.user.last_name,
            'Balance': profile.usd_amount,
            'FeroToken(FTN)': profile.token_amount,
            'Profit': profile.profit
        }
    )
    return JsonResponse(response, safe=False)




#view for delete order
def delete_order_view(request,id):

    if request.method == 'POST':
        oll=Order.objects.filter(_id=ObjectId(id)).first()
        if oll.type=='buy' :
            p_order = Order.objects.filter(_id=ObjectId(id)).first()
            p_order.delete()
            messages.success(request, 'Your purchase order has been successfully deleted!')
            return redirect('app:order')
        elif oll.type=='sell':
            s_order = Order.objects.filter(_id=ObjectId(id)).first()
            profile_pocket = Profile.objects.get(user=s_order.profile.user)
            profile_pocket.token_amount += s_order.quantity
            profile_pocket.save()
            s_order.delete()
            messages.success(request, 'Your sell order has been deleted successfully!')
            return redirect('app:order')

    return render(request, 'app/order_delete.html')
