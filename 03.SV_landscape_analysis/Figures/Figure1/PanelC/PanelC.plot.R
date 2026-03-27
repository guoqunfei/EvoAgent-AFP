# 进入数据所在路径
setwd("~/Desktop/BGI/biodiversity/projects/Cyclone/Pig/analysis/Summary20260323/Figures/Figure1/PanelC")

library(ggplot2)
library(dplyr)
library(tidyr)
library(colorspace)
library(cowplot)

# 读取数据
data <- read.table("AllStages.SVcount.DEL-INS.txt", header = FALSE, col.names = c("SampleCount", "SVCount", "Type", "Stage"))

# 创建颜色映射函数 - 确保所有阶段都有正确的颜色
create_colors <- function() {
  # 基础颜色
  base_colors <- c(DEL = "#3498DB", INS = "#2ECC71")
  
  # 为每个阶段创建颜色变体
  color_palette <- list()
  
  # Stage1 - 最浅
  color_palette[["stage1"]] <- c(
    DEL = lighten(base_colors["DEL"], amount = 0.4),
    INS = lighten(base_colors["INS"], amount = 0.4)
  )
  
  # Stage2 - 中等浅
  color_palette[["stage2"]] <- c(
    DEL = lighten(base_colors["DEL"], amount = 0.2),
    INS = lighten(base_colors["INS"], amount = 0.2)
  )
  
  # Stage3 - 基准色（不进行调整）
  color_palette[["stage3"]] <- c(
    DEL = "#3498DB",
    INS = "#2ECC71"
  )
  
  # Stage4 - 最深
  color_palette[["stage4"]] <- c(
    DEL = darken(base_colors["DEL"], amount = 0.2),
    INS = darken(base_colors["INS"], amount = 0.2)
  )
  
  return(color_palette)
}

# 创建颜色映射
color_palette <- create_colors()

# 为数据分配颜色
data <- data %>%
  rowwise() %>%
  mutate(Color = color_palette[[Stage]][Type]) %>%
  ungroup()

# 计算最大SV值用于定位标签
max_sv <- max(data$SVCount) * 1.5

# 创建主图
main_plot <- ggplot(data, aes(x = SampleCount, y = SVCount, fill = Color, group = interaction(Type, Stage))) +
  #geom_area(position = "stack", alpha = 0.85, color = NA) +
  geom_bar(stat = "identity") + 
  # 添加阶段分界线
  geom_vline(xintercept = c(149, 297, 444), 
             linetype = "dashed", color = "black", linewidth = 0.8) +
  # 添加阶段标签 - 移动到顶部
  annotate("text", x = c(75, 224, 374, 524), y = max_sv + 16000,
           label = c("Stage 1", "Stage 2", 
                     "Stage 3", "Stage 4"),
           size = 4.5, fontface = "bold", color = "black", vjust = 2.5) +
  # 设置颜色映射
  scale_fill_identity() +
  # 坐标轴设置
  scale_x_continuous(breaks = seq(50, 550, by = 100), expand = c(0, 0)) +
  scale_y_continuous(limits = c(0, 60000), breaks = c(0, 20000, 40000, 60000), labels = c("0", "20k", "40k", "60k")) +
  #scale_y_continuous(labels = scales::comma, expand = expansion(mult = c(0, 0.1))) +
  # 标题和标签
  labs(#title = "Cumulative Structural Variants (SVs) by Sample Size",
    x = "Number of Samples",
    y = "SVs number") +
  # 主题设置
  theme_classic(base_size = 14) +
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold", size = 16),
    #panel.grid.major = element_line(color = "grey90"),
    panel.grid.minor = element_blank(),
    panel.border = element_rect(color = "grey30", fill = NA, linewidth = 0.5),
    plot.margin = margin(20, 20, 20, 20),
    legend.position = "none"
  )

# 创建图例数据
legend_data <- expand.grid(
  Stage = c("stage1", "stage2", "stage3", "stage4"),
  Type = c("DEL", "INS")
) %>%
  rowwise() %>%
  mutate(
    Color = color_palette[[Stage]][Type],
    Label = paste(Type, Stage, sep = " - ")
  ) %>%
  ungroup() %>%
  mutate(
    Stage = factor(Stage, levels = c("stage1", "stage2", "stage3", "stage4")),
    Type = factor(Type, levels = c("DEL", "INS"))
  )

# 创建图例 - 移到左上角
legend_plot <- ggplot(legend_data, aes(x = Stage, y = Type)) +
  geom_tile(aes(fill = Color), color = "white", size = 0.8) +
  geom_text(aes(label = Type), color = "black", size = 4, fontface = "bold") +
  scale_fill_identity() +
  scale_x_discrete(labels = c("Stage 1", "Stage 2", "Stage 3", "Stage 4")) +
  scale_y_discrete(expand = c(0.2, 0.2)) +
  labs(x = NULL, y = NULL) +
  theme_bw() +
  theme(
    axis.text.x = element_text(face = "bold", size = 10, margin = margin(t = 5)),
    plot.margin = margin(5, 5, 5, 5)
  )

