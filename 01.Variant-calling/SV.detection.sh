#!/bin/bash

# ----------------------- 流程开始 ---------------------------------------------
echo start at `date`
start_ts=$(date +%s)

### 首先构建一个conda的环境如SV_detection保证需要的工具都在该环境下，包括软件如下：seqkit, minimap2, samtools, sniffles2, bcftools, cuteSV, Truvari, chopper, seqkit, parallel, mingz, delly
# Version:
# sniffles 2.2
# cuteSV v2.1.2
# truvari v5.3.0
# chopper 0.10.0
# seqkit 2.10.1
# parallel 20250622
# minimap2 2.30-r1287
# bcftools 1.22
# mingz hewm2008[v1.12] [https://github.com/hewm2008/MingZ]
# samtools 1.22.1
# delly 1.5.0


### 解析 --sample 参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --sample|-s)
            SampleName="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法：$0 --sample <SampleName>"
            exit 0
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

### 验证
if [ -z "$SampleName" ]; then
    echo "错误: 必须使用 --sample 指定样本名"
    exit 1
fi


### 参考基因组 下载链接：https://ftp.ensembl.org/pub/release-110/fasta/sus_scrofa/dna/Sus_scrofa.Sscrofa11.1.dna.toplevel.fa.gz
reference="Sus_scrofa.Sscrofa11.1.dna.toplevel.fa"

if [ ! -f "${reference}" ]; then
    echo "错误: 必需文件不存在:  ${reference}"
    echo "请提供正确的绝对路径:"
    read -p "> " user_input

    # 验证输入
    if [ ! -f "$user_input" ]; then
        echo "致命错误：提供的文件仍不存在，终止流程" >&2
        exit 1
    fi

    # 转为绝对路径并赋值
    REF_FILE=$(readlpath "$user_input")
    echo "已更新路径: $REF_FILE"
fi

echo "使用文件: $REF_FILE"


### 检查 conda 是否存在
if ! command -v conda >/dev/null 2>&1; then
    echo "ERROR: conda 未找到，请安装 Miniconda/Anaconda 或加载环境" >&2
    exit 1
fi

### 获取完整路径（供后续使用）
CONDA_PATH=$(command -v conda)
echo "找到 conda: ${CONDA_PATH}"

${CONDA_PATH} init bash
source ~/.bashrc


##### 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


#### 创建样本目录SampleName，后续所有分析结果均生成到该目录下
sample=${SampleName}
mkdir -p ${SampleName}
cd ${SampleName}


# ---------------------------------- Step1 : 数据质控与比对  --------------------------------------------------------------------------

## 首先统计下机数据信息，对每一个fq文件都会进行统计；接下来，初步对fastq质控，测序质量Q值大于7，长度大于2k
TaskNum=`less Path.list | wc -l`
parallel -j ${TaskNum} sh ${SCRIPT_DIR}/scripts/clean.sh < Path.list >log.clean.sh.out

## 质控结果汇总
seq 1 | while read p;do cat *.fastq.gz.stats *.fq.gz.stats | grep -v '^file' | sed 's/,//g' | awk '{sum1 += $4; sum2 += $5; sum3 += $13; sum4 += $17; sum5 +=$18};END{print "'${SampleName}'\t"sum1"\t"sum2"\t"sum2/2500000000"\t"sum3/NR"\t"sum4/NR"\t"sum5/NR}'; cat *.clean.gz.stats | grep -v '^file' | sed 's/,//g' | awk '{sum1 += $4; sum2 += $5; sum3 += $13; sum4 += $17; sum5 +=$18};END{print sum1"\t"sum2"\t"sum2/2500000000"\t"sum3/NR"\t"sum4/NR"\t"sum5/NR}';done | xargs echo | sed '1i#Sample_Name\tRead_num\tBase_num\tCoverage\tN50\tQ_value\tGC\tClean_Read_num\tClean_Base_num\tClean_Coverage\tClean_N50\tClean_Q_value\tClean_GC' > QC_summary.txt


