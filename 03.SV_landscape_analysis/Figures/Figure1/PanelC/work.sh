less data.txt | awk 'NR >= 2 {split($1,a,"");print a[5]"\t"$2"\t"$4"\t"$3"\t"$5}' | sort -k1 -n | awk '{print NR"\t"$2"\tDEL\tstage"$1"\n"NR"\t"$3"\tINS\tstage"$1}' > AllStages.SVcount.DEL-INS.txt
less data.txt | awk 'NR >= 2 {split($1,a,"");print a[5]"\t"$2"\t"$4"\t"$3"\t"$5}' | sort -k1 -n | awk '{print NR"\t"$4"\tDUP\tstage"$1"\n"NR"\t"$5"\tINV\tstage"$1}' > AllStages.SVcount.DUP-INV.txt
