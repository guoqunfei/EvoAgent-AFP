# 清空环境变量
rm(list = ls())
setwd("~/Desktop/BGI/biodiversity/projects/Cyclone/Pig/analysis/Summary20260323/Figures/Figure1/PanelF")

# 加载必要的包
library(ggplot2)
library(dplyr)
library(tidyr)
library(scales)
library(gridExtra)
library(grid)


# 读取数据
data <- read.table("SnpEff.5000bp.SV_GenomeFeature.classify.uniq.out.summary.graph.txt", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# 查看数据结构以确认列名
if(ncol(data) >= 4) {colnames(data) <- c("Type", "Num", "MAF_low", "MAF_middle", "MAF_high")}

# 处理可能的NA值
data <- data %>% mutate(Num = as.numeric(Num), MAF_low = as.numeric(MAF_low), MAF_middle = as.numeric(MAF_middle), MAF_high = as.numeric(MAF_high)
  ) %>%
  # 如果有NA值，用0替换
  mutate(Num = ifelse(is.na(Num), 0, Num), MAF_low = ifelse(is.na(MAF_low), 0, MAF_low), MAF_middle = ifelse(is.na(MAF_middle), 0, MAF_middle), MAF_high = ifelse(is.na(MAF_high), 0, MAF_high))

# 调整类别名称使其更易读
data$Type <- gsub("-", " ", data$Type)

# 设置类别顺序
type_order <- c("CDS altering", "UTR", "Splicing", "NC transcript", "Intron", "Intergenic")
data$Type <- factor(data$Type, levels = type_order)

# 反转类别顺序以匹配coord_flip后的显示
data$Type <- factor(data$Type, levels = rev(type_order))

# 分析数据范围
min_value <- min(data$Num)
max_value <- max(data$Num)

# 创建两个图，去掉标题但保留Y轴标签

# 图1：总数条形图（放在左边）- 使用对数坐标
p_left_total <- ggplot(data, aes(x = Type, y = Num)) +
  geom_bar(stat = "identity", fill = "#2E86AB", alpha = 0.8, width = 0.7) +
  # 去掉标题但保留Y轴标签
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 左边图：显示Y轴标签（类别名称）
    axis.text.y = element_text(
      size = 10, 
      #face = "bold",
      color = "black",
      hjust = 0.5,
      margin = margin(r = 5)  # 右侧边距
    ),
    axis.ticks.y = element_line(color = "black", size = 0.5),
    axis.ticks.x = element_line(color = "black", size = 0.5), 
    # 显示X轴标签（数值）
    axis.text.x = element_text(size = 9),
    # 调整边距
    plot.margin = margin(l = 15, r = 5, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major.x = element_line(color = "gray90", size = 0.3),
    panel.grid.major.y = element_blank(), 
    #panel.grid.major = element_blank(),
    #panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  # 修改数值标签：字体缩小，放在条形图内部顶部
  geom_text(
    aes(label = format(Num, big.mark = ",", scientific = FALSE)), 
    hjust = 0,  # 居中
    vjust = -0, # 放在条形图顶部上方一点
    size = 3,   # 缩小字体
    #fontface = "bold",
    position = position_dodge(width = 0.9)
  ) +
  # 使用对数坐标轴，修复标签函数
  scale_y_log10(
    # 修复的标签函数，处理NA值
    labels = function(x) {
      sapply(x, function(val) {
        # 检查是否为NA或NULL
        if (is.na(val) || is.null(val)) {
          return("")
        }
        # 处理0值
        if (val == 0) {
          return("0")
        }
        # 处理小于1000的值
        if (val < 1000) {
          return(as.character(round(val)))
        }
        # 处理1000到1M之间的值
        if (val < 1e6) {
          return(paste0(round(val/1e3, 1), "K"))
        }
        # 处理大于等于1M的值
        return(paste0(round(val/1e6, 1), "M"))
      })
    },
    expand = expansion(mult = c(0, 0.3)),  # 增加顶部空间给标签
    # 设置合适的刻度
    breaks = 10^(0:ceiling(log10(max_value))),  # 动态生成刻度
    minor_breaks = NULL
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev) +
  # 使用coord_cartesian来限制显示范围
  coord_flip(ylim = c(1000, max_value * 1.1))

# 图2：MAF比例堆叠图（放在右边）
# 转换为长格式
data_long <- data %>%
  select(Type, MAF_low, MAF_middle, MAF_high) %>%
  pivot_longer(
    cols = c(MAF_low, MAF_middle, MAF_high), 
    names_to = "MAF_Category", 
    values_to = "Proportion"
  ) %>%
  mutate(
    MAF_Category = case_when(
      MAF_Category == "MAF_low"    ~ "MAF<1%",
      MAF_Category == "MAF_middle" ~ "1%<=MAF<5%",
      MAF_Category == "MAF_high"   ~ "MAF>=5%",
      TRUE                         ~ MAF_Category
    ),
    MAF_Category = factor(MAF_Category, levels = c("MAF<1%", "1%<=MAF<5%", "MAF>=5%"))
  )

data_long$Type <- factor(data_long$Type, levels = rev(type_order))

p_right_proportion <- ggplot(
  data_long, 
  aes(x = Type, y = Proportion, fill = MAF_Category)
) +
  geom_bar(stat = "identity", position = "fill", width = 0.7) +
  scale_fill_manual(
    values = c("MAF<1%" = "#1f77b4", "1%<=MAF<5%" = "#ff7f0e", "MAF>=5%" = "#AD1414"),
    name = NULL  # 去掉图例标题
  ) +
  # 去掉所有标题
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 右边图：隐藏Y轴标签（因为左边图已经显示了）
    axis.text.y = element_blank(),
    #axis.ticks.y = element_blank(),
    # 显示X轴标签（百分比）
    
    axis.text.x = element_text(size = 9),
    # 图例放在右边
    legend.position = "right",
    legend.justification = "center",
    legend.box.just = "left",
    legend.margin = margin(l = 10, r = 5),
    legend.text = element_text(size = 10),
    legend.key.size = unit(1, "lines"),
    # 调整边距 - 与左图保持一致
    plot.margin = margin(l = 5, r = 15, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  scale_y_continuous(
    labels = percent_format(), 
    expand = expansion(mult = c(0, 0))
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev)


# 使用grid.arrange进行简单两列布局
p_SV <- grid.arrange(
  p_left_total,  # 左图：总数条形图（对数坐标，数值标签在内部）
  p_right_proportion,  # 右图：MAF比例图（图例在右边，无数值标签）
  ncol = 2,
  # 调整宽度比例：左图稍宽（因为有Y轴标签），右图稍窄（图例在右边）
  widths = c(1.1, 0.9),
  # 关键：设置相同的行高，确保两个图高度完全一致
  heights = unit(1, "null"),
  # 对齐设置
  padding = unit(0, "cm"),
  top = textGrob("SVs Distribution with Gene locus and MAF", gp = gpar(fontsize = 16, fontface = "bold"), hjust = 0.5, x = 0.5, vjust = 0.5)
)

# 保存图片
ggsave("SV_gene_MAF.png", p_SV, width = 14, height = 8, dpi = 300)
ggsave("SV_gene_MAF.pdf", p_SV, width = 14, height = 8)


# 读取数据
data <- read.table("SnpEff.5000bp.SV-DEL_GenomeFeature.classify.uniq.out.summary.graph.txt", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# 查看数据结构以确认列名
if(ncol(data) >= 4) {colnames(data) <- c("Type", "Num", "MAF_low", "MAF_middle", "MAF_high")}

# 处理可能的NA值
data <- data %>% mutate(Num = as.numeric(Num), MAF_low = as.numeric(MAF_low), MAF_middle = as.numeric(MAF_middle), MAF_high = as.numeric(MAF_high)
) %>%
  # 如果有NA值，用0替换
  mutate(Num = ifelse(is.na(Num), 0, Num), MAF_low = ifelse(is.na(MAF_low), 0, MAF_low), MAF_middle = ifelse(is.na(MAF_middle), 0, MAF_middle), MAF_high = ifelse(is.na(MAF_high), 0, MAF_high))

# 调整类别名称使其更易读
data$Type <- gsub("-", " ", data$Type)

# 设置类别顺序
type_order <- c("CDS altering", "UTR", "Splicing", "NC transcript", "Intron", "Intergenic")
data$Type <- factor(data$Type, levels = type_order)

# 反转类别顺序以匹配coord_flip后的显示
data$Type <- factor(data$Type, levels = rev(type_order))

# 分析数据范围
min_value <- min(data$Num)
max_value <- max(data$Num)

# 创建两个图，去掉标题但保留Y轴标签

# 图1：总数条形图（放在左边）- 使用对数坐标
p_left_total <- ggplot(data, aes(x = Type, y = Num)) +
  geom_bar(stat = "identity", fill = "#2E86AB", alpha = 0.8, width = 0.7) +
  # 去掉标题但保留Y轴标签
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 左边图：显示Y轴标签（类别名称）
    axis.text.y = element_text(
      size = 10, 
      #face = "bold",
      color = "black",
      hjust = 0.5,
      margin = margin(r = 5)  # 右侧边距
    ),
    axis.ticks.y = element_line(color = "black", size = 0.5),
    axis.ticks.x = element_line(color = "black", size = 0.5), 
    # 显示X轴标签（数值）
    axis.text.x = element_text(size = 9),
    # 调整边距
    plot.margin = margin(l = 15, r = 5, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major.x = element_line(color = "gray90", size = 0.3),
    panel.grid.major.y = element_blank(), 
    #panel.grid.major = element_blank(),
    #panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  # 修改数值标签：字体缩小，放在条形图内部顶部
  geom_text(
    aes(label = format(Num, big.mark = ",", scientific = FALSE)), 
    hjust = 0,  # 居中
    vjust = -0, # 放在条形图顶部上方一点
    size = 3,   # 缩小字体
    #fontface = "bold",
    position = position_dodge(width = 0.9)
  ) +
  # 使用对数坐标轴，修复标签函数
  scale_y_log10(
    # 修复的标签函数，处理NA值
    labels = function(x) {
      sapply(x, function(val) {
        # 检查是否为NA或NULL
        if (is.na(val) || is.null(val)) {
          return("")
        }
        # 处理0值
        if (val == 0) {
          return("0")
        }
        # 处理小于1000的值
        if (val < 1000) {
          return(as.character(round(val)))
        }
        # 处理1000到1M之间的值
        if (val < 1e6) {
          return(paste0(round(val/1e3, 1), "K"))
        }
        # 处理大于等于1M的值
        return(paste0(round(val/1e6, 1), "M"))
      })
    },
    expand = expansion(mult = c(0, 0.3)),  # 增加顶部空间给标签
    # 设置合适的刻度
    breaks = 10^(0:ceiling(log10(max_value))),  # 动态生成刻度
    minor_breaks = NULL
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev) +
  # 使用coord_cartesian来限制显示范围
  coord_flip(ylim = c(1000, max_value * 1.1))

# 图2：MAF比例堆叠图（放在右边）
# 转换为长格式
data_long <- data %>%
  select(Type, MAF_low, MAF_middle, MAF_high) %>%
  pivot_longer(
    cols = c(MAF_low, MAF_middle, MAF_high), 
    names_to = "MAF_Category", 
    values_to = "Proportion"
  ) %>%
  mutate(
    MAF_Category = case_when(
      MAF_Category == "MAF_low"    ~ "MAF<1%",
      MAF_Category == "MAF_middle" ~ "1%<=MAF<5%",
      MAF_Category == "MAF_high"   ~ "MAF>=5%",
      TRUE                         ~ MAF_Category
    ),
    MAF_Category = factor(MAF_Category, levels = c("MAF<1%", "1%<=MAF<5%", "MAF>=5%"))
  )

data_long$Type <- factor(data_long$Type, levels = rev(type_order))

p_right_proportion <- ggplot(
  data_long, 
  aes(x = Type, y = Proportion, fill = MAF_Category)
) +
  geom_bar(stat = "identity", position = "fill", width = 0.7) +
  scale_fill_manual(
    values = c("MAF<1%" = "#1f77b4", "1%<=MAF<5%" = "#ff7f0e", "MAF>=5%" = "#AD1414"),
    name = NULL  # 去掉图例标题
  ) +
  # 去掉所有标题
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 右边图：隐藏Y轴标签（因为左边图已经显示了）
    axis.text.y = element_blank(),
    #axis.ticks.y = element_blank(),
    # 显示X轴标签（百分比）
    
    axis.text.x = element_text(size = 9),
    # 图例放在右边
    legend.position = "right",
    legend.justification = "center",
    legend.box.just = "left",
    legend.margin = margin(l = 10, r = 5),
    legend.text = element_text(size = 10),
    legend.key.size = unit(1, "lines"),
    # 调整边距 - 与左图保持一致
    plot.margin = margin(l = 5, r = 15, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  scale_y_continuous(
    labels = percent_format(), 
    expand = expansion(mult = c(0, 0))
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev)


# 使用grid.arrange进行简单两列布局
p_SV_DEL <- grid.arrange(
  p_left_total,  # 左图：总数条形图（对数坐标，数值标签在内部）
  p_right_proportion,  # 右图：MAF比例图（图例在右边，无数值标签）
  ncol = 2,
  # 调整宽度比例：左图稍宽（因为有Y轴标签），右图稍窄（图例在右边）
  widths = c(1.1, 0.9),
  # 关键：设置相同的行高，确保两个图高度完全一致
  heights = unit(1, "null"),
  # 对齐设置
  padding = unit(0, "cm"),
  top = textGrob("SV-DEL Distribution with Gene locus and MAF", gp = gpar(fontsize = 16, fontface = "bold"), hjust = 0.5, x = 0.5, vjust = 0.5)
)

# 保存图片
ggsave("SV-DEL_gene_MAF.png", p_SV_DEL, width = 14, height = 8, dpi = 300)
ggsave("SV-DEL_gene_MAF.pdf", p_SV_DEL, width = 14, height = 8)


# 读取数据
data <- read.table("SnpEff.5000bp.SV-DUP_GenomeFeature.classify.uniq.out.summary.graph.txt", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# 查看数据结构以确认列名
if(ncol(data) >= 4) {colnames(data) <- c("Type", "Num", "MAF_low", "MAF_middle", "MAF_high")}

# 处理可能的NA值
data <- data %>% mutate(Num = as.numeric(Num), MAF_low = as.numeric(MAF_low), MAF_middle = as.numeric(MAF_middle), MAF_high = as.numeric(MAF_high)
) %>%
  # 如果有NA值，用0替换
  mutate(Num = ifelse(is.na(Num), 0, Num), MAF_low = ifelse(is.na(MAF_low), 0, MAF_low), MAF_middle = ifelse(is.na(MAF_middle), 0, MAF_middle), MAF_high = ifelse(is.na(MAF_high), 0, MAF_high))

# 调整类别名称使其更易读
data$Type <- gsub("-", " ", data$Type)

# 设置类别顺序
type_order <- c("CDS altering", "UTR", "Splicing", "NC transcript", "Intron", "Intergenic")
data$Type <- factor(data$Type, levels = type_order)

# 反转类别顺序以匹配coord_flip后的显示
data$Type <- factor(data$Type, levels = rev(type_order))

# 分析数据范围
min_value <- min(data$Num)
max_value <- max(data$Num)

# 创建两个图，去掉标题但保留Y轴标签

# 图1：总数条形图（放在左边）- 使用对数坐标
p_left_total <- ggplot(data, aes(x = Type, y = Num)) +
  geom_bar(stat = "identity", fill = "#2E86AB", alpha = 0.8, width = 0.7) +
  # 去掉标题但保留Y轴标签
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 左边图：显示Y轴标签（类别名称）
    axis.text.y = element_text(
      size = 10, 
      #face = "bold",
      color = "black",
      hjust = 0.5,
      margin = margin(r = 5)  # 右侧边距
    ),
    axis.ticks.y = element_line(color = "black", size = 0.5),
    axis.ticks.x = element_line(color = "black", size = 0.5), 
    # 显示X轴标签（数值）
    axis.text.x = element_text(size = 9),
    # 调整边距
    plot.margin = margin(l = 15, r = 5, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major.x = element_line(color = "gray90", size = 0.3),
    panel.grid.major.y = element_blank(), 
    #panel.grid.major = element_blank(),
    #panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  # 修改数值标签：字体缩小，放在条形图内部顶部
  geom_text(
    aes(label = format(Num, big.mark = ",", scientific = FALSE)), 
    hjust = 0,  # 居中
    vjust = -0, # 放在条形图顶部上方一点
    size = 3,   # 缩小字体
    #fontface = "bold",
    position = position_dodge(width = 0.9)
  ) +
  # 使用对数坐标轴，修复标签函数
  scale_y_log10(
    # 修复的标签函数，处理NA值
    labels = function(x) {
      sapply(x, function(val) {
        # 检查是否为NA或NULL
        if (is.na(val) || is.null(val)) {
          return("")
        }
        # 处理0值
        if (val == 0) {
          return("0")
        }
        # 处理小于1000的值
        if (val < 1000) {
          return(as.character(round(val)))
        }
        # 处理1000到1M之间的值
        if (val < 1e6) {
          return(paste0(round(val/1e3, 1), "K"))
        }
        # 处理大于等于1M的值
        return(paste0(round(val/1e6, 1), "M"))
      })
    },
    expand = expansion(mult = c(0, 0.3)),  # 增加顶部空间给标签
    # 设置合适的刻度
    breaks = 10^(0:ceiling(log10(max_value))),  # 动态生成刻度
    minor_breaks = NULL
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev) +
  # 使用coord_cartesian来限制显示范围
  coord_flip(ylim = c(1, max_value * 1.1))

# 图2：MAF比例堆叠图（放在右边）
# 转换为长格式
data_long <- data %>%
  select(Type, MAF_low, MAF_middle, MAF_high) %>%
  pivot_longer(
    cols = c(MAF_low, MAF_middle, MAF_high), 
    names_to = "MAF_Category", 
    values_to = "Proportion"
  ) %>%
  mutate(
    MAF_Category = case_when(
      MAF_Category == "MAF_low"    ~ "MAF<1%",
      MAF_Category == "MAF_middle" ~ "1%<=MAF<5%",
      MAF_Category == "MAF_high"   ~ "MAF>=5%",
      TRUE                         ~ MAF_Category
    ),
    MAF_Category = factor(MAF_Category, levels = c("MAF<1%", "1%<=MAF<5%", "MAF>=5%"))
  )

data_long$Type <- factor(data_long$Type, levels = rev(type_order))

p_right_proportion <- ggplot(
  data_long, 
  aes(x = Type, y = Proportion, fill = MAF_Category)
) +
  geom_bar(stat = "identity", position = "fill", width = 0.7) +
  scale_fill_manual(
    values = c("MAF<1%" = "#1f77b4", "1%<=MAF<5%" = "#ff7f0e", "MAF>=5%" = "#AD1414"),
    name = NULL  # 去掉图例标题
  ) +
  # 去掉所有标题
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 右边图：隐藏Y轴标签（因为左边图已经显示了）
    axis.text.y = element_blank(),
    #axis.ticks.y = element_blank(),
    # 显示X轴标签（百分比）
    
    axis.text.x = element_text(size = 9),
    # 图例放在右边
    legend.position = "right",
    legend.justification = "center",
    legend.box.just = "left",
    legend.margin = margin(l = 10, r = 5),
    legend.text = element_text(size = 10),
    legend.key.size = unit(1, "lines"),
    # 调整边距 - 与左图保持一致
    plot.margin = margin(l = 5, r = 15, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  scale_y_continuous(
    labels = percent_format(), 
    expand = expansion(mult = c(0, 0))
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev)


# 使用grid.arrange进行简单两列布局
p_SV_DUP <- grid.arrange(
  p_left_total,  # 左图：总数条形图（对数坐标，数值标签在内部）
  p_right_proportion,  # 右图：MAF比例图（图例在右边，无数值标签）
  ncol = 2,
  # 调整宽度比例：左图稍宽（因为有Y轴标签），右图稍窄（图例在右边）
  widths = c(1.1, 0.9),
  # 关键：设置相同的行高，确保两个图高度完全一致
  heights = unit(1, "null"),
  # 对齐设置
  padding = unit(0, "cm"),
  top = textGrob("SV-DUP Distribution with Gene locus and MAF", gp = gpar(fontsize = 16, fontface = "bold"), hjust = 0.5, x = 0.5, vjust = 0.5)
)

# 保存图片
ggsave("SV-DUP_gene_MAF.png", p_SV_DUP, width = 14, height = 8, dpi = 300)
ggsave("SV-DUP_gene_MAF.pdf", p_SV_DUP, width = 14, height = 8)


# 读取数据
data <- read.table("SnpEff.5000bp.SV-INS_GenomeFeature.classify.uniq.out.summary.graph.txt", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# 查看数据结构以确认列名
if(ncol(data) >= 4) {colnames(data) <- c("Type", "Num", "MAF_low", "MAF_middle", "MAF_high")}

# 处理可能的NA值
data <- data %>% mutate(Num = as.numeric(Num), MAF_low = as.numeric(MAF_low), MAF_middle = as.numeric(MAF_middle), MAF_high = as.numeric(MAF_high)
) %>%
  # 如果有NA值，用0替换
  mutate(Num = ifelse(is.na(Num), 0, Num), MAF_low = ifelse(is.na(MAF_low), 0, MAF_low), MAF_middle = ifelse(is.na(MAF_middle), 0, MAF_middle), MAF_high = ifelse(is.na(MAF_high), 0, MAF_high))

# 调整类别名称使其更易读
data$Type <- gsub("-", " ", data$Type)

# 设置类别顺序
type_order <- c("CDS altering", "UTR", "Splicing", "NC transcript", "Intron", "Intergenic")
data$Type <- factor(data$Type, levels = type_order)

# 反转类别顺序以匹配coord_flip后的显示
data$Type <- factor(data$Type, levels = rev(type_order))

# 分析数据范围
min_value <- min(data$Num)
max_value <- max(data$Num)

# 创建两个图，去掉标题但保留Y轴标签

# 图1：总数条形图（放在左边）- 使用对数坐标
p_left_total <- ggplot(data, aes(x = Type, y = Num)) +
  geom_bar(stat = "identity", fill = "#2E86AB", alpha = 0.8, width = 0.7) +
  # 去掉标题但保留Y轴标签
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 左边图：显示Y轴标签（类别名称）
    axis.text.y = element_text(
      size = 10, 
      #face = "bold",
      color = "black",
      hjust = 0.5,
      margin = margin(r = 5)  # 右侧边距
    ),
    axis.ticks.y = element_line(color = "black", size = 0.5),
    axis.ticks.x = element_line(color = "black", size = 0.5), 
    # 显示X轴标签（数值）
    axis.text.x = element_text(size = 9),
    # 调整边距
    plot.margin = margin(l = 15, r = 5, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major.x = element_line(color = "gray90", size = 0.3),
    panel.grid.major.y = element_blank(), 
    #panel.grid.major = element_blank(),
    #panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  # 修改数值标签：字体缩小，放在条形图内部顶部
  geom_text(
    aes(label = format(Num, big.mark = ",", scientific = FALSE)), 
    hjust = 0,  # 居中
    vjust = -0, # 放在条形图顶部上方一点
    size = 3,   # 缩小字体
    #fontface = "bold",
    position = position_dodge(width = 0.9)
  ) +
  # 使用对数坐标轴，修复标签函数
  scale_y_log10(
    # 修复的标签函数，处理NA值
    labels = function(x) {
      sapply(x, function(val) {
        # 检查是否为NA或NULL
        if (is.na(val) || is.null(val)) {
          return("")
        }
        # 处理0值
        if (val == 0) {
          return("0")
        }
        # 处理小于1000的值
        if (val < 1000) {
          return(as.character(round(val)))
        }
        # 处理1000到1M之间的值
        if (val < 1e6) {
          return(paste0(round(val/1e3, 1), "K"))
        }
        # 处理大于等于1M的值
        return(paste0(round(val/1e6, 1), "M"))
      })
    },
    expand = expansion(mult = c(0, 0.3)),  # 增加顶部空间给标签
    # 设置合适的刻度
    breaks = 10^(0:ceiling(log10(max_value))),  # 动态生成刻度
    minor_breaks = NULL
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev) +
  # 使用coord_cartesian来限制显示范围
  coord_flip(ylim = c(1000, max_value * 1.1))

# 图2：MAF比例堆叠图（放在右边）
# 转换为长格式
data_long <- data %>%
  select(Type, MAF_low, MAF_middle, MAF_high) %>%
  pivot_longer(
    cols = c(MAF_low, MAF_middle, MAF_high), 
    names_to = "MAF_Category", 
    values_to = "Proportion"
  ) %>%
  mutate(
    MAF_Category = case_when(
      MAF_Category == "MAF_low"    ~ "MAF<1%",
      MAF_Category == "MAF_middle" ~ "1%<=MAF<5%",
      MAF_Category == "MAF_high"   ~ "MAF>=5%",
      TRUE                         ~ MAF_Category
    ),
    MAF_Category = factor(MAF_Category, levels = c("MAF<1%", "1%<=MAF<5%", "MAF>=5%"))
  )

data_long$Type <- factor(data_long$Type, levels = rev(type_order))

p_right_proportion <- ggplot(
  data_long, 
  aes(x = Type, y = Proportion, fill = MAF_Category)
) +
  geom_bar(stat = "identity", position = "fill", width = 0.7) +
  scale_fill_manual(
    values = c("MAF<1%" = "#1f77b4", "1%<=MAF<5%" = "#ff7f0e", "MAF>=5%" = "#AD1414"),
    name = NULL  # 去掉图例标题
  ) +
  # 去掉所有标题
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 右边图：隐藏Y轴标签（因为左边图已经显示了）
    axis.text.y = element_blank(),
    #axis.ticks.y = element_blank(),
    # 显示X轴标签（百分比）
    
    axis.text.x = element_text(size = 9),
    # 图例放在右边
    legend.position = "right",
    legend.justification = "center",
    legend.box.just = "left",
    legend.margin = margin(l = 10, r = 5),
    legend.text = element_text(size = 10),
    legend.key.size = unit(1, "lines"),
    # 调整边距 - 与左图保持一致
    plot.margin = margin(l = 5, r = 15, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  scale_y_continuous(
    labels = percent_format(), 
    expand = expansion(mult = c(0, 0))
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev)


# 使用grid.arrange进行简单两列布局
p_SV_INS <- grid.arrange(
  p_left_total,  # 左图：总数条形图（对数坐标，数值标签在内部）
  p_right_proportion,  # 右图：MAF比例图（图例在右边，无数值标签）
  ncol = 2,
  # 调整宽度比例：左图稍宽（因为有Y轴标签），右图稍窄（图例在右边）
  widths = c(1.1, 0.9),
  # 关键：设置相同的行高，确保两个图高度完全一致
  heights = unit(1, "null"),
  # 对齐设置
  padding = unit(0, "cm"),
  top = textGrob("SV-INS Distribution with Gene locus and MAF", gp = gpar(fontsize = 16, fontface = "bold"), hjust = 0.5, x = 0.5, vjust = 0.5)
)

# 保存图片
ggsave("SV_INS_gene_MAF.png", p_SV_INS, width = 14, height = 8, dpi = 300)
ggsave("SV_INS_gene_MAF.pdf", p_SV_INS, width = 14, height = 8)


# 读取数据
data <- read.table("SnpEff.5000bp.SV-INV_GenomeFeature.classify.uniq.out.summary.graph.txt", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# 查看数据结构以确认列名
if(ncol(data) >= 4) {colnames(data) <- c("Type", "Num", "MAF_low", "MAF_middle", "MAF_high")}

# 处理可能的NA值
data <- data %>% mutate(Num = as.numeric(Num), MAF_low = as.numeric(MAF_low), MAF_middle = as.numeric(MAF_middle), MAF_high = as.numeric(MAF_high)
) %>%
  # 如果有NA值，用0替换
  mutate(Num = ifelse(is.na(Num), 0, Num), MAF_low = ifelse(is.na(MAF_low), 0, MAF_low), MAF_middle = ifelse(is.na(MAF_middle), 0, MAF_middle), MAF_high = ifelse(is.na(MAF_high), 0, MAF_high))

# 调整类别名称使其更易读
data$Type <- gsub("-", " ", data$Type)

# 设置类别顺序
type_order <- c("CDS altering", "UTR", "Splicing", "NC transcript", "Intron", "Intergenic")
data$Type <- factor(data$Type, levels = type_order)

# 反转类别顺序以匹配coord_flip后的显示
data$Type <- factor(data$Type, levels = rev(type_order))

# 分析数据范围
min_value <- min(data$Num)
max_value <- max(data$Num)

# 创建两个图，去掉标题但保留Y轴标签

# 图1：总数条形图（放在左边）- 使用对数坐标
p_left_total <- ggplot(data, aes(x = Type, y = Num)) +
  geom_bar(stat = "identity", fill = "#2E86AB", alpha = 0.8, width = 0.7) +
  # 去掉标题但保留Y轴标签
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 左边图：显示Y轴标签（类别名称）
    axis.text.y = element_text(
      size = 10, 
      #face = "bold",
      color = "black",
      hjust = 0.5,
      margin = margin(r = 5)  # 右侧边距
    ),
    axis.ticks.y = element_line(color = "black", size = 0.5),
    axis.ticks.x = element_line(color = "black", size = 0.5), 
    # 显示X轴标签（数值）
    axis.text.x = element_text(size = 9),
    # 调整边距
    plot.margin = margin(l = 15, r = 5, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major.x = element_line(color = "gray90", size = 0.3),
    panel.grid.major.y = element_blank(), 
    #panel.grid.major = element_blank(),
    #panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  # 修改数值标签：字体缩小，放在条形图内部顶部
  geom_text(
    aes(label = format(Num, big.mark = ",", scientific = FALSE)), 
    hjust = 0,  # 居中
    vjust = -0, # 放在条形图顶部上方一点
    size = 3,   # 缩小字体
    #fontface = "bold",
    position = position_dodge(width = 0.9)
  ) +
  # 使用对数坐标轴，修复标签函数
  scale_y_log10(
    # 修复的标签函数，处理NA值
    labels = function(x) {
      sapply(x, function(val) {
        # 检查是否为NA或NULL
        if (is.na(val) || is.null(val)) {
          return("")
        }
        # 处理0值
        if (val == 0) {
          return("0")
        }
        # 处理小于1000的值
        if (val < 1000) {
          return(as.character(round(val)))
        }
        # 处理1000到1M之间的值
        if (val < 1e6) {
          return(paste0(round(val/1e3, 1), "K"))
        }
        # 处理大于等于1M的值
        return(paste0(round(val/1e6, 1), "M"))
      })
    },
    expand = expansion(mult = c(0, 0.3)),  # 增加顶部空间给标签
    # 设置合适的刻度
    breaks = 10^(0:ceiling(log10(max_value))),  # 动态生成刻度
    minor_breaks = NULL
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev) +
  # 使用coord_cartesian来限制显示范围
  coord_flip(ylim = c(1, max_value * 1.1))

# 图2：MAF比例堆叠图（放在右边）
# 转换为长格式
data_long <- data %>%
  select(Type, MAF_low, MAF_middle, MAF_high) %>%
  pivot_longer(
    cols = c(MAF_low, MAF_middle, MAF_high), 
    names_to = "MAF_Category", 
    values_to = "Proportion"
  ) %>%
  mutate(
    MAF_Category = case_when(
      MAF_Category == "MAF_low"    ~ "MAF<1%",
      MAF_Category == "MAF_middle" ~ "1%<=MAF<5%",
      MAF_Category == "MAF_high"   ~ "MAF>=5%",
      TRUE                         ~ MAF_Category
    ),
    MAF_Category = factor(MAF_Category, levels = c("MAF<1%", "1%<=MAF<5%", "MAF>=5%"))
  )

data_long$Type <- factor(data_long$Type, levels = rev(type_order))

p_right_proportion <- ggplot(
  data_long, 
  aes(x = Type, y = Proportion, fill = MAF_Category)
) +
  geom_bar(stat = "identity", position = "fill", width = 0.7) +
  scale_fill_manual(
    values = c("MAF<1%" = "#1f77b4", "1%<=MAF<5%" = "#ff7f0e", "MAF>=5%" = "#AD1414"),
    name = NULL  # 去掉图例标题
  ) +
  # 去掉所有标题
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 右边图：隐藏Y轴标签（因为左边图已经显示了）
    axis.text.y = element_blank(),
    #axis.ticks.y = element_blank(),
    # 显示X轴标签（百分比）
    
    axis.text.x = element_text(size = 9),
    # 图例放在右边
    legend.position = "right",
    legend.justification = "center",
    legend.box.just = "left",
    legend.margin = margin(l = 10, r = 5),
    legend.text = element_text(size = 10),
    legend.key.size = unit(1, "lines"),
    # 调整边距 - 与左图保持一致
    plot.margin = margin(l = 5, r = 15, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  scale_y_continuous(
    labels = percent_format(), 
    expand = expansion(mult = c(0, 0))
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev)


# 使用grid.arrange进行简单两列布局
p_SV_INV <- grid.arrange(
  p_left_total,  # 左图：总数条形图（对数坐标，数值标签在内部）
  p_right_proportion,  # 右图：MAF比例图（图例在右边，无数值标签）
  ncol = 2,
  # 调整宽度比例：左图稍宽（因为有Y轴标签），右图稍窄（图例在右边）
  widths = c(1.1, 0.9),
  # 关键：设置相同的行高，确保两个图高度完全一致
  heights = unit(1, "null"),
  # 对齐设置
  padding = unit(0, "cm"),
  top = textGrob("SV-INV Distribution with Gene locus and MAF", gp = gpar(fontsize = 16, fontface = "bold"), hjust = 0.5, x = 0.5, vjust = 0.5)
)

# 保存图片
ggsave("SV-INV_gene_MAF.png", p_SV_INV, width = 14, height = 8, dpi = 300)
ggsave("SV-INV_gene_MAF.pdf", p_SV_INV, width = 14, height = 8)


# 读取数据
data <- read.table("SnpEff.5000bp.INDEL_GenomeFeature.classify.uniq.out.summary.graph.txt", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# 查看数据结构以确认列名
if(ncol(data) >= 4) {colnames(data) <- c("Type", "Num", "MAF_low", "MAF_middle", "MAF_high")}

# 处理可能的NA值
data <- data %>% mutate(Num = as.numeric(Num), MAF_low = as.numeric(MAF_low), MAF_middle = as.numeric(MAF_middle), MAF_high = as.numeric(MAF_high)
) %>%
  # 如果有NA值，用0替换
  mutate(Num = ifelse(is.na(Num), 0, Num), MAF_low = ifelse(is.na(MAF_low), 0, MAF_low), MAF_middle = ifelse(is.na(MAF_middle), 0, MAF_middle), MAF_high = ifelse(is.na(MAF_high), 0, MAF_high))

# 调整类别名称使其更易读
data$Type <- gsub("-", " ", data$Type)

# 设置类别顺序
type_order <- c("CDS altering", "UTR", "Splicing", "NC transcript", "Intron", "Intergenic")
data$Type <- factor(data$Type, levels = type_order)

# 反转类别顺序以匹配coord_flip后的显示
data$Type <- factor(data$Type, levels = rev(type_order))

# 分析数据范围
min_value <- min(data$Num)
max_value <- max(data$Num)

# 创建两个图，去掉标题但保留Y轴标签

# 图1：总数条形图（放在左边）- 使用对数坐标
p_left_total <- ggplot(data, aes(x = Type, y = Num)) +
  geom_bar(stat = "identity", fill = "#2E86AB", alpha = 0.8, width = 0.7) +
  # 去掉标题但保留Y轴标签
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 左边图：显示Y轴标签（类别名称）
    axis.text.y = element_text(
      size = 10, 
      #face = "bold",
      color = "black",
      hjust = 0.5,
      margin = margin(r = 5)  # 右侧边距
    ),
    axis.ticks.y = element_line(color = "black", size = 0.5),
    axis.ticks.x = element_line(color = "black", size = 0.5), 
    # 显示X轴标签（数值）
    axis.text.x = element_text(size = 9),
    # 调整边距
    plot.margin = margin(l = 15, r = 5, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major.x = element_line(color = "gray90", size = 0.3),
    panel.grid.major.y = element_blank(), 
    #panel.grid.major = element_blank(),
    #panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  # 修改数值标签：字体缩小，放在条形图内部顶部
  geom_text(
    aes(label = format(Num, big.mark = ",", scientific = FALSE)), 
    hjust = 0,  # 居中
    vjust = -0, # 放在条形图顶部上方一点
    size = 3,   # 缩小字体
    #fontface = "bold",
    position = position_dodge(width = 0.9)
  ) +
  # 使用对数坐标轴，修复标签函数
  scale_y_log10(
    # 修复的标签函数，处理NA值
    labels = function(x) {
      sapply(x, function(val) {
        # 检查是否为NA或NULL
        if (is.na(val) || is.null(val)) {
          return("")
        }
        # 处理0值
        if (val == 0) {
          return("0")
        }
        # 处理小于1000的值
        if (val < 1000) {
          return(as.character(round(val)))
        }
        # 处理1000到1M之间的值
        if (val < 1e6) {
          return(paste0(round(val/1e3, 1), "K"))
        }
        # 处理大于等于1M的值
        return(paste0(round(val/1e6, 1), "M"))
      })
    },
    expand = expansion(mult = c(0, 0.3)),  # 增加顶部空间给标签
    # 设置合适的刻度
    breaks = 10^(0:ceiling(log10(max_value))),  # 动态生成刻度
    minor_breaks = NULL
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev) +
  # 使用coord_cartesian来限制显示范围
  coord_flip(ylim = c(1000, max_value * 1.1))

# 图2：MAF比例堆叠图（放在右边）
# 转换为长格式
data_long <- data %>%
  select(Type, MAF_low, MAF_middle, MAF_high) %>%
  pivot_longer(
    cols = c(MAF_low, MAF_middle, MAF_high), 
    names_to = "MAF_Category", 
    values_to = "Proportion"
  ) %>%
  mutate(
    MAF_Category = case_when(
      MAF_Category == "MAF_low"    ~ "MAF<1%",
      MAF_Category == "MAF_middle" ~ "1%<=MAF<5%",
      MAF_Category == "MAF_high"   ~ "MAF>=5%",
      TRUE                         ~ MAF_Category
    ),
    MAF_Category = factor(MAF_Category, levels = c("MAF<1%", "1%<=MAF<5%", "MAF>=5%"))
  )

data_long$Type <- factor(data_long$Type, levels = rev(type_order))

p_right_proportion <- ggplot(
  data_long, 
  aes(x = Type, y = Proportion, fill = MAF_Category)
) +
  geom_bar(stat = "identity", position = "fill", width = 0.7) +
  scale_fill_manual(
    values = c("MAF<1%" = "#1f77b4", "1%<=MAF<5%" = "#ff7f0e", "MAF>=5%" = "#AD1414"),
    name = NULL  # 去掉图例标题
  ) +
  # 去掉所有标题
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 右边图：隐藏Y轴标签（因为左边图已经显示了）
    axis.text.y = element_blank(),
    #axis.ticks.y = element_blank(),
    # 显示X轴标签（百分比）
    
    axis.text.x = element_text(size = 9),
    # 图例放在右边
    legend.position = "right",
    legend.justification = "center",
    legend.box.just = "left",
    legend.margin = margin(l = 10, r = 5),
    legend.text = element_text(size = 10),
    legend.key.size = unit(1, "lines"),
    # 调整边距 - 与左图保持一致
    plot.margin = margin(l = 5, r = 15, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  scale_y_continuous(
    labels = percent_format(), 
    expand = expansion(mult = c(0, 0))
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev)


# 使用grid.arrange进行简单两列布局
p_INDEL <- grid.arrange(
  p_left_total,  # 左图：总数条形图（对数坐标，数值标签在内部）
  p_right_proportion,  # 右图：MAF比例图（图例在右边，无数值标签）
  ncol = 2,
  # 调整宽度比例：左图稍宽（因为有Y轴标签），右图稍窄（图例在右边）
  widths = c(1.1, 0.9),
  # 关键：设置相同的行高，确保两个图高度完全一致
  heights = unit(1, "null"),
  # 对齐设置
  padding = unit(0, "cm"),
  top = textGrob("INDEL Distribution with Gene locus and MAF", gp = gpar(fontsize = 16, fontface = "bold"), hjust = 0.5, x = 0.5, vjust = 0.5)
)

# 保存图片
ggsave("INDEL_gene_MAF.png", p_INDEL, width = 14, height = 8, dpi = 300)
ggsave("INDEL_gene_MAF.pdf", p_INDEL, width = 14, height = 8)


# 读取数据
data <- read.table("SnpEff.5000bp.SNP_GenomeFeature.classify.uniq.out.summary.graph.txt", header = TRUE, sep = "\t", stringsAsFactors = FALSE)

# 查看数据结构以确认列名
if(ncol(data) >= 4) {colnames(data) <- c("Type", "Num", "MAF_low", "MAF_middle", "MAF_high")}

# 处理可能的NA值
data <- data %>% mutate(Num = as.numeric(Num), MAF_low = as.numeric(MAF_low), MAF_middle = as.numeric(MAF_middle), MAF_high = as.numeric(MAF_high)
) %>%
  # 如果有NA值，用0替换
  mutate(Num = ifelse(is.na(Num), 0, Num), MAF_low = ifelse(is.na(MAF_low), 0, MAF_low), MAF_middle = ifelse(is.na(MAF_middle), 0, MAF_middle), MAF_high = ifelse(is.na(MAF_high), 0, MAF_high))

# 调整类别名称使其更易读
data$Type <- gsub("-", " ", data$Type)

# 设置类别顺序
type_order <- c("CDS altering", "UTR", "Splicing", "NC transcript", "Intron", "Intergenic")
data$Type <- factor(data$Type, levels = type_order)

# 反转类别顺序以匹配coord_flip后的显示
data$Type <- factor(data$Type, levels = rev(type_order))

# 分析数据范围
min_value <- min(data$Num)
max_value <- max(data$Num)

# 创建两个图，去掉标题但保留Y轴标签

# 图1：总数条形图（放在左边）- 使用对数坐标
p_left_total <- ggplot(data, aes(x = Type, y = Num)) +
  geom_bar(stat = "identity", fill = "#2E86AB", alpha = 0.8, width = 0.7) +
  # 去掉标题但保留Y轴标签
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 左边图：显示Y轴标签（类别名称）
    axis.text.y = element_text(
      size = 10, 
      #face = "bold",
      color = "black",
      hjust = 0.5,
      margin = margin(r = 5)  # 右侧边距
    ),
    axis.ticks.y = element_line(color = "black", size = 0.5),
    axis.ticks.x = element_line(color = "black", size = 0.5), 
    # 显示X轴标签（数值）
    axis.text.x = element_text(size = 9),
    # 调整边距
    plot.margin = margin(l = 15, r = 5, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major.x = element_line(color = "gray90", size = 0.3),
    panel.grid.major.y = element_blank(), 
    #panel.grid.major = element_blank(),
    #panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  # 修改数值标签：字体缩小，放在条形图内部顶部
  geom_text(
    aes(label = format(Num, big.mark = ",", scientific = FALSE)), 
    hjust = 0,  # 居中
    vjust = -0, # 放在条形图顶部上方一点
    size = 3,   # 缩小字体
    #fontface = "bold",
    position = position_dodge(width = 0.9)
  ) +
  # 使用对数坐标轴，修复标签函数
  scale_y_log10(
    # 修复的标签函数，处理NA值
    labels = function(x) {
      sapply(x, function(val) {
        # 检查是否为NA或NULL
        if (is.na(val) || is.null(val)) {
          return("")
        }
        # 处理0值
        if (val == 0) {
          return("0")
        }
        # 处理小于1000的值
        if (val < 1000) {
          return(as.character(round(val)))
        }
        # 处理1000到1M之间的值
        if (val < 1e6) {
          return(paste0(round(val/1e3, 1), "K"))
        }
        # 处理大于等于1M的值
        return(paste0(round(val/1e6, 1), "M"))
      })
    },
    expand = expansion(mult = c(0, 0.3)),  # 增加顶部空间给标签
    # 设置合适的刻度
    breaks = 10^(0:ceiling(log10(max_value))),  # 动态生成刻度
    minor_breaks = NULL
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev) +
  # 使用coord_cartesian来限制显示范围
  coord_flip(ylim = c(1000, max_value * 1.1))

# 图2：MAF比例堆叠图（放在右边）
# 转换为长格式
data_long <- data %>%
  select(Type, MAF_low, MAF_middle, MAF_high) %>%
  pivot_longer(
    cols = c(MAF_low, MAF_middle, MAF_high), 
    names_to = "MAF_Category", 
    values_to = "Proportion"
  ) %>%
  mutate(
    MAF_Category = case_when(
      MAF_Category == "MAF_low"    ~ "MAF<1%",
      MAF_Category == "MAF_middle" ~ "1%<=MAF<5%",
      MAF_Category == "MAF_high"   ~ "MAF>=5%",
      TRUE                         ~ MAF_Category
    ),
    MAF_Category = factor(MAF_Category, levels = c("MAF<1%", "1%<=MAF<5%", "MAF>=5%"))
  )

data_long$Type <- factor(data_long$Type, levels = rev(type_order))

p_right_proportion <- ggplot(
  data_long, 
  aes(x = Type, y = Proportion, fill = MAF_Category)
) +
  geom_bar(stat = "identity", position = "fill", width = 0.7) +
  scale_fill_manual(
    values = c("MAF<1%" = "#1f77b4", "1%<=MAF<5%" = "#ff7f0e", "MAF>=5%" = "#AD1414"),
    name = NULL  # 去掉图例标题
  ) +
  # 去掉所有标题
  labs(
    title = NULL,
    x = NULL,
    y = NULL
  ) +
  theme_minimal() +
  theme(
    # 去掉主标题
    plot.title = element_blank(),
    # 去掉坐标轴标题
    axis.title = element_blank(),
    # 右边图：隐藏Y轴标签（因为左边图已经显示了）
    axis.text.y = element_blank(),
    #axis.ticks.y = element_blank(),
    # 显示X轴标签（百分比）
    
    axis.text.x = element_text(size = 9),
    # 图例放在右边
    legend.position = "right",
    legend.justification = "center",
    legend.box.just = "left",
    legend.margin = margin(l = 10, r = 5),
    legend.text = element_text(size = 10),
    legend.key.size = unit(1, "lines"),
    # 调整边距 - 与左图保持一致
    plot.margin = margin(l = 5, r = 15, t = 5, b = 15),
    # 去掉网格线
    panel.grid.major = element_blank(),
    panel.grid.minor = element_blank(),
    # 确保绘图区域对齐
    panel.spacing = unit(0, "cm"),
    plot.background = element_blank()
  ) +
  scale_y_continuous(
    labels = percent_format(), 
    expand = expansion(mult = c(0, 0))
  ) +
  coord_flip() +
  scale_x_discrete(limits = rev)


# 使用grid.arrange进行简单两列布局
p_SNP <- grid.arrange(
  p_left_total,  # 左图：总数条形图（对数坐标，数值标签在内部）
  p_right_proportion,  # 右图：MAF比例图（图例在右边，无数值标签）
  ncol = 2,
  # 调整宽度比例：左图稍宽（因为有Y轴标签），右图稍窄（图例在右边）
  widths = c(1.1, 0.9),
  # 关键：设置相同的行高，确保两个图高度完全一致
  heights = unit(1, "null"),
  # 对齐设置
  padding = unit(0, "cm"),
  top = textGrob("SNPs Distribution with Gene locus and MAF", gp = gpar(fontsize = 16, fontface = "bold"), hjust = 0.5, x = 0.5, vjust = 0.5)
)

# 保存图片
ggsave("SNP_gene_MAF.png", p_SNP, width = 14, height = 8, dpi = 300)
ggsave("SNP_gene_MAF.pdf", p_SNP, width = 14, height = 8)


library(cowplot)
blank <- ggplot() + theme_void()
top_row <- plot_grid(p_SV, blank, ncol = 2, rel_widths = c(1, 1), labels = c("A", ""), label_size = 14, label_fontface = "bold")
bottom_rows <- plot_grid(p_SV_DEL, p_SV_INS, p_SV_DUP, p_SV_INV, p_INDEL, p_SNP,
                         ncol = 2, labels = c("B", "C", "D", "E", "F", "G"), label_size = 14, label_fontface = "bold")
combined <- plot_grid(top_row, bottom_rows,
                      ncol = 1, rel_heights = c(1.2, 3))
ggsave("PanelF.png", combined, width = 28, height = 32, dpi = 300)
ggsave("PanelF.pdf", combined, width = 28, height = 32)


