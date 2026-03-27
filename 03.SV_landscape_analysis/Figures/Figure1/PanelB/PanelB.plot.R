## 进入数据所在目录
setwd("~/Desktop/BGI/biodiversity/projects/Cyclone/Pig/analysis/Summary20260323/Figures/Figure1/PanelB")

library(ggplot2)
library(patchwork)

data <- read.csv("data.txt", sep="")

p_Coverage <- ggplot(data, aes(x = "", y = Coverage, fill = "")) + 
  geom_violin( width = 0.8, alpha = 0.6, trim = FALSE, color = "gray30", fill = "gray80", scale = "width" ) + 
  geom_boxplot(width = 0.25, alpha = 0.8, outlier.color = "red", outlier.shape = 19, outlier.size = 2, color = "black", fill = "lightblue") + 
  scale_fill_brewer(palette = "Pastel1") + theme_bw() + 
  stat_summary(fun = mean, geom = "point", shape = 18, size = 3, color = "darkblue", aes(group = "")) + 
  theme(panel.grid.major.y = element_line(color = "gray90", linetype = "dashed"), 
        legend.position = "none" ) + xlab("") + ylab("Cyclone sequence coverage (X)") + scale_y_continuous(limits = c(0, 50))

p_N50 <- ggplot(data, aes(x = "", y = N50, fill = "")) + 
  geom_violin( width = 0.8, alpha = 0.6, trim = FALSE, color = "gray30", fill = "gray80", scale = "width" ) + 
  geom_boxplot(width = 0.25, alpha = 0.8, outlier.color = "red", outlier.shape = 19, outlier.size = 2, color = "black", fill = "lightblue") + 
  scale_fill_brewer(palette = "Pastel1") + theme_bw() + 
  stat_summary(fun = mean, geom = "point", shape = 18, size = 3, color = "darkblue", aes(group = "")) + 
  theme(panel.grid.major.y = element_line(color = "gray90", linetype = "dashed"), 
        legend.position = "none" ) + xlab("") + ylab("Read N50 (bp)") + 
  scale_y_continuous(limits = c(0, 30000), breaks = c(0, 10000, 20000, 30000), labels = c("0k", "10k", "20k", "30k"))

p_AvgLen <- ggplot(data, aes(x = "", y = Base_num / Read_num, fill = "")) + 
  geom_violin( width = 0.8, alpha = 0.6, trim = FALSE, color = "gray30", fill = "gray80", scale = "width" ) + 
  geom_boxplot(width = 0.25, alpha = 0.8, outlier.color = "red", outlier.shape = 19, outlier.size = 2, color = "black", fill = "lightblue") + 
  scale_fill_brewer(palette = "Pastel1") + theme_bw() + stat_summary(fun = mean, geom = "point", shape = 18, size = 3, color = "darkblue", aes(group = "")) + 
  theme(panel.grid.major.y = element_line(color = "gray90", linetype = "dashed"), 
        legend.position = "none" ) + xlab("") + ylab("Read average length (bp)") + 
  scale_y_continuous(limits = c(0, 20000), breaks = c(0, 5000, 10000, 15000, 20000), labels = c("0k", "5k", "10k", "15k", "20k"))


combined <- p_Coverage + p_N50 + p_AvgLen
ggsave("PanelB.png", combined, width = 12, height = 8, dpi = 300)
ggsave("PanelB.pdf", combined, width = 12, height = 8)