# 3D建筑形态指标计算平台

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/)
[![QGIS](https://img.shields.io/badge/QGIS-3.20+-green.svg)](https://qgis.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个基于 QGIS 和 PyQt5 的 3D 建筑形态分析应用程序，专门用于计算城市形态学参数（Urban Morphology Parameters）和景观生态学指数。

## 🌟 主要特性

- **城市形态参数计算**: 支持多种城市覆盖参数（UCP）计算，包括λb、λp、λf、HAW、DH、MH、STDH等
- **景观指数分析**: 基于pylandstats库计算景观生态学指数
- **多种分析模式**: 支持基于栅格、矢量边界、建筑物数据的三种计算模式
- **可视化界面**: 基于PyQt5和QGIS的直观用户界面
- **批量处理**: 支持多进程并行计算，提高处理效率
- **结果输出**: 计算结果以GeoTIFF格式输出，便于后续分析

## 📋 功能模块

### 1. 城市形态参数计算 (UCP)
- **建筑覆盖率 (λb)**: Building Coverage Ratio
- **不透水面覆盖率 (λp)**: Impervious Surface Coverage Ratio  
- **前沿面积比 (λf)**: Frontal Area Ratio (0°, 45°, 90°, 135°)
- **高宽比 (HAW)**: Height-to-Width Ratio
- **建筑高度差 (DH)**: Building Height Difference
- **平均建筑高度 (MH)**: Mean Building Height
- **建筑高度标准差 (STDH)**: Standard Deviation of Building Height

### 2. 景观生态学指数
- **斑块密度 (Patch Density)**
- **边缘密度 (Edge Density)**
- **景观形状指数 (Landscape Shape Index)**
- **最大斑块指数 (Largest Patch Index)**
- **聚集指数 (Aggregation Index)**

## 🔧 环境要求

### 系统要求
- Windows 10/11（推荐）
- Python 3.7 或更高版本
- QGIS 3.20 或更高版本

### Python依赖
详见 `requirements.txt` 文件。主要依赖包括：
- PyQt5 >= 5.15.0
- QGIS >= 3.20.0
- numpy >= 1.20.0
- scipy >= 1.8.0
- rasterio >= 1.3.0
- geopandas >= 0.12.0
- pylandstats >= 3.0.0

## 🚀 快速开始

### 1. 安装QGIS
首先需要安装QGIS LTR版本：
1. 访问 [QGIS官网](https://qgis.org/zh-Hans/site/forusers/download.html)
2. 下载并安装QGIS LTR版本
3. 记住安装路径（如：`C:/Program Files/QGIS 3.28/`）

### 2. 克隆项目
```bash
git clone [repository-url]
cd urbanMorphology
```

### 3. 配置环境

#### 3.1 安装Python依赖
```bash
pip install -r requirements.txt
```

#### 3.2 配置QGIS路径
1. 复制配置模板：
   ```bash
   cp config.json.example config.json
   ```

2. 编辑 `config.json` 文件，修改QGIS路径：
   ```json
   {
     "qgis": {
       "prefix_path": "C:/Program Files/QGIS 3.28/apps/qgis-ltr"
     }
   }
   ```

### 4. 运行程序
```bash
python main.py
```

## 📁 项目结构

```
urbanMorphology/
├── main.py                 # 应用程序入口
├── config.py              # 配置管理模块
├── config.json           # 配置文件
├── config.json.example   # 配置模板
├── requirements.txt      # Python依赖
├── CLAUDE.md            # 开发文档
├── README.md           # 项目说明
├── 
├── Widgets/            # UI组件
│   ├── mainWindow.py   # 主窗口
│   └── ...
├── 
├── computation/        # 核心计算模块
│   ├── morphology.py   # 城市形态参数计算
│   ├── landscape.py    # 景观指数计算
│   ├── AI_Calculation.py # 聚集指数计算
│   └── extractByMask.py  # 栅格掩膜提取
├── 
├── utils/              # 工具类
│   └── tools.py        # 通用工具函数
├── 
├── resource/           # 资源文件
│   ├── buildings_GBA/  # 示例建筑数据
│   ├── GAIA/          # 示例底图数据
│   └── test/          # 测试数据
└── 
└── res/                # 计算结果输出目录
```

## 💻 使用说明

### 1. 数据准备
程序需要以下输入数据：
- **建筑物矢量数据**: Shapefile格式，需包含高度字段（默认为'Height'）
- **底图栅格数据**: GeoTIFF格式的土地利用或建筑底面数据

### 2. 界面操作
1. 启动程序后，系统会自动加载默认数据
2. 使用工具栏选择感兴趣区域
3. 选择要计算的参数类型
4. 点击计算按钮开始处理
5. 结果将自动保存到 `res/` 或 `resource/result/` 目录

### 3. 参数配置
可在 `config.json` 中修改以下计算参数：
```json
{
  "computation": {
    "number_of_each_degree": 120,    // 空间分辨率 (0.5' 精度)
    "building_min_height": 1,        // 建筑最小高度阈值
    "building_min_area": 5,          // 建筑最小面积阈值
    "height_field": "Height"         // 高度字段名称
  }
}
```

## 📊 输出结果

计算结果以GeoTIFF格式保存，文件命名规则：
```
{建筑物名称}_{网格坐标}_{参数名}.tif
```

结果目录结构：
```
res/
├── area/          # 建筑面积
├── count/         # 建筑数量
├── lb/           # 建筑覆盖率
├── lp/           # 不透水面覆盖率
├── haw/          # 高宽比
├── mh/           # 平均高度
└── ...           # 其他参数
```

## 🐛 常见问题

### Q1: 程序启动失败，提示QGIS路径错误
**A**: 请检查 `config.json` 中的QGIS路径是否正确。确保路径指向QGIS的apps/qgis-ltr目录。

### Q2: 计算过程中出现内存不足
**A**: 可以尝试：
- 减小计算区域范围
- 调整 `number_of_each_degree` 参数降低分辨率
- 关闭其他占用内存的程序

### Q3: 依赖包安装失败
**A**: 建议使用conda环境：
```bash
conda create -n urban python=3.8
conda activate urban
pip install -r requirements.txt
```

## 📝 开发指南

### 代码结构
- 主要业务逻辑在 `computation/` 目录
- UI组件在 `Widgets/` 目录
- 通用工具函数在 `utils/` 目录

### 扩展开发
1. 添加新的形态参数：在 `morphology.py` 中添加计算函数
2. 添加新的景观指数：在 `landscape.py` 中扩展
3. UI修改：编辑 `ui/mainWindow.ui` 然后重新生成Python代码

详细开发文档请参考 [CLAUDE.md](CLAUDE.md)

## 📄 许可证

本项目采用 MIT 许可证。详情请参见 [LICENSE](LICENSE) 文件。

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目。


## 🙏 致谢

感谢以下开源项目的支持：
- [QGIS](https://qgis.org/) - 地理信息系统
- [PyQt5](https://riverbankcomputing.com/software/pyqt/) - GUI框架
- [pylandstats](https://pylandstats.readthedocs.io/) - 景观指数计算库
- [rasterio](https://rasterio.readthedocs.io/) - 栅格数据处理

---

*本项目用于学术研究和城市规划分析，如用于商业用途请遵循相应许可协议。*
