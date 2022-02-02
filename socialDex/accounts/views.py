from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm,UserEditForm,LoginForm
from django.contrib.auth import login,authenticate
from django.contrib import messages
from app.models import Profile,Order
from django.utils import timezone
import random
import json
from web3 import Web3

ganache_url='http://127.0.0.1:7545'
web3 = Web3(Web3.HTTPProvider(ganache_url))
web3.eth.defaultAccount= web3.eth.accounts[0]
Faucet = web3.eth.defaultAccount
print(web3.isConnected())

#CONTRACT TOKEN-ERC20
abi = json.loads('[{"inputs":[],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[],"name":"admin","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"subtractedValue","type":"uint256"}],"name":"decreaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"addedValue","type":"uint256"}],"name":"increaseAllowance","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"sender","type":"address"},{"internalType":"address","name":"recipient","type":"address"},{"internalType":"uint256","name":"amount","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"nonpayable","type":"function"}]')
address = Web3.toChecksumAddress('0x8247E9b38E5AcED0Ee4FBBc1dc9c26712372864B')
contract = web3.eth.contract(address=address,abi=abi)

@login_required()
def ip_control_view(request):

    return render(request, 'accounts/ip_control.html', )


def getIpAdd(request):
    try:
        x_forward = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forward:
            ip = x_forward.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
    except:
        ip = ""
    return ip


def login_view(request):
    ip_address = getIpAdd(request)
    initial_data = {
        'ip_address': ip_address,
    }
    form = LoginForm(request.POST or None)
    if form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)
        if user != None:
            login(request, user)
            try:
                user_info = Profile.objects.get(user=user)
                user_info.last_login = timezone.now()
            except:
                user_info = Profile.objects.create(user=user)
                user_info.last_login = timezone.now()
            user_info.save()

            ip_address = getIpAdd(request)
            ip_list = []
            if ip_address not in user_info.ips:
                ip_list.append(ip_address)
                user_info.ips = ip_list
                user_info.save()

            if ip_address != user_info.ip_address:
                user_info.ip_address = ip_address
                user_info.save()
                return redirect(f"accounts:ip-control")

            else:
                return redirect('accounts:profile',user.pk)
    else:
        form = LoginForm(initial=initial_data)
    return render(request, 'accounts/login.html',{'form': form})





def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():


            address= form.cleaned_data.get('address')
            if Profile.objects.filter(token_address=address).exists():
                messages.error(request,'This address is already in the database')
                return redirect('accounts:register')
            user = form.save()
            user.refresh_from_db() #stiamo andando a ricaricare l'istanza del profilo che è stata generata dal signals

            newUser = Profile(user=user)
            rand= int(random.uniform(20, 40))

            newUser.usd_amount= int(random.uniform(1000, 2000))

            newUser.ip_address=getIpAdd(request)
            newUser.last_login=timezone.now()
            newUser.ips.append(getIpAdd(request))
            newUser.token_address=address
            #transaction
            tx = contract.functions.transfer(newUser.token_address,rand).transact({'from': Faucet})
            newUser.token_amount = contract.functions.balanceOf(newUser.token_address).call()

            newUser.save()


            row_password = form.cleaned_data.get('password1')
            user = authenticate(username=user.username,password=row_password)
            login(request,user)
            return redirect('accounts:profile',user.pk)
    else:
        form = RegistrationForm()
        return render(request, 'accounts/registration.html', {'form': form})

    return render(request,'accounts/registration.html',{'form': form})

@login_required()
def profile(request,id):
    user_profile = get_object_or_404(Profile, user_id=id)
    profile_pocket = Profile.objects.get(user=request.user)
    my_purchase_orders_list = Order.objects.filter(profile=user_profile,type='buy').order_by('price')
    my_sale_orders_list = Order.objects.filter(profile=user_profile,type='sell').order_by('price')

    mp_list=Order.objects.filter(profile=user_profile,type='buy',status='close').order_by('price')
    sm_list=Order.objects.filter(profile=user_profile,type='sell',status='close').order_by('price')
    profit_buy=[]
    profit_sell=[]
    for purchase_list in mp_list:
        depth = purchase_list.quantity * purchase_list.price
        profit_buy.append(depth)
    for sale_list in sm_list:
        depth = sale_list.quantity * sale_list.price
        profit_sell.append(depth)
    profile_pocket.profit = sum(profit_sell) - sum(profit_buy)
    profile_pocket.save()

    return render(request, 'accounts/profile.html', {'user_profile': user_profile,'profile_pocket': profile_pocket,
                                                     'my_purchase_orders_list':my_purchase_orders_list,
                                                     'my_sale_orders_list':my_sale_orders_list,})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)

        if user_form.is_valid() :
            user_form.save()

            messages.success(request,'Your profile has been successfully edited')
            return redirect('accounts:profile', request.user.pk)
        else:
            messages.error(request,'The data entered is not valid',extra_tags='danger')
    else:
        user_form = UserEditForm(instance=request.user)

    return render(request,'accounts/edit.html',{'user_form': user_form})
