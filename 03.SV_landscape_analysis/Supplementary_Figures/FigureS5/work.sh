bcftools query -f '%CHROM\t%POS\t%SVTYPE\t%AF\n' Final.vcf.gz > SV_AF.txt

bcftools query -f '%CHROM\t%POS\t%ID\t%SVTYPE\t%AF\n' All.SV_SNP_Indel.ac1.rmdupPosTheSame_SNPIndelID.fill_tags.rmGT.vcf.gz | awk '{print $1"\t"$3"\t"$5}' | awk '{split($2,a,"_"); print $1"\t"a[length(a)-1]"\t"a[length(a)]"\t"$3"\t"$2}' | awk '{if($3 == "DEL" || $3 == "INV" || $3 == "INS" || $3 == "DUP") print $1"\t"$3"\t"$4"\t"$5; else if(length($2) == 1 && length($3) == 1) print $1"\tSNP\t"$4"\t"$5; else print $1"\tINDEL\t"$4"\t"$5}' | awk '{print $1"\t"$2"\t"$3}' > SV_SNP_INDEL_AF.clean.txt

bcftools query -f '%CHROM\t%POS\t%ID\t%SVTYPE\t%MAF\n' All.SV_SNP_Indel.ac1.rmdupPosTheSame_SNPIndelID.fill_tags.rmGT.vcf.gz | awk '{print $1"\t"$3"\t"$5}' | awk '{split($2,a,"_"); print $1"\t"a[length(a)-1]"\t"a[length(a)]"\t"$3"\t"$2}' | awk '{if($3 == "DEL" || $3 == "INV" || $3 == "INS" || $3 == "DUP") print $1"\t"$3"\t"$4"\t"$5; else if(length($2) == 1 && length($3) == 1) print $1"\tSNP\t"$4"\t"$5; else print $1"\tINDEL\t"$4"\t"$5}' | awk '{print $1"\t"$2"\t"$3}' > SV_SNP_INDEL_MAF.clean.txt