## minimap2 比对
ls *.fastq.clean.gz *.fq.clean.gz > Clean.Path.list
parallel -j 1 "minimap2 ${reference} {} -a -t 16 -k 16 -w 13 -A 2 -B 4 -O 4,41 -E 2,1 -s 180 -U70,1000000 | samtools view -@ 16 -Sb - | samtools sort -@ 16 -o {}.bam && samtools index -@ 16 {}.bam" < Clean.Path.list

samtools merge -@ 64 all.bam *.clean.gz.bam
samtools index -@ 64 all.bam
samtools flagstats -@ 64 all.bam > all.bam.flagstats

### 计算比对结果中的duplication rate (这一步非常慢，建议不需要执行）
#java -Xmx300G -jar picard/2.23.8/picard.jar MarkDuplicates I=all.bam O=all.marked_duplicates.bam M=all.mark_duplicates_metrics.txt
#bamtools stats -in all.marked_duplicates.bam > all.marked_duplicates.bam.bamstats



## ---------------------------------------  Step2: SV calling ------------------------------------------------------

### sniffles2 calling
if [ ! -s "sniffles2.vcf" ]; then
    sniffles -t 64 --input all.bam --vcf sniffles2.vcf --minsupport 5 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${SampleName} --snf sniffles2.snf
    echo "$?: sniffles -t 64 --input all.bam --vcf sniffles2.vcf --minsupport 5 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${SampleName} --snf sniffles2.snf"
        
    #### sniffles2 filtering
    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.filter.vcf
    bcftools query -f '%SVTYPE\n' sniffles2.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.count.txt 
    bcftools view sniffles2.vcf -O z -o sniffles2.vcf.gz
    bcftools index sniffles2.vcf.gz
    bcftools view sniffles2.filter.vcf -O z -o sniffles2.filter.vcf.gz
    bcftools index sniffles2.filter.vcf.gz
fi

### sniffles calling 第二种情况：选择auto参数call SV
if [ ! -s "sniffles2.auto.vcf" ]; then
    sniffles -t 64 --input all.bam --vcf sniffles2.auto.vcf --minsupport auto --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.auto.snf
    echo "$?: sniffles -t 64 --input all.bam --vcf sniffles2.auto.vcf --minsupport auto --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.auto.snf"

    #### sniffles auto filtering
    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.auto.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.auto.filter.vcf
    bcftools query -f '%SVTYPE\n' sniffles2.auto.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.auto.count.txt 
    bcftools view sniffles2.auto.vcf -O z -o sniffles2.auto.vcf.gz 
    bcftools index sniffles2.auto.vcf.gz
    bcftools view sniffles2.auto.filter.vcf -O z -o sniffles2.auto.filter.vcf.gz 
    bcftools index sniffles2.auto.filter.vcf.gz
fi


### sniffles calling 第三种情况：选择auto参数，minsupport-auto-mult 选择0.1, call SV
if [ ! -s "sniffles.auto0.1.vcf" ]; then
    sniffles -t 64 --input all.bam --vcf sniffles2.auto0.1.vcf --minsupport auto --minsupport-auto-mult 0.1 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.auto0.1.snf
    echo "$?: sniffles -t 64 --input all.bam --vcf sniffles2.auto0.1.vcf --minsupport auto --minsupport-auto-mult 0.1 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.auto0.1.snf"

    #### sniffles auto 0.1 filtering
    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.auto0.1.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.auto0.1.filter.vcf
    bcftools query -f '%SVTYPE\n' sniffles2.auto0.1.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.auto0.1.count.txt
    bcftools view sniffles2.auto0.1.vcf -O z -o sniffles2.auto0.1.vcf.gz
    bcftools index sniffles2.auto0.1.vcf.gz
    bcftools view sniffles2.auto0.1.filter.vcf -O z -o sniffles2.auto0.1.filter.vcf.gz 
    bcftools index sniffles2.auto0.1.filter.vcf.gz
fi


