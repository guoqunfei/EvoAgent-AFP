
setwd("~/Desktop/BGI/biodiversity/projects/Cyclone/Pig/analysis/Summary20260323/Supplementary_Figures/FigureS5")

# ============================================
# SV频率分布图 - RStudio版本
# ============================================

# 读取数据
data <- read.table("SV_SNP_INDEL_AF.clean.txt", header = FALSE, sep = "\t")
colnames(data) <- c("chr", "type", "freq")

# 查看数据摘要
cat("数据维度:", nrow(data), "行\n")
cat("\nSV类型分布:\n")
print(table(data$type))

# 创建频率区间（0.005为间隔）
breaks <- seq(0, 1, by = 0.005)
bin_centers <- (head(breaks, -1) + tail(breaks, -1)) / 2

# 统计每种类型的SV在每个区间的数量
sv_types <- c("DEL", "INS", "INV", "DUP", "SNP", "INDEL")
counts <- matrix(0, nrow = length(bin_centers), ncol = length(sv_types))
colnames(counts) <- sv_types

for (i in seq_along(sv_types)) {
  type_data <- data$freq[data$type == sv_types[i]]
  if (length(type_data) > 0) {
    counts[, i] <- hist(type_data, breaks = breaks, plot = FALSE)$counts
  }
}

# 创建数据框
plot_data <- data.frame(
  freq = bin_centers,
  Deletion = counts[, "DEL"],
  Insertion = counts[, "INS"],
  Inversion = counts[, "INV"],
  Duplication = counts[, "DUP"],
  SNP = counts[, "SNP"],
  INDEL = counts[, "INDEL"]
)

# 加载必要的包
library(ggplot2)
library(reshape2)

# 转换为长格式
plot_long <- melt(plot_data, id.vars = "freq", variable.name = "SV_type", value.name = "count")

# 设置颜色
colors <- c(
  "Deletion" = "#2E8B57",      # 深绿色
  "Insertion" = "#6B5B95",     # 紫色
  "Inversion" = "#5F9EA0",     # 蓝绿色
  "Duplication" = "#F0E68C",    # 浅黄色
  "SNP" = "#F8766D",
  "INDEL" = "#00BFC4"
)

# 绘制图表
plot_long_filter <- plot_long %>% filter(count > 0)

p1 <- ggplot(plot_long_filter, aes(x = freq, y = count, color = SV_type)) +
  geom_line(linewidth = 1.2) +
  scale_y_log10(
    limits = c(1, 25000000),
    breaks = c(1,2,3,4,5,6,7,8,9, 10,20,30,40,50,60,70,80,90, 100,200,300,400,500,600,700,800,900, 1000,2000,3000,4000,5000,6000,7000,8000,9000, 10000,20000,30000,40000,50000,60000,70000,80000,90000, 100000,200000,300000,400000,500000,600000,700000,800000,900000, 1000000,2000000,3000000,4000000,5000000,6000000,7000000,8000000,9000000, 10000000),
    labels = c("1","","","","","","","","", "10","","","","","","","","", "100","","","","","","","","", "1k","","","","","","","","", "10k","","","","","","","","", "100k", "","","","","","","","", "1M","","","","","","","","", "10M")
  ) +
  scale_x_continuous(
    breaks = seq(0, 1, by = 0.2),
    labels = c("0", "0.2", "0.4", "0.6", "0.8", "1")
  ) +
  scale_color_manual(values = colors) +
  labs(
    title = "SV/SNP/INDEL frequency in 591 accessions",
    x = "Frequeny of SVs/SNPs/INDELs",
    y = "Number of SVs/SNPs/INDELs",
    color = "SV type"
  ) +
  theme_classic() +
  theme(
    plot.title = element_text(hjust = 0.5, size = 16, face = "bold"),
    axis.title = element_text(size = 14),
    axis.text = element_text(size = 12),
    legend.box = "horizontal",
    legend.box.just = "center",
    legend.spacing.x = unit(1, "cm"),
    legend.position = c(0.5, 0.9),
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 10),
    #legend.background = element_rect(fill = "white", color = NA),
    axis.line = element_line(color = "black", linewidth = 0.8),
    axis.ticks = element_line(color = "black", linewidth = 0.8)
  ) +
  guides(color = guide_legend(nrow = 2))

# 显示图表
print(p1)

