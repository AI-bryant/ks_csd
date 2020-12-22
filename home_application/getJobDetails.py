#!coding=utf-8
import json
import re
from datetime import timedelta

from celery.task import periodic_task

from blueking.component.shortcuts import get_client_by_request, get_client_by_user


import time

# 获取数据库中未处理的作业
from home_application.models import JobWork
import sys
if sys.getdefaultencoding() != 'utf-8':
    reload(sys)
    sys.setdefaultencoding('utf-8')


@periodic_task(run_every=timedelta(seconds=60*60*24*1))
def initDev():
    time.sleep(3600)
    inits()

def inits():
    job = JobWork.objects.all()
    for item in job:
        if item.isDispose == '0':
            get_job_instance_status(item.job_instance_id, item.bk_biz_id, item.id)

    # return HttpResponse('ok')
# 查询作业状态
def get_job_instance_status(id, bk_biz_id, dbid):

    client = get_client_by_user('admin')
    business_list = client.job.get_job_instance_status({'job_instance_id':id, 'bk_biz_id': bk_biz_id})
    data = business_list['data']

    if data['is_finished']:
        get_job_log(id, bk_biz_id, dbid)

# 查询做业日志详情
def get_job_log(id,bk_biz_id, dbid):
    datas = {
        'bk_biz_id': bk_biz_id,
        'job_instance_id': id
    }
    client = get_client_by_user('admin')
    business_list = client.job.get_job_instance_log(datas)
    if business_list['result']:
        data = business_list['data']
        items = data[0]
        if items['status'] == 3 or items['status'] == 4:
            #拿到作业执行状态3
            for i in items['step_results']:
                for j in i['ip_logs']:
                    parsing_log(j['log_content'],bk_biz_id,j['ip'])
            times = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            JobWork.objects.filter(id=dbid).update(jobStatus=str(items['status']), isDispose=str(1), updatedDate=times)

        else:
            times = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            JobWork.objects.filter(id=dbid).update(jobStatus=str(items['status']), updatedDate=times)