### sniffles calling 第四种情况：选择auto参数，minsupport-auto-mult 选择0.25, call SV
if [ ! -s "sniffles.auto0.25.vcf" ]; then
    sniffles -t 64 --input all.bam --vcf sniffles2.auto0.25.vcf --minsupport auto --minsupport-auto-mult 0.25 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.auto0.25.snf
    echo "$?: sniffles -t 64 --input all.bam --vcf sniffles2.auto0.25.vcf --minsupport auto --minsupport-auto-mult 0.25 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.auto0.25.snf"
    
    #### sniffles auto 0.25 filtering
    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.auto0.25.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.auto0.25.filter.vcf
    bcftools query -f '%SVTYPE\n' sniffles2.auto0.25.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.auto0.25.count.txt
    bcftools view sniffles2.auto0.25.vcf -O z -o sniffles2.auto0.25.vcf.gz
    bcftools index sniffles2.auto0.25.vcf.gz
    bcftools view sniffles2.auto0.25.filter.vcf -O z -o sniffles2.auto0.25.filter.vcf.gz 
    bcftools index sniffles2.auto0.25.filter.vcf.gz
fi


bamDepth_float=`less QC_summary.txt | grep -v '#' | awk '{print $10}'`
bamDepth=$(printf "%.0f" "${bamDepth_float}")


### sniffles calling 第五种情况：只选择5X数据 call SV
if [[ "${bamDepth}" -gt 5 && ! -s "sniffles2.5X.vcf" ]]; then
    Depth5X=$(echo "scale=5; 5 / ${bamDepth}" | bc)
    Para5X=$(echo "123 + ${Depth5X}" | bc)

    samtools view -@ 20 -b -s ${Para5X} all.bam -o all.5X.bam
    samtools index -@ 20 all.5X.bam

    sniffles -t 64 --input all.5X.bam --vcf sniffles2.5X.vcf --minsupport 2 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.5X.snf
    echo "$?: sniffles -t 64 --input all.5X.bam --vcf sniffles2.5X.vcf --minsupport 2 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.5X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.5X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.5X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.5X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.5X.count.txt 
    bcftools view sniffles2.5X.vcf -O z -o sniffles2.5X.vcf.gz 
    bcftools index sniffles2.5X.vcf.gz
    bcftools view sniffles2.5X.filter.vcf -O z -o sniffles2.5X.filter.vcf.gz 
    bcftools index sniffles2.5X.filter.vcf.gz
fi


### sniffles calling 第六种情况：只选择10X数据 call SV
if [[ "${bamDepth}" -gt 10 && ! -s "sniffles2.10X.vcf" ]]; then
    Depth10X=$(echo "scale=5; 10 / ${bamDepth}" | bc)
    Para10X=$(echo "123 + ${Depth10X}" | bc)

    samtools view -@ 20 -b -s ${Para10X} all.bam -o all.10X.bam
    samtools index -@ 20 all.10X.bam

    sniffles -t 64 --input all.10X.bam --vcf sniffles2.10X.vcf --minsupport 3 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.10X.snf
    echo "$?: sniffles -t 64 --input all.10X.bam --vcf sniffles2.10X.vcf --minsupport 3 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.10X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.10X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.10X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.10X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.10X.count.txt 
    bcftools view sniffles2.10X.vcf -O z -o sniffles2.10X.vcf.gz 
    bcftools index sniffles2.10X.vcf.gz
    bcftools view sniffles2.10X.filter.vcf -O z -o sniffles2.10X.filter.vcf.gz 
    bcftools index sniffles2.10X.filter.vcf.gz
fi


### sniffles calling 第七种情况：只选择15X数据 call SV
if [[ "${bamDepth}" -gt 15 && ! -s "sniffles2.15X.vcf" ]]; then
    Depth15X=$(echo "scale=5; 15 / ${bamDepth}" | bc)
    Para15X=$(echo "123 + ${Depth15X}" | bc)

    samtools view -@ 20 -b -s ${Para15X} all.bam -o all.15X.bam
    samtools index -@ 20 all.15X.bam

    sniffles -t 64 --input all.15X.bam --vcf sniffles2.15X.vcf --minsupport 4 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.15X.snf
    echo "$?: sniffles -t 64 --input all.15X.bam --vcf sniffles2.15X.vcf --minsupport 4 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.15X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.15X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.15X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.15X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.15X.count.txt 
    bcftools view sniffles2.15X.vcf -O z -o sniffles2.15X.vcf.gz 
    bcftools index sniffles2.15X.vcf.gz
    bcftools view sniffles2.15X.filter.vcf -O z -o sniffles2.15X.filter.vcf.gz 
    bcftools index sniffles2.15X.filter.vcf.gz
