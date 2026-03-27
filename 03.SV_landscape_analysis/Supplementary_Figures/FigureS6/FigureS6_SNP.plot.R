setwd("~/Desktop/BGI/biodiversity/projects/Cyclone/Pig/analysis/Summary20260323/Supplementary_Figures/FigureS6")

# 加载必要的包
library(ggplot2)
library(ggpubr)
library(rstatix)
library(dplyr)
library(patchwork)

# 读取数据 - 确保列名匹配
data <- read.delim("SNP_HET_HOM.count.addinfo.txt")

# 确保Stage是因子类型并按正确顺序排列
data$Stage <- factor(data$Stage, levels = c("Stage1", "Stage2", "Stage3", "Stage4"))

# 统计学检验
dunn_result <- dunn_test(HOM ~ Stage, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
stage_levels <- levels(data$Stage)
stage_positions <- setNames(1:length(stage_levels), stage_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HOM) * 1.05
  step_y <- max(data$HOM) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = stage_levels)),
      x2 = as.numeric(factor(group2, levels = stage_levels))
    )
}

# 创建箱线图
p1 <- ggplot(data, aes(x = Stage, y = HOM)) +
  geom_boxplot(
    aes(fill = Stage),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(2000000, 4500000),
    breaks = c(2000000, 2500000, 3000000, 3500000, 4000000, 4500000),
    labels = c("2M", "2.5M", "3M", "3.5M", "4M", "4.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "Stage",
    x = "HOM",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p1 <- p1 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
  ## 扩展y轴空间
  ## + coord_cartesian(ylim = c(min(data$HOM) * 0.95, max(signif_data$y.position) * 1))
}

# 保存图标到原文件目录
ggsave("SNP_HOM_Stages_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_HOM_Stages_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 统计学检验
dunn_result <- dunn_test(HET ~ Stage, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
stage_levels <- levels(data$Stage)
stage_positions <- setNames(1:length(stage_levels), stage_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HET) * 1.05
  step_y <- max(data$HET) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = stage_levels)),
      x2 = as.numeric(factor(group2, levels = stage_levels))
    )
}

# 创建箱线图
p2 <- ggplot(data, aes(x = Stage, y = HET)) +
  geom_boxplot(
    aes(fill = Stage),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(4000000, 8500000),
    breaks = c(4000000, 4500000, 5000000, 5500000, 6000000, 6500000, 7000000, 7500000, 8000000, 8500000),
    labels = c("4M", "4.5M", "5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "Stage",
    x = "HET",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  )

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p2 <- p2 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
  ## 扩展y轴空间
  ## + coord_cartesian(ylim = c(min(data$HOM_Count) * 0.95, max(signif_data$y.position) * 1))
}

# 保存图标到原文件目录
ggsave("SNP_HET_Stages_comparison_with_significance.png", p2, width = 6, height = 4, dpi = 300)
ggsave("SNP_HET_Stages_comparison_with_significance.pdf", p2, width = 6, height = 4)


# 确保Farm是因子类型并按正确顺序排列
data$Farm <- factor(data$Farm, levels = c("CH", "HM", "ZQ"))

# 统计学检验
dunn_result <- dunn_test(HOM ~ Farm, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
farm_levels <- levels(data$Farm)
farm_positions <- setNames(1:length(farm_levels), farm_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HOM) * 1.05
  step_y <- max(data$HOM) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = farm_levels)),
      x2 = as.numeric(factor(group2, levels = farm_levels))
    )
}

# 创建箱线图
p3 <- ggplot(data, aes(x = Farm, y = HOM)) +
  geom_boxplot(
    aes(fill = Farm),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(2000000, 4500000),
    breaks = c(2000000, 2500000, 3000000, 3500000, 4000000, 4500000),
    labels = c("2M", "2.5M", "3M", "3.5M", "4M", "4.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "Farm",
    x = "HOM",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p3 <- p3 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_HOM_Farms_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_HOM_Farms_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 统计学检验
dunn_result <- dunn_test(HET ~ Farm, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
farm_levels <- levels(data$Farm)
farm_positions <- setNames(1:length(farm_levels), farm_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HET) * 1.05
  step_y <- max(data$HET) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = farm_levels)),
      x2 = as.numeric(factor(group2, levels = farm_levels))
    )
}

