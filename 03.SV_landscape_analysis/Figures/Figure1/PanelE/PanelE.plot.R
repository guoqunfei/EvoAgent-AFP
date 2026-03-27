## 进入数据所在目录
setwd("~/Desktop/BGI/biodiversity/projects/Cyclone/Pig/analysis/Summary20260323/Figures/Figure1/PanelE")

library(ggplot2)
library(dplyr)
library(tidyr)
library(colorspace)

# 读取数据
data <- read.table("PolyAC.graph.data.addStage.txt", header = FALSE, col.names = c("SampleCount", "SVCount", "Type", "Stage"))

# 创建颜色映射函数 - 确保所有阶段都有正确的颜色
create_colors <- function() {
  # 基础颜色
  base_colors <- c(AC1 = "#3498DB", AC2 = "#2ECC71", AC3 = "#E74C3C")
  
  # 为每个阶段创建颜色变体
  color_palette <- list()
  
  # Stage1 - 最浅
  color_palette[["stage1"]] <- c(
    AC1 = lighten(base_colors["AC1"], amount = 0.4),
    AC2 = lighten(base_colors["AC2"], amount = 0.4),
    AC3 = lighten(base_colors["AC3"], amount = 0.4)
  )
  
  # Stage2 - 中等浅
  color_palette[["stage2"]] <- c(
    AC1 = lighten(base_colors["AC1"], amount = 0.2),
    AC2 = lighten(base_colors["AC2"], amount = 0.2),
    AC3 = lighten(base_colors["AC3"], amount = 0.2)
  )
  
  # Stage3 - 基准色（不进行调整）
  color_palette[["stage3"]] <- c(
    AC1 = "#3498DB",
    AC2 = "#2ECC71",
    AC3 = "#E74C3C"
    #AC1 = base_colors["AC1"],
    #AC2 = base_colors["AC2"],
    #AC3 = base_colors["AC3"]
  )
  
  # Stage4 - 最深
  color_palette[["stage4"]] <- c(
    AC1 = darken(base_colors["AC1"], amount = 0.2),
    AC2 = darken(base_colors["AC2"], amount = 0.2),
    AC3 = darken(base_colors["AC3"], amount = 0.2)
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
  geom_area(position = "stack", alpha = 0.85, color = NA) +
  # 添加阶段分界线
  geom_vline(xintercept = c(149, 297, 444), 
             linetype = "dashed", color = "black", linewidth = 0.8) +
  # 添加阶段标签 - 移动到顶部
  annotate("text", x = c(75, 223, 371, 518), y = max_sv,
           label = c("Stage 1", "Stage 2", 
                     "Stage 3", "Stage 4"),
           size = 4.5, fontface = "bold", color = "black", vjust = 2.5) +
  # 设置颜色映射
  scale_fill_identity() +
  # 坐标轴设置
  scale_x_continuous(breaks = seq(0, 600, by = 50), expand = c(0, 0)) +
  scale_y_continuous(limits = c(0, 500000), breaks = c(0, 100000, 200000, 300000, 400000, 500000), labels = c("0", "100k", "200k", "300k", "400k", "500k")) +
  #scale_y_continuous(labels = scales::comma, expand = expansion(mult = c(0, 0.1))) +
  # 标题和标签
  labs(#title = "Cumulative Structural Variants (SVs) by Sample Size",
       x = "Number of Samples",
       y = "Cumulative SVs") +
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
  Type = c("AC1", "AC2", "AC3")
) %>%
  rowwise() %>%
  mutate(
    Color = color_palette[[Stage]][Type],
    Label = paste(Type, Stage, sep = " - ")
  ) %>%
  ungroup() %>%
  mutate(
    Stage = factor(Stage, levels = c("stage1", "stage2", "stage3", "stage4")),
    Type = factor(Type, levels = c("AC1", "AC2", "AC3"))
  )

# 先创建组合标签（确保顺序正确）
legend_data$combo <- with(legend_data, paste(Type, Stage, sep = "_"))
# 或者使用 interaction：legend_data$combo <- interaction(Type, Stage, sep = " ")

legend_plot <- ggplot(legend_data, aes(x = combo, y = 1)) +  # y固定为1，x为12个组合
  geom_tile(aes(fill = Color), color = "white", size = 0.8) +
  geom_text(aes(label = recode(Type,
                               "AC1" = "AC=1",
                               "AC2" = "AC=2", 
                               "AC3" = "AC>2")), 
            color = "black", size = 3, fontface = "bold") +
  scale_fill_identity() +
  scale_x_discrete(labels = c("Stage 1","Stage 2","Stage 3","Stage 4", "Stage 1","Stage 2","Stage 3","Stage 4", "Stage 1","Stage 2","Stage 3","Stage 4")) +
  scale_y_continuous(
    breaks = NULL,      # 隐藏Y轴刻度
    labels = NULL,      # 隐藏Y轴标签
    expand = c(0, 0)    # 去除Y轴边距
  ) +
  labs(x = NULL, y = NULL) +
  theme_bw() +
  theme(
    # 关键：X轴标签旋转45度避免重叠，或改为垂直(angle=90)
    axis.text.x = element_text(face = "bold", size = 7, angle = 0, hjust = 1),
    axis.ticks.x = element_blank(),  # 可选：隐藏X轴刻度线
    axis.ticks.y = element_blank(),  # 必须：隐藏Y轴刻度线
    plot.margin = margin(20, 20, 10, 10)
  )


library(cowplot)
library(patchwork)

combined <- legend_plot / main_plot + plot_layout(heights = c(0.05, 1))
ggsave("PanelE.png", combined, width = 14, height = 8,  dpi = 300)
ggsave("PanelE.pdf", combined, width = 14, height = 8)