fi


### sniffles calling 第八种情况：只选择20X数据 call SV
if [[ "${bamDepth}" -gt 20 && ! -s "sniffles2.20X.vcf" ]]; then
    Depth20X=$(echo "scale=5; 20 / ${bamDepth}" | bc)
    Para20X=$(echo "123 + ${Depth20X}" | bc)

    samtools view -@ 20 -b -s ${Para20X} all.bam -o all.20X.bam
    samtools index -@ 20 all.20X.bam

    sniffles -t 64 --input all.20X.bam --vcf sniffles2.20X.vcf --minsupport 5 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.20X.snf
    echo "$?: sniffles -t 64 --input all.20X.bam --vcf sniffles2.20X.vcf --minsupport 5 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.20X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.20X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.20X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.20X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.20X.count.txt 
    bcftools view sniffles2.20X.vcf -O z -o sniffles2.20X.vcf.gz 
    bcftools index sniffles2.20X.vcf.gz
    bcftools view sniffles2.20X.filter.vcf -O z -o sniffles2.20X.filter.vcf.gz 
    bcftools index sniffles2.20X.filter.vcf.gz
fi


### sniffles calling 第九种情况：只选择25X数据 call SV
if [[ "${bamDepth}" -gt 25 && ! -s "sniffles2.25X.vcf" ]]; then
    Depth25X=$(echo "scale=5; 25 / ${bamDepth}" | bc)
    Para25X=$(echo "123 + ${Depth25X}" | bc)

    samtools view -@ 20 -b -s ${Para25X} all.bam -o all.25X.bam
    samtools index -@ 20 all.25X.bam

    sniffles -t 64 --input all.25X.bam --vcf sniffles2.25X.vcf --minsupport 7 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.25X.snf
    echo "$?: sniffles -t 64 --input all.25X.bam --vcf sniffles2.25X.vcf --minsupport 7 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.25X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.25X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.25X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.25X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.25X.count.txt 
    bcftools view sniffles2.25X.vcf -O z -o sniffles2.25X.vcf.gz 
    bcftools index sniffles2.25X.vcf.gz
    bcftools view sniffles2.25X.filter.vcf -O z -o sniffles2.25X.filter.vcf.gz 
    bcftools index sniffles2.25X.filter.vcf.gz
fi


### sniffles calling 第十种情况：只选择30X数据 call SV
if [[ "${bamDepth}" -gt 30 && ! -s "sniffles2.30X.vcf" ]]; then
    Depth30X=$(echo "scale=5; 30 / ${bamDepth}" | bc)
    Para30X=$(echo "123 + ${Depth30X}" | bc)

    samtools view -@ 20 -b -s ${Para30X} all.bam -o all.30X.bam
    samtools index -@ 20 all.30X.bam

    sniffles -t 64 --input all.30X.bam --vcf sniffles2.30X.vcf --minsupport 8 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.30X.snf
    echo "$?: sniffles -t 64 --input all.30X.bam --vcf sniffles2.30X.vcf --minsupport 8 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.30X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.30X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.30X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.30X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.30X.count.txt 
    bcftools view sniffles2.30X.vcf -O z -o sniffles2.30X.vcf.gz 
    bcftools index sniffles2.30X.vcf.gz
    bcftools view sniffles2.30X.filter.vcf -O z -o sniffles2.30X.filter.vcf.gz 
    bcftools index sniffles2.30X.filter.vcf.gz
fi


### sniffles calling 第十一种情况：只选择35X数据 call SV
if [[ "${bamDepth}" -gt 35 && ! -s "sniffles2.35X.vcf" ]]; then
    Depth35X=$(echo "scale=5; 35 / ${bamDepth}" | bc)
    Para35X=$(echo "123 + ${Depth35X}" | bc)

    samtools view -@ 20 -b -s ${Para35X} all.bam -o all.35X.bam
    samtools index -@ 20 all.35X.bam

    sniffles -t 64 --input all.35X.bam --vcf sniffles2.35X.vcf --minsupport 9 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.35X.snf
    echo "$?: sniffles -t 64 --input all.35X.bam --vcf sniffles2.35X.vcf --minsupport 9 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.35X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.35X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.35X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.35X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.35X.count.txt 
    bcftools view sniffles2.35X.vcf -O z -o sniffles2.35X.vcf.gz 
    bcftools index sniffles2.35X.vcf.gz
    bcftools view sniffles2.35X.filter.vcf -O z -o sniffles2.35X.filter.vcf.gz 
    bcftools index sniffles2.35X.filter.vcf.gz