# 创建箱线图
p4 <- ggplot(data, aes(x = Farm, y = HET)) +
  geom_boxplot(
    aes(fill = Farm),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(4000000, 8500000),
    breaks = c(4000000, 4500000, 5000000, 5500000, 6000000, 6500000, 7000000, 7500000, 8000000, 8500000),
    labels = c("4M", "4.5M", "5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "Farm",
    x = "HET",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p4 <- p4 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_HET_Farms_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_HET_Farms_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 确保Strain是因子类型并按正确顺序排列
data$Strain <- factor(data$Strain, levels = c("LY", "YL"))

# 统计学检验
dunn_result <- dunn_test(HOM ~ Strain, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
strain_levels <- levels(data$Strain)
strain_positions <- setNames(1:length(strain_levels), strain_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HOM) * 1.05
  step_y <- max(data$HOM) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = strain_levels)),
      x2 = as.numeric(factor(group2, levels = strain_levels))
    )
}

# 创建箱线图
p5 <- ggplot(data, aes(x = Strain, y = HOM)) +
  geom_boxplot(
    aes(fill = Strain),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(2000000, 4500000),
    breaks = c(2000000, 2500000, 3000000, 3500000, 4000000, 4500000),
    labels = c("2M", "2.5M", "3M", "3.5M", "4M", "4.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "Strain",
    x = "HOM",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p5 <- p5 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_HOM_Strains_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_HOM_Strains_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 统计学检验
dunn_result <- dunn_test(HET ~ Strain, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
strain_levels <- levels(data$Strain)
strain_positions <- setNames(1:length(strain_levels), strain_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HET) * 1.05
  step_y <- max(data$HET) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = strain_levels)),
      x2 = as.numeric(factor(group2, levels = strain_levels))
    )
}

# 创建箱线图
p6 <- ggplot(data, aes(x = Strain, y = HET)) +
  geom_boxplot(
    aes(fill = Strain),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(4000000, 8500000),
    breaks = c(4000000, 4500000, 5000000, 5500000, 6000000, 6500000, 7000000, 7500000, 8000000, 8500000),
    labels = c("4M", "4.5M", "5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "Strain",
    x = "HET",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p6 <- p6 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_HET_Strains_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_HET_Strains_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 确保Sex是因子类型并按正确顺序排列
data$Sex <- factor(data$Sex, levels = c("F", "M"))

# 统计学检验
dunn_result <- dunn_test(HOM ~ Sex, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
sex_levels <- levels(data$Sex)
sex_positions <- setNames(1:length(sex_levels), sex_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HOM) * 1.05
  step_y <- max(data$HOM) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = sex_levels)),
      x2 = as.numeric(factor(group2, levels = sex_levels))
    )
}

# 创建箱线图
p7 <- ggplot(data, aes(x = Sex, y = HOM)) +
  geom_boxplot(
    aes(fill = Sex),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(2000000, 4500000),
    breaks = c(2000000, 2500000, 3000000, 3500000, 4000000, 4500000),
    labels = c("2M", "2.5M", "3M", "3.5M", "4M", "4.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  scale_x_discrete(labels = c("F" = "Female", "M" = "Male")) + 
  labs(
    title = "Sex",
    x = "HOM",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p7 <- p7 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_HOM_Sexs_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_HOM_Sexs_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 统计学检验
dunn_result <- dunn_test(HET ~ Sex, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
sex_levels <- levels(data$Sex)
sex_positions <- setNames(1:length(sex_levels), sex_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HET) * 1.05
  step_y <- max(data$HET) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = sex_levels)),
      x2 = as.numeric(factor(group2, levels = sex_levels))
    )
}

