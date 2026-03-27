## 需要先将snpeff工具安装好
java -jar /opt/software/miniconda/envs/SV_annotation/share/snpeff-5.4.0a-0/snpEff.jar build -c snpEff.config -gtf22 -v my_genome

## -ud 可以调整 500、1000、5000，这里使用5000来分析
java -Xmx32G -jar /opt/software/miniconda/envs/SV_annotation/share/snpeff-5.4.0a-0/snpEff.jar eff -csvStats variants.SnpEff.csv -s variants.SnpEff.html -c snpEff.config -v -ud 5000 -nodownload my_genome All.SV_SNP_Indel.ac1.rmdupPosTheSame_SNPIndelID.fill_tags.rmGT.vcf.gz > my.SnpEff.5000bp.vcf

bcftools view -H All.SV_SNP_Indel.ac1.rmdupPosTheSame_SNPIndelID.fill_tags.rmGT.vcf.gz | awk '{split($8,a,"MAF=");split(a[2],b,";");print $3"\t"b[1]}' > MAF.out

## 执行自定义脚本 adjust_format.py，可以生成三个文件：SnpEff.5000bp.INDEL_GenomeFeature.classify.out、SnpEff.5000bp.SNP_GenomeFeature.classify.out、SnpEff.5000bp.SV_GenomeFeature.classify.out
python adjust_format.py

less SnpEff.5000bp.SV_GenomeFeature.classify.out | awk '{print $1"\t"$3"\t"$4}' | sort | uniq > SnpEff.5000bp.SV_GenomeFeature.classify.uniq.out
less SnpEff.5000bp.SV_GenomeFeature.classify.uniq.out | awk '{print $2}' | sort | uniq | while read p;do less SnpEff.5000bp.SV_GenomeFeature.classify.uniq.out | awk '$2 == "'${p}'"' | awk '$3<0.01{a++}$3>=0.01&&$3<0.05{b++}$3>=0.05{c++}END{print "<1%", a, "1%~5%", b, ">=5%", c}' | while read s;do echo -ne "${p}\t${s}\n";done;done | awk '{print $0"\t"$3+$5+$7"\t"$3/($3+$5+$7)"\t"$5/($3+$5+$7)"\t"$7/($3+$5+$7)}' | awk '{print $1"\t"$8"\t"$9"\t"$10"\t"$11}' | sed '1iType\tNum\tMAF<1%\t1%<=MAF<5%\tMAF>=5%' > SnpEff.5000bp.SV_GenomeFeature.classify.uniq.out.summary.graph.txt

less SnpEff.5000bp.SV_GenomeFeature.classify.out | grep "DEL\s" | awk '{print $1"\t"$3"\t"$4}' | sort | uniq > SnpEff.5000bp.SV-DEL_GenomeFeature.classify.uniq.out
less SnpEff.5000bp.SV-DEL_GenomeFeature.classify.uniq.out | awk '{print $2}' | sort | uniq | while read p;do less SnpEff.5000bp.SV-DEL_GenomeFeature.classify.uniq.out | awk '$2 == "'${p}'"' | awk '$3<0.01{a++}$3>=0.01&&$3<0.05{b++}$3>=0.05{c++}END{print "<1%", a, "1%~5%", b, ">=5%", c}' | while read s;do echo -ne "${p}\t${s}\n";done;done | awk '{print $0"\t"$3+$5+$7"\t"$3/($3+$5+$7)"\t"$5/($3+$5+$7)"\t"$7/($3+$5+$7)}' | awk '{print $1"\t"$8"\t"$9"\t"$10"\t"$11}' | sed '1iType\tNum\tMAF<1%\t1%<=MAF<5%\tMAF>=5%' > SnpEff.5000bp.SV-DEL_GenomeFeature.classify.uniq.out.summary.graph.txt

less SnpEff.5000bp.SV_GenomeFeature.classify.out | grep "INS\s" | awk '{print $1"\t"$3"\t"$4}' | sort | uniq > SnpEff.5000bp.SV-INS_GenomeFeature.classify.uniq.out
less SnpEff.5000bp.SV-INS_GenomeFeature.classify.uniq.out | awk '{print $2}' | sort | uniq | while read p;do less SnpEff.5000bp.SV-INS_GenomeFeature.classify.uniq.out | awk '$2 == "'${p}'"' | awk '$3<0.01{a++}$3>=0.01&&$3<0.05{b++}$3>=0.05{c++}END{print "<1%", a, "1%~5%", b, ">=5%", c}' | while read s;do echo -ne "${p}\t${s}\n";done;done | awk '{print $0"\t"$3+$5+$7"\t"$3/($3+$5+$7)"\t"$5/($3+$5+$7)"\t"$7/($3+$5+$7)}' | awk '{print $1"\t"$8"\t"$9"\t"$10"\t"$11}' | sed '1iType\tNum\tMAF<1%\t1%<=MAF<5%\tMAF>=5%' > SnpEff.5000bp.SV-INS_GenomeFeature.classify.uniq.out.summary.graph.txt