fi


### sniffles calling 第十二种情况：只选择40X数据 call SV
if [[ "${bamDepth}" -gt 40 && ! -s "sniffles2.40X.vcf" ]]; then
    Depth40X=$(echo "scale=5; 40 / ${bamDepth}" | bc)
    Para40X=$(echo "123 + ${Depth40X}" | bc)

    samtools view -@ 20 -b -s ${Para40X} all.bam -o all.40X.bam
    samtools index -@ 20 all.40X.bam

    sniffles -t 64 --input all.40X.bam --vcf sniffles2.40X.vcf --minsupport 10 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.40X.snf
    echo "$?: sniffles -t 64 --input all.40X.bam --vcf sniffles2.40X.vcf --minsupport 10 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.40X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.40X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.40X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.40X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.40X.count.txt 
    bcftools view sniffles2.40X.vcf -O z -o sniffles2.40X.vcf.gz 
    bcftools index sniffles2.40X.vcf.gz
    bcftools view sniffles2.40X.filter.vcf -O z -o sniffles2.40X.filter.vcf.gz 
    bcftools index sniffles2.40X.filter.vcf.gz
fi


### sniffles calling 第十三种情况：只选择45X数据 call SV
if [[ "${bamDepth}" -gt 45 && ! -s "sniffles2.45X.vcf" ]]; then
    Depth45X=$(echo "scale=5; 45 / ${bamDepth}" | bc)
    Para45X=$(echo "123 + ${Depth45X}" | bc)

    samtools view -@ 20 -b -s ${Para45X} all.bam -o all.45X.bam
    samtools index -@ 20 all.45X.bam

    sniffles -t 64 --input all.45X.bam --vcf sniffles2.45X.vcf --minsupport 11 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.45X.snf
    echo "$?: sniffles -t 64 --input all.45X.bam --vcf sniffles2.45X.vcf --minsupport 11 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.45X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.45X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.45X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.45X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.45X.count.txt 
    bcftools view sniffles2.45X.vcf -O z -o sniffles2.45X.vcf.gz 
    bcftools index sniffles2.45X.vcf.gz
    bcftools view sniffles2.45X.filter.vcf -O z -o sniffles2.45X.filter.vcf.gz 
    bcftools index sniffles2.45X.filter.vcf.gz
fi


### sniffles calling 第十四种情况：只选择50X数据 call SV
if [[ "${bamDepth}" -gt 50 && ! -s "sniffles2.50X.vcf" ]]; then
    Depth50X=$(echo "scale=5; 50 / ${bamDepth}" | bc)
    Para50X=$(echo "123 + ${Depth50X}" | bc)

    samtools view -@ 20 -b -s ${Para50X} all.bam -o all.50X.bam
    samtools index -@ 20 all.50X.bam

    sniffles -t 64 --input all.50X.bam --vcf sniffles2.50X.vcf --minsupport 12 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.50X.snf
    echo "$?: sniffles -t 64 --input all.50X.bam --vcf sniffles2.50X.vcf --minsupport 12 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.50X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.50X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.50X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.50X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.50X.count.txt 
    bcftools view sniffles2.50X.vcf -O z -o sniffles2.50X.vcf.gz 
    bcftools index sniffles2.50X.vcf.gz
    bcftools view sniffles2.50X.filter.vcf -O z -o sniffles2.50X.filter.vcf.gz 
    bcftools index sniffles2.50X.filter.vcf.gz
fi