# 创建箱线图
p8 <- ggplot(data, aes(x = Sex, y = HET)) +
  geom_boxplot(
    aes(fill = Sex),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(4000000, 8500000),
    breaks = c(4000000, 4500000, 5000000, 5500000, 6000000, 6500000, 7000000, 7500000, 8000000, 8500000),
    labels = c("4M", "4.5M", "5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "Sex",
    x = "HET",
    y = "SNPs Count"
  ) +
  scale_x_discrete(labels = c("F" = "Female", "M" = "Male")) + 
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p8 <- p8 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_HET_Sexs_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_HET_Sexs_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 读取数据 - 确保列名匹配
data <- read.delim("MAF0.05_SNP_HET_HOM.count.addinfo.txt")

# 确保Stage是因子类型并按正确顺序排列
data$Stage <- factor(data$Stage, levels = c("Stage1", "Stage2", "Stage3", "Stage4"))

# 统计学检验
dunn_result <- dunn_test(HOM ~ Stage, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
stage_levels <- levels(data$Stage)
stage_positions <- setNames(1:length(stage_levels), stage_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HOM) * 1.05
  step_y <- max(data$HOM) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = stage_levels)),
      x2 = as.numeric(factor(group2, levels = stage_levels))
    )
}

# 创建箱线图
p9 <- ggplot(data, aes(x = Stage, y = HOM)) +
  geom_boxplot(
    aes(fill = Stage),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(2000000, 4500000),
    breaks = c(2000000, 2500000, 3000000, 3500000, 4000000, 4500000),
    labels = c("2M", "2.5M", "3M", "3.5M", "4M", "4.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "MAF0.05_Stage",
    x = "HOM",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p9 <- p9 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
  ## 扩展y轴空间
  ## + coord_cartesian(ylim = c(min(data$HOM) * 0.95, max(signif_data$y.position) * 1))
}

# 保存图标到原文件目录
ggsave("SNP_MAF0.05_HOM_Stages_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_MAF0.05_HOM_Stages_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 统计学检验
dunn_result <- dunn_test(HET ~ Stage, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
stage_levels <- levels(data$Stage)
stage_positions <- setNames(1:length(stage_levels), stage_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HET) * 1.05
  step_y <- max(data$HET) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = stage_levels)),
      x2 = as.numeric(factor(group2, levels = stage_levels))
    )
}

# 创建箱线图
p10 <- ggplot(data, aes(x = Stage, y = HET)) +
  geom_boxplot(
    aes(fill = Stage),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(4000000, 8500000),
    breaks = c(4000000, 4500000, 5000000, 5500000, 6000000, 6500000, 7000000, 7500000, 8000000, 8500000),
    labels = c("4M", "4.5M", "5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "MAF0.05_Stage",
    x = "HET",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  )

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p10 <- p10 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
  ## 扩展y轴空间
  ## + coord_cartesian(ylim = c(min(data$HOM_Count) * 0.95, max(signif_data$y.position) * 1))
}

# 保存图标到原文件目录
ggsave("SNP_MAF0.05_HET_Stages_comparison_with_significance.png", p2, width = 6, height = 4, dpi = 300)
ggsave("SNP_MAF0.05_HET_Stages_comparison_with_significance.pdf", p2, width = 6, height = 4)


# 确保Farm是因子类型并按正确顺序排列
data$Farm <- factor(data$Farm, levels = c("CH", "HM", "ZQ"))

# 统计学检验
dunn_result <- dunn_test(HOM ~ Farm, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
farm_levels <- levels(data$Farm)
farm_positions <- setNames(1:length(farm_levels), farm_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HOM) * 1.05
  step_y <- max(data$HOM) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = farm_levels)),
      x2 = as.numeric(factor(group2, levels = farm_levels))
    )
}

