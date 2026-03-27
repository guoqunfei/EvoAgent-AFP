#!/bin/bash

SEQKIT_THREADS=8

##### 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


CfqPath=$1
Cfq=`echo "${CfqPath}" | awk -F '/' '{print $NF}'`
CCfq=`echo "${Cfq}" | sed 's/gz/clean.gz/g'`

# 第一步：统计原始文件数据量信息
seqkit stats -a ${CfqPath} > ${Cfq}.stats

# 第二步：卡长度大于 2kb 和 测序质量大于 7 进行过滤
python ${SCRIPT_DIR}/filter.py ${CfqPath} | mingz -c > ${CCfq}

# 第三步：统计过滤之后的文件数据量信息
seqkit stats -a ${CCfq} > ${CCfq}.stats

