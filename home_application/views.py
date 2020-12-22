# -*- coding: utf-8 -*-
from django.shortcuts import render
from blueking.component.shortcuts import get_client_by_request, get_client_by_user

# 开发框架中通过中间件默认是需要登录态的，如有不需要登录的，可添加装饰器login_exempt
# 装饰器引入 from blueapps.account.decorators import login_exempt
from home_application.getJobDetails import inits
from home_application.indexTime import getBizList


def home(request):
    """
    首页
    """
    return render(request, 'home_application/home.html')


def contact(request):
    """
    联系我们
    """
    return render(request, 'home_application/contact.html')

def getBizLists(request):
    """
    作业
    """
    getBizList(request)
    return render({'a': 'a'})

def initss(request):
    """
    处理作业
    """
    inits()
    return render({'a': '1'})

def gethost(requset):
    """
    获取设备
    """
    datas = {
        'ip': {
            'data': ["192.168.1.24"],
            "exact": 1,
            "flag": "bk_host_innerip|bk_host_outerip"
        }
    }
    client = get_client_by_user('admin')
    business_list = client.cc.search_host(datas)
    print(business_list)

    return render({"a": "1"})

def updatahost(requset):
    """
    获取设备
    """
    datas = {
        "bk_supplier_account": 0,
        "bk_host_id": 1,
        "data": {
            "bk_host_name": "nginx2"
        }

    }
    client = get_client_by_user('admin')
    business_list = client.cc.update_host(datas)
    print(business_list)

    return render({"a": "1"})