# 创建箱线图
p11 <- ggplot(data, aes(x = Farm, y = HOM)) +
  geom_boxplot(
    aes(fill = Farm),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(2000000, 4500000),
    breaks = c(2000000, 2500000, 3000000, 3500000, 4000000, 4500000),
    labels = c("2M", "2.5M", "3M", "3.5M", "4M", "4.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "MAF0.05_Farm",
    x = "HOM",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p11 <- p11 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_MAF0.05_HOM_Farms_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_MAF0.05_HOM_Farms_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 统计学检验
dunn_result <- dunn_test(HET ~ Farm, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
farm_levels <- levels(data$Farm)
farm_positions <- setNames(1:length(farm_levels), farm_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HET) * 1.05
  step_y <- max(data$HET) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = farm_levels)),
      x2 = as.numeric(factor(group2, levels = farm_levels))
    )
}

# 创建箱线图
p12 <- ggplot(data, aes(x = Farm, y = HET)) +
  geom_boxplot(
    aes(fill = Farm),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(4000000, 8500000),
    breaks = c(4000000, 4500000, 5000000, 5500000, 6000000, 6500000, 7000000, 7500000, 8000000, 8500000),
    labels = c("4M", "4.5M", "5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "MAF0.05_Farm",
    x = "HET",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p12 <- p12 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_MAF0.05_HET_Farms_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_MAF0.05_HET_Farms_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 确保Strain是因子类型并按正确顺序排列
data$Strain <- factor(data$Strain, levels = c("LY", "YL"))

# 统计学检验
dunn_result <- dunn_test(HOM ~ Strain, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
strain_levels <- levels(data$Strain)
strain_positions <- setNames(1:length(strain_levels), strain_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HOM) * 1.05
  step_y <- max(data$HOM) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = strain_levels)),
      x2 = as.numeric(factor(group2, levels = strain_levels))
    )
}

# 创建箱线图
p13 <- ggplot(data, aes(x = Strain, y = HOM)) +
  geom_boxplot(
    aes(fill = Strain),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(2000000, 4500000),
    breaks = c(2000000, 2500000, 3000000, 3500000, 4000000, 4500000),
    labels = c("2M", "2.5M", "3M", "3.5M", "4M", "4.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "MAF0.05_Strain",
    x = "HOM",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p13 <- p13 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_MAF0.05_HOM_Strains_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_MAF0.05_HOM_Strains_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 统计学检验
dunn_result <- dunn_test(HET ~ Strain, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
strain_levels <- levels(data$Strain)
strain_positions <- setNames(1:length(strain_levels), strain_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HET) * 1.05
  step_y <- max(data$HET) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = strain_levels)),
      x2 = as.numeric(factor(group2, levels = strain_levels))
    )
}

# 创建箱线图
p14 <- ggplot(data, aes(x = Strain, y = HET)) +
  geom_boxplot(
    aes(fill = Strain),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(4000000, 8500000),
    breaks = c(4000000, 4500000, 5000000, 5500000, 6000000, 6500000, 7000000, 7500000, 8000000, 8500000),
    labels = c("4M", "4.5M", "5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "MAF0.05_Strain",
    x = "HET",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
    #panel.grid.major.x = element_blank(),
    #panel.border = element_rect(color = "gray80", fill = NA, linewidth = 0.5)
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p14 <- p14 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_MAF0.05_HET_Strains_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_MAF0.05_HET_Strains_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 确保Sex是因子类型并按正确顺序排列
data$Sex <- factor(data$Sex, levels = c("F", "M"))

# 统计学检验
dunn_result <- dunn_test(HOM ~ Sex, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
sex_levels <- levels(data$Sex)
sex_positions <- setNames(1:length(sex_levels), sex_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HOM) * 1.05
  step_y <- max(data$HOM) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = sex_levels)),
      x2 = as.numeric(factor(group2, levels = sex_levels))
    )
}