# 解析日志
def parsing_log(log, bk_biz_id, ip):
    try:
        parsing_host = {}
        log = log.encode('gbk')
        new_log = log[log.index('{'):]
        parsing_host['bk_apache'] = json.loads(new_log, strict=False)['apache']
        parsing_host['nginx'] = json.loads(new_log, strict=False)['nginx']
        parsing_host['weblogic'] = json.loads(new_log, strict=False)['weblogic']
        parsing_host['bk_tomcat'] = json.loads(new_log, strict=False)['tomcat']
    except:
       print ''
    # bk_obj_id = get_host(ip, bk_biz_id)
    for (k, v) in parsing_host.items():

        if any(v):
            if k == 'bk_apache':
                if v.get('version'):

                    try:
                        instObj = {
                          'ip': ip,
                          'version': v.get('version'),
                          'inst_name': k,
                          'v': v,
                          'data':{
                              'bk_inst_key': str(ip) + '_' + v.get('version'),
                              'bk_inst_name': str(ip) + '_' + v.get('version'),
                              'bk_ip': ip,
                              'bk_version': v.get('version'),
                              'bk_main_path': v.get('home'),
                              'bk_build_param': '' if len(v.get('compile_args')) > 4000 else v.get('compile_args'),
                              'bk_port': ','.join(list(set(v.get('ports'))) ),
                              'bk_max_keepalive': v.get('maxkeepaliverequests'),
                              'bk_max_connect': v.get('maxclients'),
                              'bk_log_path': v.get('customlog')
                          }
                        }
                        if not '2.2.15' in v.get('version'):
                            get_inst(instObj,bk_biz_id)
                    except:
                        pass
            elif k == 'bk_tomcat':
                try:
                    instObj = {
                        'ip': ip,
                        'version': v.get('version'),
                        'inst_name': k,
                        'v': v,
                        'data': {
                            'bk_inst_key': str(ip) + '_' + v.get('version'),
                            'bk_inst_name': str(ip) + '_' + v.get('version'),
                            'bk_ip': ip,
                            'bk_version': v.get('version'),
                            'bk_main_path': v.get('home'),
                            'bk_jdk_version': v.get('jdk_version'),
                            'bk_mem': 'Permsize:' + str(v.get('Permsize')) + ',Xmx:' + str(v.get('Xmx') )+ ',Xms:' + str(v.get('Xms'))
                        }
                    }

                    get_inst(instObj, bk_biz_id)
                except:
                    print ''
            elif k == 'weblogic':
                # 唯一键 ip_domain_servicename
                taget = {}
                tagets = ''
                jdbc_key = []
                app_server = []

                if isinstance(v.get('domains'), list):
                    for z in v.get('domains'):


                        # z 是domains 下的每条数据
                        try:

                            app_server = v.get('isAdmin').split('\n')

                            db_str = ''
                            urls = ''
                            jdbc_name = ''
                            jdbc_jndi_name = ''
                            jdbc_max_capacity = ''
                            jdbc_min_capacity = ''
                            initial_capacity = ''
                            jdbc_user = ''
                            if isinstance(z.get('jdbc'), list) and len(z.get('jdbc')) > 0:
                                for a in z.get('jdbc'):
                                  url = re.findall(r'@(.+?)\:', a.get('url'), re.I)
                                  if len(url) > 0:
                                      url = url[0]
                                  jdbc_name = a.get('name')
                                  jdbc_jndi_name    = a.get('jndi-name')
                                  jdbc_max_capacity = a.get('max-capacity')
                                  jdbc_min_capacity = a.get('min-capacity')
                                  initial_capacity  = a.get('initial-capacity')
                                  jdbc_user         = a.get('user')
                                  if a.get('target'):
                                      jdbc_key = a.get('target').split(',')
                                      for item in jdbc_key:
                                          taget[item] = {
                                              'domain': url,
                                              'jdbc_name':jdbc_name,
                                              'jdbc_jndi_name':jdbc_jndi_name,
                                              'jdbc_max_capacity':jdbc_max_capacity,
                                              'jdbc_min_capacity':jdbc_min_capacity,
                                              'initial_capacity':initial_capacity,
                                              'jdbc_user':jdbc_user,
                                          }
                                  db_str = 'name:' + str(a.get('name')) + str(',url:') + str(a.get('url')) + ',target:' + str(a.get('target') )+ '\n'
                            for s in z.get('servers'):
                                # s 是jdbc 下的servers 每条数据
                                web_version = ''
                                web_version = "-".join(v.get('versions'))
                                if (s.get('name') == 'AdminServer' and s.get('name') in app_server) and not s.get('name') in taget:
                                    instObj = {
                                        'ip': ip,
                                        'version': z.get('version'),
                                        'inst_name': k,
                                        'v': v,
                                        'data': {
                                            # 内存参数
                                            'mem_config': 'MaxPermSize：' + str(
                                                s.get('MaxPermSize')) + ',\nPermSize:' + str(
                                                s.get('PermSize')) + ',\nXmx:' + str(s.get('Xmx')) + ',\nXms' + str(
                                                s.get(',Xms')),
                                            # 节点名
                                            'node_name': str(s.get('name')),
                                            # 数据库信息
                                            'db_info': db_str,
                                            # 唯一键
                                            'bk_inst_name': str(ip) + '_' + str(s.get('name')) + '_' + s.get('nossl').get('listen_port'),
                                            'ip': ip,
                                            'version': web_version,
                                            # 主路径
                                            'home_path': z.get('home'),
                                            # jdk版本
                                            'jdk_version': s.get('jdk_version'),
                                            # 节点端口
                                            'node_port': s.get('nossl').get('listen_port'),
                                            # 监听地址
                                            'listen_address': s.get('nossl').get('listen_address'),
                                        }
                                    }
                                    get_inst(instObj, bk_biz_id)

                                for items in taget:

                                    instObj = {
                                        'ip': ip,
                                        'version': z.get('version'),
                                        'inst_name': k,
                                        'v': v,
                                        'data': {
                                            # 内存参数
                                            'mem_config': 'MaxPermSize：'+ str(s.get('MaxPermSize')) + ',\nPermSize:' + str(s.get('PermSize')) + ',\nXmx:' + str(s.get('Xmx')) + ',\nXms' + str(s.get(',Xms')),
                                            # 节点名
                                            'node_name': str(s.get('name')),
                                            # 数据库信息
                                            'db_info': db_str,
                                            # 域名
                                            'domain': taget[item]['domain'],
                                            # 唯一键
                                            'bk_inst_name': str(ip) + '_' +str(s.get('name')),
                                            'ip': ip,
                                            'version': web_version,
                                            # 主路径
                                            'home_path': z.get('home'),
                                            # jdk版本
                                            'jdk_version': s.get('jdk_version'),
                                            # 节点端口
                                            'node_port': s.get('nossl').get('listen_port'),
                                            # 监听地址
                                            'listen_address': s.get('nossl').get('listen_address'),
                                        }
                                    }
                                    if items == s.get('name'):
                                        instObj['data']['jdbc_name'] = taget[item]['jdbc_name']
                                        instObj['data']['jdbc_jndi_name'] = taget[item]['jdbc_jndi_name']
                                        instObj['data']['jdbc_max_capacity'] = taget[item]['jdbc_max_capacity']
                                        instObj['data']['jdbc_min_capacity'] = taget[item]['jdbc_min_capacity']
                                        instObj['data']['initial_capacity'] = taget[item]['initial_capacity']
                                        instObj['data']['jdbc_user'] = taget[item]['jdbc_user']

                                        if items in app_server:
                                            get_inst(instObj, bk_biz_id)
                                    # elif items == 'AdminServer':
                                    #     instObj['bk_inst_name'] = str(ip) + '_' +str(s.get('name')) + '_' + s.get('nossl').get('listen_port')
                                    #     print '--------------------------------------'
                                    #     # if items == 'AdminServer':
                                    #     #     if v.get('isAdmin'):
                                    #     #         get_inst(instObj, bk_biz_id)
                                    #     # else:
                                    #     #     if s.get('nossl').get('listen_address') == ip or v.get('isAdmin'):
                                        #         get_inst(instObj, bk_biz_id)
                                    # else:
                                    #     get_inst(instObj, bk_biz_id)
                        except Exception as e:
                            print (e)

            elif k == 'nginx':
                try:

                    instObj = {
                        'ip': ip,
                        'version': v.get('version'),
                        'inst_name': k,
                        'v': v,
                        'data': {
                            'bk_inst_name': str(ip) + '_' + v.get('version'),
                            'bk_version': v.get('version'),
                            'bk_main_path': v.get('home'),
                            'bk_build_param':  '' if len(v.get('compile_args')) > 4000 else v.get('compile_args'),
                            'bk_port': ','.join(list(set(v.get('ports')))),
                            'bk_ip': str(ip)
                        }

                    }
                    get_inst(instObj,bk_biz_id)
                except:
                    print
        else:
            #  删除
            # 删除实例
            # de_obj = {
            #     "bk_supplier_account": "0",
            #     "bk_obj_id": obj['inst_name'],
            #
            #     "bk_inst_id": data[0]['bk_inst_id']
            #
            # }
            # client = get_client_by_user('admin')
            # business_list = client.cc.delete_inst(de_obj)
            # print '='*100
            # print business_list
            # print '='*100
            pass
            # data = {
            #     'bk_obj_id': k,
            # }
            # client = get_client_by_user('admin')
            # business_list = client.cc.search_inst(data)