# 保存图表到原文件目录
ggsave("SV-SNP-INDEL_AF_plot.png", p1, width = 6, height = 5, dpi = 300)
ggsave("SV-SNP-INDEL_AF_plot.pdf", p1, width = 6, height = 5)


# 读取数据
data <- read.table("SV_SNP_INDEL_MAF.clean.txt", header = FALSE, sep = "\t")
colnames(data) <- c("chr", "type", "freq")

# 查看数据摘要
cat("数据维度:", nrow(data), "行\n")
cat("\nSV类型分布:\n")
print(table(data$type))

# 创建频率区间（0.005为间隔）
breaks <- seq(0, 1, by = 0.005)
bin_centers <- (head(breaks, -1) + tail(breaks, -1)) / 2

# 统计每种类型的SV在每个区间的数量
sv_types <- c("DEL", "INS", "INV", "DUP", "SNP", "INDEL")
counts <- matrix(0, nrow = length(bin_centers), ncol = length(sv_types))
colnames(counts) <- sv_types

for (i in seq_along(sv_types)) {
  type_data <- data$freq[data$type == sv_types[i]]
  if (length(type_data) > 0) {
    counts[, i] <- hist(type_data, breaks = breaks, plot = FALSE)$counts
  }
}

# 创建数据框
plot_data <- data.frame(
  freq = bin_centers,
  Deletion = counts[, "DEL"],
  Insertion = counts[, "INS"],
  Inversion = counts[, "INV"],
  Duplication = counts[, "DUP"],
  SNP = counts[, "SNP"],
  INDEL = counts[, "INDEL"]
)

# 加载必要的包
library(ggplot2)
library(reshape2)

# 转换为长格式
plot_long <- melt(plot_data, id.vars = "freq", variable.name = "SV_type", value.name = "count")

# 设置颜色
colors <- c(
  "Deletion" = "#2E8B57",      # 深绿色
  "Insertion" = "#6B5B95",     # 紫色
  "Inversion" = "#5F9EA0",     # 蓝绿色
  "Duplication" = "#F0E68C",    # 浅黄色
  "SNP" = "#F8766D",
  "INDEL" = "#00BFC4"
)

library(dplyr)
# 绘制图表
plot_long_filter <- plot_long %>% filter(count > 0)

p2 <- ggplot(plot_long_filter, aes(x = freq, y = count, color = SV_type)) +
  geom_line(linewidth = 1.2) +
  scale_y_log10(
    limits = c(1, 25000000),
    breaks = c(1,2,3,4,5,6,7,8,9, 10,20,30,40,50,60,70,80,90, 100,200,300,400,500,600,700,800,900, 1000,2000,3000,4000,5000,6000,7000,8000,9000, 10000,20000,30000,40000,50000,60000,70000,80000,90000, 100000,200000,300000,400000,500000,600000,700000,800000,900000, 1000000,2000000,3000000,4000000,5000000,6000000,7000000,8000000,9000000, 10000000),
    labels = c("1","","","","","","","","", "10","","","","","","","","", "100","","","","","","","","", "1k","","","","","","","","", "10k","","","","","","","","", "100k", "","","","","","","","", "1M","","","","","","","","", "10M")
  ) +
  scale_x_continuous(
    limits = c(0, 0.5),
    breaks = c(0.01, 0.05, 0.1, 0.2, 0.5),
    labels = c("0.01", "0.05", "0.1", "0.2", "0.5")
  ) + 
  #scale_x_continuous(
  #  breaks = seq(0, 1, by = 0.2),
  #  labels = c("0", "0.2", "0.4", "0.6", "0.8", "1")
  #) +
  scale_color_manual(values = colors) +
  labs(
    title = "SV/SNP/INDEL frequency in 591 accessions",
    x = "Minor allele frequeny",
    y = "Number of SVs/SNPs/INDELs",
    color = "SV type"
  ) +
  theme_classic() +
  theme(
    plot.title = element_text(hjust = 0.5, size = 16, face = "bold"),
    axis.title = element_text(size = 14),
    axis.text = element_text(size = 12),
    legend.box = "horizontal",
    legend.box.just = "center",
    legend.spacing.x = unit(1, "cm"),
    legend.position = c(0.5, 0.9),
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 10),
    #legend.background = element_rect(fill = "white", color = NA),
    axis.line = element_line(color = "black", linewidth = 0.8),
    axis.ticks = element_line(color = "black", linewidth = 0.8)
  ) +
  guides(color = guide_legend(nrow = 2))