### sniffles calling 第十五种情况：只选择55X数据 call SV
if [[ "${bamDepth}" -gt 55 && ! -s "sniffles2.55X.vcf" ]]; then
    Depth55X=$(echo "scale=5; 55 / ${bamDepth}" | bc)
    Para55X=$(echo "123 + ${Depth55X}" | bc)

    samtools view -@ 20 -b -s ${Para55X} all.bam -o all.55X.bam
    samtools index -@ 20 all.55X.bam

    sniffles -t 64 --input all.55X.bam --vcf sniffles2.55X.vcf --minsupport 13 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.55X.snf
    echo "$?: sniffles -t 64 --input all.55X.bam --vcf sniffles2.55X.vcf --minsupport 13 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.55X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.55X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.55X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.55X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.55X.count.txt 
    bcftools view sniffles2.55X.vcf -O z -o sniffles2.55X.vcf.gz 
    bcftools index sniffles2.55X.vcf.gz
    bcftools view sniffles2.55X.filter.vcf -O z -o sniffles2.55X.filter.vcf.gz 
    bcftools index sniffles2.55X.filter.vcf.gz
fi


### sniffles calling 第十六种情况：只选择60X数据 call SV
if [[ "${bamDepth}" -gt 60 && ! -s "sniffles2.60X.vcf" ]]; then
    Depth60X=$(echo "scale=5; 60 / ${bamDepth}" | bc)
    Para60X=$(echo "123 + ${Depth60X}" | bc)

    samtools view -@ 20 -b -s ${Para60X} all.bam -o all.60X.bam
    samtools index -@ 20 all.60X.bam

    sniffles -t 64 --input all.60X.bam --vcf sniffles2.60X.vcf --minsupport 14 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.60X.snf
    echo "$?: sniffles -t 64 --input all.60X.bam --vcf sniffles2.60X.vcf --minsupport 14 --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.60X.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.60X.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.60X.filter.vcf 
    bcftools query -f '%SVTYPE\n' sniffles2.60X.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.60X.count.txt 
    bcftools view sniffles2.60X.vcf -O z -o sniffles2.60X.vcf.gz 
    bcftools index sniffles2.60X.vcf.gz
    bcftools view sniffles2.60X.filter.vcf -O z -o sniffles2.60X.filter.vcf.gz 
    bcftools index sniffles2.60X.filter.vcf.gz
fi


### sniffles calling 第十七种情况：不同深度人工选择合适的深度
if [ "${bamDepth}" -lt 10 ]; then
    minsupportNum=2
elif [ "${bamDepth}" -lt 15 ]; then
    minsupportNum=3
elif [ "${bamDepth}" -lt 20 ]; then
    minsupportNum=4
elif [ "${bamDepth}" -lt 25 ]; then
    minsupportNum=5
elif [ "${bamDepth}" -lt 30 ]; then
    minsupportNum=7
elif [ "${bamDepth}" -lt 35 ]; then
    minsupportNum=8
elif [ "${bamDepth}" -lt 40 ]; then
    minsupportNum=9
elif [ "${bamDepth}" -lt 45 ]; then
    minsupportNum=10
elif [ "${bamDepth}" -lt 50 ]; then
    minsupportNum=11
elif [ "${bamDepth}" -lt 55 ]; then
    minsupportNum=12
elif [ "${bamDepth}" -lt 60 ]; then
    minsupportNum=13
elif [ "${bamDepth}" -lt 65 ]; then
    minsupportNum=14
elif [ "${bamDepth}" -lt 70 ]; then
    minsupportNum=15
elif [ "${bamDepth}" -lt 75 ]; then
    minsupportNum=16
elif [ "${bamDepth}" -lt 80 ]; then
    minsupportNum=17
elif [ "${bamDepth}" -lt 85 ]; then
    minsupportNum=18
elif [ "${bamDepth}" -lt 90 ]; then
    minsupportNum=19
elif [ "${bamDepth}" -lt 95 ]; then
    minsupportNum=20
elif [ "${bamDepth}" -lt 100 ]; then
    minsupportNum=21
elif [ "${bamDepth}" -lt 105 ]; then
    minsupportNum=22
elif [ "${bamDepth}" -lt 110 ]; then
    minsupportNum=23
elif [ "${bamDepth}" -lt 115 ]; then
    minsupportNum=24
elif [ "${bamDepth}" -lt 120 ]; then
    minsupportNum=25
elif [ "${bamDepth}" -lt 125 ]; then
    minsupportNum=26
elif [ "${bamDepth}" -lt 130 ]; then
    minsupportNum=27
elif [ "${bamDepth}" -lt 135 ]; then
    minsupportNum=28
