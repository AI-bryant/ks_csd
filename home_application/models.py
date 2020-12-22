# -*- coding: utf-8 -*-
from django.db import models

# Create your models here.
class JobWork(models.Model):
    # id
    id = models.AutoField(primary_key=True)
    # 作业id
    job_instance_id =  models.CharField(max_length=100)
    # bk_biz_id
    bk_biz_id = models.CharField(max_length=100)
    # 作业名称
    job_instance_name = models.CharField(max_length=500)
    # 作业状态 作业状态码: 1.未执行; 2.正在执行; 3.执行成功; 4.执行失败; 5.跳过; 6.忽略错误; 7.等待用户; 8.手动结束; 9.状态异常; 10.步骤强制终止中; 11.步骤强制终止成功; 12.步骤强制终止失败
    jobStatus = models.CharField(max_length=50)
    # 是否有处理 0未处理 1处理成功 2处理失败
    isDispose = models.CharField(max_length=50)
    # 创建日期
    createdDate = models.CharField(max_length=200)
    # 修改日期
    updatedDate = models.CharField(max_length=200, null=True)

    # 表名
    class Meta:
        db_table = 'JobWork'