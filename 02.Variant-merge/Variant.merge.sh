#!/bin/sh

echo start at `date`

${CONDA_PATH} init bash

source ~/.bashrc

conda activate SV_detection


### 首先需要生成 snf_files_list.tsv 文件和 Chr.list 文件
parallel -j 1 "mkdir -p tmp{} && sniffles -t 16 --input snf_files_list.tsv --vcf multisample.Chr{}.vcf --allow-overwrite --no-sort --contig {} --tmp-dir tmp{}" < Chr.list

ls multisample.Chr*.vcf | while read p;do bgzip -c ${p} > ${p}.gz; tabix -p vcf ${p}.gz; done

bcftools concat --output Step1.vcf.gz --output-type z multisample.Chr*.vcf.gz

/share/app/vcftools/0.1.16/bin/vcftools --gzvcf Step1.vcf.gz --missing-indv --out missing_stats

less missing_stats.imiss | awk '$5 < 0.2 {print $1}' > keep_samples.txt

bcftools view -S keep_samples.txt Step1.vcf.gz -o Step2.vcf.gz

bcftools view -i 'SVTYPE="DEL" || SVTYPE="DUP" || SVTYPE="INS" || SVTYPE="INV"' Step2.vcf.gz | bcftools view -i 'FILTER="PASS"' -t 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,X,Y -Oz -o Step3.vcf.gz

bcftools sort Step3.vcf.gz -Oz -o Step3.sorted.vcf.gz

bcftools index Step3.sorted.vcf.gz --tbi

bcftools filter -e 'abs(SVLEN)<50 || abs(SVLEN)>30000000' Step3.sorted.vcf.gz -o Step4.vcf.gz

bcftools filter -i 'F_MISSING <= 0.1' Step4.vcf.gz -Oz -o Step5.vcf.gz

bcftools index Step5.vcf.gz --tbi

truvari collapse -f Sus_scrofa.Sscrofa11.1.dna.toplevel.fa -i Step5.vcf.gz -k common -o Step6.vcf.gz -c Step6.truvari_collapsed.vcf.gz

bcftools bcftools/1.11/libexec/bcftools/fill-tags.so Step6.truvari_collapsed.vcf.gz -Oz -o Step6.fill_tags.vcf.gz -- -t all

bcftools view -i 'INFO/AC>=1' Step6.fill_tags.vcf.gz -o Step6.fill_tags.AC.vcf.gz

bcftools view -h Step6.fill_tags.AC.vcf.gz > Step6.fill_tags.AC.SortedChr.vcf

less Chr.sorted.list | while read p;do bcftools view -H Step6.fill_tags.AC.vcf.gz | awk '$1 == "'${p}'"' | sort -k1,1V -k2,2n  >> Step6.fill_tags.AC.SortedChr.vcf;done

bcftools view Step6.fill_tags.AC.SortedChr.vcf -Oz -o Step6.fill_tags.AC.SortedChr.vcf.gz

bcftools view -h Step6.fill_tags.AC.SortedChr.vcf.gz | tail -n1 | sed 's/\t/\n/g' | awk 'NR >= 10' | awk '{print $1"Cyclone"}' > FinalHead.list

bcftools reheader -s FinalHead.list Step6.fill_tags.AC.SortedChr.vcf.gz -o Final.vcf.gz

echo end at `date`