elif [ "${bamDepth}" -lt 140 ]; then
    minsupportNum=29
else
    minsupportNum=30
fi

if [ ! -s "sniffles2.selected.vcf" ]; then
    sniffles -t 64 --input all.bam --vcf sniffles2.selected.vcf --minsupport ${minsupportNum} --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.selected.snf
    echo "$?: sniffles -t 64 --input all.bam --vcf sniffles2.selected.vcf --minsupport ${minsupportNum} --minsvlen 50 --allow-overwrite --reference ${reference} --sample-id ${sample} --snf sniffles2.selected.snf"

    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' sniffles2.selected.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > sniffles2.selected.filter.vcf
    bcftools query -f '%SVTYPE\n' sniffles2.selected.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > sniffles2.selected.count.txt
    bcftools view sniffles2.selected.vcf -O z -o sniffles2.selected.vcf.gz 
    bcftools index sniffles2.selected.vcf.gz
    bcftools view sniffles2.selected.filter.vcf -O z -o sniffles2.selected.filter.vcf.gz
    bcftools index sniffles2.selected.filter.vcf.gz
fi


### cuteSV calling
if [ ! -s "cuteSV.vcf" ]; then
    cuteSV -t 64 --max_cluster_bias_INS 100 --diff_ratio_merging_INS 0.3 --max_cluster_bias_DEL 100 --diff_ratio_merging_DEL 0.3 --min_size 50 --min_support 5 --max_size -1 --genotype -S ${SampleName} all.bam ${reference} cuteSV.vcf ./
    echo "$?: cuteSV -t 64 --max_cluster_bias_INS 100 --diff_ratio_merging_INS 0.3 --max_cluster_bias_DEL 100 --diff_ratio_merging_DEL 0.3 --min_size 50 --min_support 5 --max_size -1 --genotype -S ${SampleName} all.bam ${reference} cuteSV.vcf ./"

    #### cuteSV filtering
    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' cuteSV.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > cuteSV.filter.vcf
    bcftools query -f '%SVTYPE\n' cuteSV.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > cuteSV.count.txt 
    bcftools view cuteSV.vcf -O z -o cuteSV.vcf.gz
    bcftools index cuteSV.vcf.gz
    bcftools view cuteSV.filter.vcf -O z -o cuteSV.filter.vcf.gz
    bcftools index cuteSV.filter.vcf.gz
fi


### delly calling
if [ ! -s "delly.vcf" ]; then
    
    ${CONDA_PATH} activate delly

    delly lr -y ont -q 20 -s 15 -z 5 -o delly.bcf -g ${reference} all.bam
    echo "$?: delly lr -y ont -q 20 -s 15 -z 5 -o delly.bcf -g ${reference} all.bam"

    ${CONDA_PATH} deactivate

    bcftools view delly.bcf > delly.vcf
    bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' delly.vcf | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y > delly.filter.vcf
    bcftools query -f '%SVTYPE\n' delly.filter.vcf | sort | uniq -c | xargs echo | awk '{print $1"\t"$3"\t"$5"\t"$7"\t"$1+$3+$5+$7}' | sed '1i#DEL\tDUP\tINS\tINV\tTotal' > delly.count.txt 
    bcftools view delly.vcf -O z -o delly.vcf.gz
    bcftools index delly.vcf.gz
    bcftools view delly.filter.vcf -O z -o delly.filter.vcf.gz
    bcftools index delly.filter.vcf.gz
fi

rm -f all.5X.bam all.10X.bam all.15X.bam all.20X.bam all.25X.bam all.30X.bam all.35X.bam all.40X.bam all.45X.bam all.50X.bam all.55X.bam all.60X.bam all.80X.bam *.fq.clean.gz *.fastq.clean.gz *.clean.gz.bam


# 创建一个done文件标志整个流程是没有任何问题正常跑完
touch SV_calling.finished.done

end_ts=$(date +%s)
duration=$(( end_ts - start_ts ))
printf '\n[Done] Total elapsed time: %02d:%02d:%02d\n' $(( duration / 3600 )) $(( (duration % 3600) / 60 )) $(( duration % 60 )) > Finished.time


cd ..


echo end at `date`