less SnpEff.5000bp.SV_GenomeFeature.classify.out | grep "DUP\s" | awk '{print $1"\t"$3"\t"$4}' | sort | uniq > SnpEff.5000bp.SV-DUP_GenomeFeature.classify.uniq.out
less SnpEff.5000bp.SV-DUP_GenomeFeature.classify.uniq.out | awk '{print $2}' | sort | uniq | while read p;do less SnpEff.5000bp.SV-DUP_GenomeFeature.classify.uniq.out | awk '$2 == "'${p}'"' | awk '$3<0.01{a++}$3>=0.01&&$3<0.05{b++}$3>=0.05{c++}END{print "<1%", a, "1%~5%", b, ">=5%", c}' | while read s;do echo -ne "${p}\t${s}\n";done;done | awk '{print $0"\t"$3+$5+$7"\t"$3/($3+$5+$7)"\t"$5/($3+$5+$7)"\t"$7/($3+$5+$7)}' | awk '{print $1"\t"$8"\t"$9"\t"$10"\t"$11}' | sed '1iType\tNum\tMAF<1%\t1%<=MAF<5%\tMAF>=5%' > SnpEff.5000bp.SV-DUP_GenomeFeature.classify.uniq.out.summary.graph.txt

less SnpEff.5000bp.SV_GenomeFeature.classify.out | grep "INV\s" | awk '{print $1"\t"$3"\t"$4}' | sort | uniq > SnpEff.5000bp.SV-INV_GenomeFeature.classify.uniq.out
less SnpEff.5000bp.SV-INV_GenomeFeature.classify.uniq.out | awk '{print $2}' | sort | uniq | while read p;do less SnpEff.5000bp.SV-INV_GenomeFeature.classify.uniq.out | awk '$2 == "'${p}'"' | awk '$3<0.01{a++}$3>=0.01&&$3<0.05{b++}$3>=0.05{c++}END{print "<1%", a, "1%~5%", b, ">=5%", c}' | while read s;do echo -ne "${p}\t${s}\n";done;done | awk '{print $0"\t"$3+$5+$7"\t"$3/($3+$5+$7)"\t"$5/($3+$5+$7)"\t"$7/($3+$5+$7)}' | awk '{print $1"\t"$8"\t"$9"\t"$10"\t"$11}' | sed '1iType\tNum\tMAF<1%\t1%<=MAF<5%\tMAF>=5%' > SnpEff.5000bp.SV-INV_GenomeFeature.classify.uniq.out.summary.graph.txt


less SnpEff.5000bp.INDEL_GenomeFeature.classify.out | awk '{print $1"\t"$3"\t"$4}' | sort | uniq > SnpEff.5000bp.INDEL_GenomeFeature.classify.uniq.out
less SnpEff.5000bp.INDEL_GenomeFeature.classify.uniq.out | awk '{print $2}' | sort | uniq | while read p;do less SnpEff.5000bp.INDEL_GenomeFeature.classify.uniq.out | awk '$2 == "'${p}'"' | awk '$3<0.01{a++}$3>=0.01&&$3<0.05{b++}$3>=0.05{c++}END{print "<1%", a, "1%~5%", b, ">=5%", c}' | while read s;do echo -ne "${p}\t${s}\n";done;done | awk '{print $0"\t"$3+$5+$7"\t"$3/($3+$5+$7)"\t"$5/($3+$5+$7)"\t"$7/($3+$5+$7)}' | awk '{print $1"\t"$8"\t"$9"\t"$10"\t"$11}' | sed '1iType\tNum\tMAF<1%\t1%<=MAF<5%\tMAF>=5%' > SnpEff.5000bp.INDEL_GenomeFeature.classify.uniq.out.summary.graph.txt

less SnpEff.5000bp.SNP_GenomeFeature.classify.out | awk '{print $1"\t"$3"\t"$4}' | sort | uniq > SnpEff.5000bp.SNP_GenomeFeature.classify.uniq.out
less SnpEff.5000bp.SNP_GenomeFeature.classify.uniq.out | awk '{print $2}' | sort | uniq | while read p;do less SnpEff.5000bp.SNP_GenomeFeature.classify.uniq.out | awk '$2 == "'${p}'"' | awk '$3<0.01{a++}$3>=0.01&&$3<0.05{b++}$3>=0.05{c++}END{print "<1%", a, "1%~5%", b, ">=5%", c}' | while read s;do echo -ne "${p}\t${s}\n";done;done | awk '{print $0"\t"$3+$5+$7"\t"$3/($3+$5+$7)"\t"$5/($3+$5+$7)"\t"$7/($3+$5+$7)}' | awk '{print $1"\t"$8"\t"$9"\t"$10"\t"$11}' | sed '1iType\tNum\tMAF<1%\t1%<=MAF<5%\tMAF>=5%' > SnpEff.5000bp.SNP_GenomeFeature.classify.uniq.out.summary.graph.txt