# 创建箱线图
p15 <- ggplot(data, aes(x = Sex, y = HOM)) +
  geom_boxplot(
    aes(fill = Sex),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(2000000, 4500000),
    breaks = c(2000000, 2500000, 3000000, 3500000, 4000000, 4500000),
    labels = c("2M", "2.5M", "3M", "3.5M", "4M", "4.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  scale_x_discrete(labels = c("F" = "Female", "M" = "Male")) + 
  labs(
    title = "MAF0.05_Sex",
    x = "HOM",
    y = "SNPs Count"
  ) +
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p15 <- p15 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_MAF0.05_HOM_Sexs_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_MAF0.05_HOM_Sexs_comparison_with_significance.pdf", p1, width = 6, height = 4)


# 统计学检验
dunn_result <- dunn_test(HET ~ Sex, data = data, p.adjust.method = "bonferroni")

# 只保留p<0.05的显著结果
signif_data <- dunn_result %>% 
  filter(p.adj < 0.05) %>%
  mutate(
    label = case_when(
      p.adj < 0.001 ~ "***",
      p.adj < 0.01 ~ "**",
      p.adj < 0.05 ~ "*"
    )
  )

# 创建数值映射
sex_levels <- levels(data$Sex)
sex_positions <- setNames(1:length(sex_levels), sex_levels)

# 计算每个比较对的y位置
if(nrow(signif_data) > 0) {
  base_y <- max(data$HET) * 1.05
  step_y <- max(data$HET) * 0.05
  signif_data$y.position <- base_y + (1:nrow(signif_data) - 1) * step_y
  
  # 创建数值位置列
  signif_data <- signif_data %>%
    mutate(
      x1 = as.numeric(factor(group1, levels = sex_levels)),
      x2 = as.numeric(factor(group2, levels = sex_levels))
    )
}

# 创建箱线图
p16 <- ggplot(data, aes(x = Sex, y = HET)) +
  geom_boxplot(
    aes(fill = Sex),
    alpha = 0.8, 
    outlier.shape = 16, 
    outlier.size = 1.5,
    width = 0.6
  ) +
  scale_y_continuous(
    limits = c(4000000, 8500000),
    breaks = c(4000000, 4500000, 5000000, 5500000, 6000000, 6500000, 7000000, 7500000, 8000000, 8500000),
    labels = c("4M", "4.5M", "5M", "5.5M", "6M", "6.5M", "7M", "7.5M", "8M", "8.5M")
  ) + 
  scale_fill_manual(values = c("#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3")) +
  labs(
    title = "MAF0.05_Sex",
    x = "HET",
    y = "SNPs Count"
  ) +
  scale_x_discrete(labels = c("F" = "Female", "M" = "Male")) + 
  theme_classic(base_size = 12) +
  theme(
    axis.title = element_text(face = "bold", size = 10),
    axis.text = element_text(size = 8),
    legend.position = "none",
    plot.title = element_text(hjust = 0.5, vjust = -5),
  ) 

# 添加显著性标记
if(nrow(signif_data) > 0) {
  p16 <- p16 + 
    # 水平连接线
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x2, y = y.position, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 垂直线端
    geom_segment(
      data = signif_data,
      aes(x = x1, xend = x1, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    geom_segment(
      data = signif_data,
      aes(x = x2, xend = x2, y = y.position - step_y * 0.1, yend = y.position),
      linewidth = 0.5,
      color = "black"
    ) +
    # 星号标签
    geom_text(
      data = signif_data,
      aes(x = (x1 + x2)/2, y = y.position + step_y * 0.01, label = label),
      size = 5,
      vjust = 0
    ) 
}

# 保存图标到原文件目录
ggsave("SNP_MAF0.05_HET_Sexs_comparison_with_significance.png", p1, width = 6, height = 4, dpi = 300)
ggsave("SNP_MAF0.05_HET_Sexs_comparison_with_significance.pdf", p1, width = 6, height = 4)


Fp <- plot_grid(
  p1, p2, p3, p4,
  p5, p6, p7, p8,
  p9, p10, p11, p12,
  p13, p14, p15, p16,
  ncol = 4,
  labels = c("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"),
  label_size = 14,
  label_fontface = "bold"
)

ggsave("FigureS6_SNP.png", Fp, width = 24, height = 16, dpi = 300)
ggsave("FigureS6_SNP.pdf", Fp, width = 24, height = 16)