# 显示图表
print(p2)

# 保存图表到原文件目录
ggsave("SV-SNP-INDEL_MAF_plot.png", p2, width = 6, height = 5, dpi = 300)
ggsave("SV-SNP-INDEL_MAF_plot.pdf", p2, width = 6, height = 5)


# 读取数据
data <- read.table("SV_AF.txt", header = FALSE, sep = "\t")
colnames(data) <- c("chr", "pos", "type", "freq")

# 查看数据摘要
cat("数据维度:", nrow(data), "行\n")
cat("\nSV类型分布:\n")
print(table(data$type))

# 创建频率区间（0.005为间隔）
breaks <- seq(0, 1, by = 0.005)
bin_centers <- (head(breaks, -1) + tail(breaks, -1)) / 2

# 统计每种类型的SV在每个区间的数量
sv_types <- c("DEL", "INS", "INV", "DUP")
counts <- matrix(0, nrow = length(bin_centers), ncol = length(sv_types))
colnames(counts) <- sv_types

for (i in seq_along(sv_types)) {
  type_data <- data$freq[data$type == sv_types[i]]
  if (length(type_data) > 0) {
    counts[, i] <- hist(type_data, breaks = breaks, plot = FALSE)$counts
  }
}

# 创建数据框
plot_data <- data.frame(
  freq = bin_centers,
  Deletion = counts[, "DEL"],
  Insertion = counts[, "INS"],
  Inversion = counts[, "INV"],
  Duplication = counts[, "DUP"]
)

# 加载必要的包
library(ggplot2)
library(reshape2)

# 转换为长格式
plot_long <- melt(plot_data, id.vars = "freq", variable.name = "SV_type", value.name = "count")

# 设置颜色
colors <- c(
  "Deletion" = "#2E8B57",      # 深绿色
  "Insertion" = "#6B5B95",     # 紫色
  "Inversion" = "#5F9EA0",     # 蓝绿色
  "Duplication" = "#F0E68C"    # 浅黄色
)

# 绘制图表
plot_long_filter <- plot_long %>% filter(count > 0)

p3 <- ggplot(plot_long_filter, aes(x = freq, y = count, color = SV_type)) +
  geom_line(linewidth = 1.2) +
  scale_y_log10(
    limits = c(1, 200000),
    breaks = c(1,2,3,4,5,6,7,8,9, 10,20,30,40,50,60,70,80,90, 100,200,300,400,500,600,700,800,900, 1000,2000,3000,4000,5000,6000,7000,8000,9000, 10000,20000,30000,40000,50000,60000,70000,80000,90000, 100000, 200000),
    labels = c("1","","","","","","","","", "10","","","","","","","","", "100","","","","","","","","", "1k","","","","","","","","", "10k","","","","","","","","", "100k", "200k")
  ) +
  scale_x_continuous(
    breaks = seq(0, 1, by = 0.2),
    labels = c("0", "0.2", "0.4", "0.6", "0.8", "1")
  ) +
  scale_color_manual(values = colors) +
  labs(
    title = "SV frequency in 591 accessions",
    x = "Frequency of SVs",
    y = "Number of SVs",
    color = "SV type"
  ) +
  theme_classic() +
  theme(
    plot.title = element_text(hjust = 0.5, size = 16, face = "bold"),
    axis.title = element_text(size = 14),
    axis.text = element_text(size = 12),
    legend.position = c(0.7, 0.8),
    legend.title = element_text(size = 12, face = "bold"),
    legend.text = element_text(size = 10),
    legend.background = element_rect(fill = "white", color = NA),
    axis.line = element_line(color = "black", linewidth = 0.8),
    axis.ticks = element_line(color = "black", linewidth = 0.8)
  )

# 显示图表
print(p3)

# 保存图表到原文件目录
ggsave("SV_frequency_plot.png", p3, width = 6, height = 5, dpi = 300)
ggsave("SV_frequency_plot.pdf", p3, width = 6, height = 5)

library(patchwork)
p4 <- p1 + p2 + p3 + plot_annotation(tag_levels = c('A', 'B', 'C'))
# 保存图表到原文件目录
ggsave("FigureS5.png", p4, width = 18, height = 5, dpi = 300)
ggsave("FigureS5.pdf", p4, width = 18, height = 5)
