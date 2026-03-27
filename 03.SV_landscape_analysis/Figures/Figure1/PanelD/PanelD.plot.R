## 进入数据所在目录
setwd("~/Desktop/BGI/biodiversity/projects/Cyclone/Pig/analysis/Summary20260323/Figures/Figure1/PanelD")

library(ggplot2)
library(scales)
library(patchwork)
library(cowplot)


data1 <- read.delim("CycloneSEQ_DNBSEQ_DEL_length.tsv", header = FALSE)
p1 <- ggplot(data1, aes(x = V1, y = V2, color = V3)) + geom_line(linewidth = 0.7) +
  scale_y_log10(
    limits = c(1, 30000),
    breaks = c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 20000),
    labels = c("1", "", "", "", "", "", "", "", "", "10", "", "", "", "", "", "", "", "", "100", "", "", "", "", "", "", "", "", "1k", "", "", "", "", "", "", "", "", "10k", "20k")
  ) + 
  scale_x_log10(
    limits = c(50, 30000000),
    breaks = c(50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 2000000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000, 20000000, 30000000),
    labels = c("50", "", "", "", "", "100", "", "", "", "", "", "", "", "", "1k", "", "", "", "", "", "", "", "", "10k", "", "", "", "", "", "", "", "", "100k", "", "", "", "", "", "", "", "", "1M", "", "", "", "", "", "", "", "", "10M", "", "30M")
  ) + 
  theme_classic() + xlab("Allele size (bp)") + ylab("SVs Count") + labs(title = "DEL") + theme(legend.position = "none", axis.text.x = element_text(size = 7), plot.title = element_text(hjust = 0.5, vjust = -5))
  
  
data2 <- read.delim("CycloneSEQ_DNBSEQ_DUP_length.tsv", header = FALSE)
p2 <- ggplot(data2, aes(x = V1, y = V2, color = V3)) +  geom_line(linewidth = 0.7) + 
  scale_y_log10(
    limits = c(1, 30000),
    breaks = c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 20000),
    labels = c("1", "", "", "", "", "", "", "", "", "10", "", "", "", "", "", "", "", "", "100", "", "", "", "", "", "", "", "", "1k", "", "", "", "", "", "", "", "", "10k", "20k")
  ) + 
  scale_x_log10(
    limits = c(50, 30000000),
    breaks = c(50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 2000000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000, 20000000, 30000000),
    labels = c("50", "", "", "", "", "100", "", "", "", "", "", "", "", "", "1k", "", "", "", "", "", "", "", "", "10k", "", "", "", "", "", "", "", "", "100k", "", "", "", "", "", "", "", "", "1M", "", "", "", "", "", "", "", "", "10M", "", "30M")
  ) + 
  theme_classic() + xlab("Allele size (bp)") + ylab("SVs Count") + labs(title = "DUP") + theme(legend.position = "none", axis.text.x = element_text(size = 7), plot.title = element_text(hjust = 0.5, vjust = -5))


data3 <- read.delim("CycloneSEQ_DNBSEQ_INV_length.tsv", header = FALSE)
p3 <- ggplot(data3, aes(x = V1, y = V2, color = V3)) + geom_line(linewidth = 0.7) + 
  scale_y_log10(
    limits = c(1, 30000),
    breaks = c(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 20000),
    labels = c("1", "", "", "", "", "", "", "", "", "10", "", "", "", "", "", "", "", "", "100", "", "", "", "", "", "", "", "", "1k", "", "", "", "", "", "", "", "", "10k", "20k")
  ) + 
  scale_x_log10(
    limits = c(50, 30000000),
    breaks = c(50, 60, 70, 80, 90, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000, 200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 2000000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000, 20000000, 30000000),
    labels = c("50", "", "", "", "", "100", "", "", "", "", "", "", "", "", "1k", "", "", "", "", "", "", "", "", "10k", "", "", "", "", "", "", "", "", "100k", "", "", "", "", "", "", "", "", "1M", "", "", "", "", "", "", "", "", "10M", "", "30M")
  ) + 
  theme_classic() + xlab("Allele size (bp)") + ylab("SVs Count") + labs(title = "INV") + theme(legend.position = "none", axis.text.x = element_text(size = 7), plot.title = element_text(hjust = 0.5, vjust = -5))

data4  <- read.table("SV_count.graph.txt", quote="\"", comment.char="")
pdf("SV_count.graph.pdf", height = 3, width = 3); 
p4_1 <- ggplot(data4[data4$V2 == "DEL",], aes(x = V1, y = V3, fill=V1)) + geom_bar(stat = "identity") + 
  theme_classic() + theme(legend.position = "none") + xlab("") + ylab("") + 
  scale_x_discrete(labels = c("CycloneSEQ" = "LRS", "DNBSEQ" = "SRS")) + 
  scale_y_continuous(limits = c(0, 220000), breaks = c(0, 50000, 100000, 150000, 200000), labels = c("0", "50k", "100k", "150k", "200k")) +
  geom_text(aes(label = V2), position = position_dodge(width = 0.8), vjust = 2, hjust = 0.5, color = "white", size = 3)

data5 <- data4[data4$V2 != "DEL",]
p4_2 <- ggplot(data5[nrow(data5):1, ], aes(x = V1, y = V3, fill = V1)) + 
  geom_bar(stat = "identity", position = "stack", color = "black") + 
  theme_classic() + theme(legend.position = "none") + xlab("") + ylab("") + 
  scale_x_discrete(labels = c("CycloneSEQ" = "LRS", "DNBSEQ" = "SRS")) + 
  geom_text(aes(label = rev(V2)), position = position_dodge(width = 0.8), vjust = -1, hjust = 0.5, color = "white", size = 3) +
  scale_y_continuous(limits = c(0, 2000), breaks = c(0, 500, 1000, 1500), labels = c("0", "500", "1k", "1.5k"))

p4 <- p4_1 + p4_2
p4
dev.off()


legend_data <- data.frame(V3 = unique(data1$V3), x = 1, y = 1)
legend_plot <- ggplot(legend_data, aes(x, y, color = V3)) + 
  geom_line() + scale_color_discrete(labels = c("LRS", "SRS")) + 
  theme_void() + theme( legend.position = "top", legend.direction = "horizontal", legend.box = "horizontal", legend.text = element_text(size = 12)) + 
  guides(color = guide_legend(title = NULL, keywidth = unit(2, "cm"), keyheight = unit(1, "cm")))

combined <- legend_plot / (p1 + p2) / (p3 + p4) + plot_layout(heights = c(0.01, 1, 1))
ggsave("PanelD.png", combined, height = 7, width = 6, dpi = 300)
ggsave("PanelD.pdf", combined, height = 7, width = 6)