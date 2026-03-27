## 进入数据所在目录
setwd("~/Desktop/BGI/biodiversity/projects/Cyclone/Pig/analysis/Summary20260323/Supplementary_Figures/FigureS3")

library(ggplot2)
library(patchwork)
library(cowplot)

data <- read.csv("plot.txt", sep="")

p1 <- ggplot(data,  aes(x= Coverage, y = N50, color = X5x)) + geom_point(size = 2.5, alpha = 0.8, shape = 16) + theme_classic() +
  scale_color_gradientn(colors = c("#FF8C00", "#FFD700", "#ADFF2F", "#32CD32", "#FF4500", "#FF0000")) +
  scale_x_log10(limits = c(10,200), breaks = c(10, 20, 30, 40, 50, 100, 150, 200), labels = c("10", "20", "30", "40", "50", "100", "150", "200")) + 
  scale_y_continuous(limits = c(0, 35000), breaks = c(10000, 20000, 30000), labels = c("10k", "20k", "30k")) +
  ylab("N50 (bp)") + xlab("Coverage (X)") + labs(color = ">= five-fold") + 
  theme(panel.grid = element_blank(), axis.line = element_line(color = "black", linewidth = 0.5), 
        axis.ticks = element_line(color = "black"),
        axis.text = element_text(size = 12, color = "black"),
        axis.title = element_text(size = 14, face = "bold"),
        legend.position = "right",
        legend.key.height = unit(1.5, "cm"), 
        legend.key.width = unit(0.8, "cm"),
        legend.text = element_text(size = 11),
        plot.margin = margin(t = 10, r = 20, b = 10, l = 10))

p2 <- ggplot(data,  aes(x= Coverage, y = N50, color = X10x)) + geom_point(size = 2.5, alpha = 0.8, shape = 16) + theme_classic() +
  scale_color_gradientn(colors = c("#FF8C00", "#FFD700", "#ADFF2F", "#32CD32", "#FF4500", "#FF0000")) +
  scale_x_log10(limits = c(10,200), breaks = c(10, 20, 30, 40, 50, 100, 150, 200), labels = c("10", "20", "30", "40", "50", "100", "150", "200")) + 
  scale_y_continuous(limits = c(0, 35000), breaks = c(10000, 20000, 30000), labels = c("10k", "20k", "30k")) +
  ylab("N50 (bp)") + xlab("Coverage (X)") + labs(color = ">= ten-fold") + 
  theme(panel.grid = element_blank(), axis.line = element_line(color = "black", linewidth = 0.5), 
        axis.ticks = element_line(color = "black"),
        axis.text = element_text(size = 12, color = "black"),
        axis.title = element_text(size = 14, face = "bold"),
        legend.position = "right",
        legend.key.height = unit(1.5, "cm"), 
        legend.key.width = unit(0.8, "cm"),
        legend.text = element_text(size = 11),
        plot.margin = margin(t = 10, r = 20, b = 10, l = 10))


combined <- plot_grid(p1, p2, nrow = 2, labels = c("A", "B"), label_size = 14, label_fontface = "bold")
ggsave("FigureS3.png", combined, height = 8, width = 8, dpi = 300)
ggsave("FigureS3.pdf", combined, height = 8, width = 8)