# 组合主图和图例 - 图例移动到左上角
final_plot1 <- ggdraw() + draw_plot(main_plot) 
#+ draw_plot(legend_plot, x = 0.05, y = 0.72, width = 0.25, height = 0.25)
# 显示图像
pdf("AllStages.SVcount.DEL-INS.pdf", width = 14, height = 5)
print(final_plot1)
dev.off()


# 读取数据
data <- read.table("AllStages.SVcount.DUP-INV.txt", header = FALSE, col.names = c("SampleCount", "SVCount", "Type", "Stage"))

# 创建颜色映射函数 - 确保所有阶段都有正确的颜色
create_colors <- function() {
  # 基础颜色
  base_colors <- c(DUP = "#31688E", INV = "#8A8A8A")
  
  # 为每个阶段创建颜色变体
  color_palette <- list()
  
  # Stage1 - 最浅
  color_palette[["stage1"]] <- c(
    DUP = lighten(base_colors["DUP"], amount = 0.4),
    INV = lighten(base_colors["INV"], amount = 0.4)
  )
  
  # Stage2 - 中等浅
  color_palette[["stage2"]] <- c(
    DUP = lighten(base_colors["DUP"], amount = 0.2),
    INV = lighten(base_colors["INV"], amount = 0.2)
  )
  
  # Stage3 - 基准色（不进行调整）
  color_palette[["stage3"]] <- c(
    DUP = "#31688E",
    INV = "#8A8A8A"
  )
  
  # Stage4 - 最深
  color_palette[["stage4"]] <- c(
    DUP = darken(base_colors["DUP"], amount = 0.2),
    INV = darken(base_colors["INV"], amount = 0.2)
  )
  
  return(color_palette)
}

# 创建颜色映射
color_palette <- create_colors()

# 为数据分配颜色
data <- data %>%
  rowwise() %>%
  mutate(Color = color_palette[[Stage]][Type]) %>%
  ungroup()

# 计算最大SV值用于定位标签
max_sv <- max(data$SVCount) * 1.5

# 创建主图
main_plot <- ggplot(data, aes(x = SampleCount, y = SVCount, fill = Color, group = interaction(Type, Stage))) +
  #geom_area(position = "stack", alpha = 0.85, color = NA) +
  geom_bar(stat = "identity") + 
  # 添加阶段分界线
  geom_vline(xintercept = c(149, 297, 444), 
             linetype = "dashed", color = "black", linewidth = 0.8) +
  # 添加阶段标签 - 移动到顶部
  annotate("text", x = c(75, 224, 374, 524), y = max_sv + 100,
           label = c("Stage 1", "Stage 2", 
                     "Stage 3", "Stage 4"),
           size = 4.5, fontface = "bold", color = "black", vjust = 2.5) +
  # 设置颜色映射
  scale_fill_identity() +
  # 坐标轴设置
  scale_x_continuous(breaks = seq(50, 550, by = 100), expand = c(0, 0)) +
  scale_y_continuous(labels = scales::comma, expand = expansion(mult = c(0, 0.1))) +
  # 标题和标签
  labs(#title = "Cumulative Structural Variants (SVs) by Sample Size",
    x = "Number of Samples",
    y = "SVs number") +
  # 主题设置
  theme_classic(base_size = 14) +
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold", size = 16),
    #panel.grid.major = element_line(color = "grey90"),
    panel.grid.minor = element_blank(),
    panel.border = element_rect(color = "grey30", fill = NA, linewidth = 0.5),
    plot.margin = margin(20, 20, 20, 20),
    legend.position = "none"
  )

# 创建图例数据
legend_data <- expand.grid(
  Stage = c("stage1", "stage2", "stage3", "stage4"),
  Type = c("DUP", "INV")
) %>%
  rowwise() %>%
  mutate(
    Color = color_palette[[Stage]][Type],
    Label = paste(Type, Stage, sep = " - ")
  ) %>%
  ungroup() %>%
  mutate(
    Stage = factor(Stage, levels = c("stage1", "stage2", "stage3", "stage4")),
    Type = factor(Type, levels = c("DUP", "INV"))
  )

# 创建图例 - 移到左上角
legend_plot <- ggplot(legend_data, aes(x = Stage, y = Type)) +
  geom_tile(aes(fill = Color), color = "white", size = 0.8) +
  geom_text(aes(label = Type), color = "black", size = 4, fontface = "bold") +
  scale_fill_identity() +
  scale_x_discrete(labels = c("Stage 1", "Stage 2", "Stage 3", "Stage 4")) +
  scale_y_discrete(expand = c(0.2, 0.2)) +
  labs(x = NULL, y = NULL) +
  theme_bw() +
  theme(
    axis.text.x = element_text(face = "bold", size = 10, margin = margin(t = 5)),
    plot.margin = margin(5, 5, 5, 5)
  )

# 组合主图和图例 - 图例移动到左上角
final_plot2 <- ggdraw() + draw_plot(main_plot)
# + draw_plot(legend_plot, x = 0.05, y = 0.72, width = 0.25, height = 0.25)
# 显示图像
pdf("AllStages.SVcount.DUP-INV.pdf", width = 14, height = 5)
print(final_plot2)
dev.off()

combined <- final_plot1 / final_plot2
ggsave("PanelC.png", combined, width = 14, height = 10, dpi = 300)
ggsave("PanelC.pdf", combined, width = 14, height = 10)