#     查询实例
def get_inst(obj,bk_biz_id):
    datas ={
        'bk_obj_id': obj.get('inst_name'),
        'bk_supplier_account': 0
    }
    condition = {}
    condition[obj.get('inst_name')] = list()
    # 按条件查询  没有新增  有 更新
    # if obj['inst_name'] == 'weblogic':
    ip_obj = {
        "field": "bk_inst_name",
        "operator": "$eq",
        "value": obj['data'].get('bk_inst_name')
    }
        # ver_obj = {
        #     "field": "version",
        #     "operator": "$eq",
        #     "value": obj.get('version')
        # }
    #     node_port = {
    #         "field": "node_port",
    #         "operator": "$eq",
    #         "value": obj['data'].get('node_port')
    #     }
    #     condition[obj.get('.')].append(node_port)
    # else:
    #     ip_obj = {
    #         "field": "bk_ip",
    #         "operator": "$eq",
    #         "value": obj['ip']
    #     }
    #     ver_obj = {
    #         "field": "bk_version",
    #         "operator": "$eq",
    #         "value": obj['version']
    #     }
    condition[obj['inst_name']].append(ip_obj)
    # condition[obj['inst_name']].append(ver_obj)
    datas['condition'] = condition
    # 根据条件查询 实例 没有查到数据进行新增数据
    client = get_client_by_user('admin')
    business_list = client.cc.search_inst(datas)
    if business_list['result']:
        data = business_list['data']['info']
        if len(data) == 0:
            obj['data']['bk_supplier_account'] = 0
            obj['data']['bk_obj_id'] = obj['inst_name']
            # 新增实例
            client = get_client_by_user('admin')
            business_list = client.cc.create_inst(obj['data'])
            if business_list['result']:
                dataObj = {
                    # 源模型实例id 创建成功中 data中会返回
                    'bk_inst_id': get_host(obj['ip']),
                    # 目标模型实例id data中会返回
                    'bk_asst_inst_id': business_list['data']['bk_inst_id'],
                    'metadata': {
                        'label':{
                            'bk_biz_id': bk_biz_id
                        }
                    }
                }
                dataObj['bk_obj_asst_id'] = 'host_run_' + obj['inst_name']
                # 新增模型实例之间的关联关系.
                client = get_client_by_user('admin')
                business_list = client.cc.add_instance_association(dataObj)
                # if not business_list['result']:
                #
                #     print '='*100
                #     print obj['ip'], '新增失败',obj['inst_name'],business_list
                #     print '='*100
                # else:
                #     print '=' * 100
                #     print obj['ip'], '新增成功',obj['inst_name'], business_list
                #     print '=' * 100

                # host_data = business_list['data']
        else:
            # 更新实例字段
            ids = data[0]['bk_inst_id']
            obj['data'].pop('bk_inst_name', 404)
            obj['data'].pop('bk_inst_key', 404)
            obj['data']['bk_supplier_account'] = 0
            obj['data']['bk_obj_id'] = obj['inst_name']
            obj['data']['bk_inst_id'] = ids
            client = get_client_by_user('admin')
            business_list = client.cc.update_inst(obj['data'])
            if business_list['result']:
                dataObj = {
                    # 源模型实例id 创建成功中 data中会返回
                    'bk_inst_id': get_host(obj['ip']),
                    # 目标模型实例id data中会返回
                    'bk_asst_inst_id': ids,
                    'metadata': {
                        'label': {
                            'bk_biz_id': bk_biz_id
                        }
                    }
                }
                # if obj['inst_name'] == 'nginx':
                #     dataObj['bk_obj_asst_id'] = obj['inst_name'] + '_run_host'
                # elif obj['inst_name'] == 'weblogc':
                #     dataObj['bk_obj_asst_id'] = 'host_run_bk_' + obj['inst_name']
                # else:
                dataObj['bk_obj_asst_id'] = 'host_run_' + obj['inst_name']
                # 新增模型实例之间的关联关系.
                # client = get_client_by_user('admin')
                # business_list = client.cc.add_instance_association(dataObj)
                # if not business_list['result']:
                #     print '=' * 100
                #     print obj['ip'], '更新失败',obj['inst_name'],business_list
                #     print '=' * 100
                # else:
                #     print '=' * 100
                #     print obj['ip'],'更新成功', business_list
                #     print '=' * 100



# 查询主机详情
def get_host(ip):
    datas = {
        'ip': {
            'data': [ip],
            "exact": 1,
            "flag": "bk_host_innerip|bk_host_outerip"
        }
    }
    client = get_client_by_user('admin')
    business_list = client.cc.search_host(datas)

    if business_list["result"]:
        data = business_list['data']['info'][0]
        # print data
        return data['host']['bk_host_id']

# 查询模型实例的关联关系
def find_instance(obj, parsing_host):

    for (k, v) in parsing_host.items():
        # print k, v
        if not v == {} and not v['compile_args'] == '':
            datas = {
                "condition": {
                    "bk_obj_id": k,
                    "bk_object_id": obj['bk_object_id'],
                },
                "metadata": {
                    "label": {
                        "bk_biz_id": obj['bk_biz_id']
                    }
                }
            }
            client = get_client_by_user('admin')
            business_list = client.cc.find_instance_association(datas)
            data = business_list['data']
            # print '='*100
            # print business_list
            # print '=' * 100

