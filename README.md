# NS-3 5G 网络切片仿真模型（测试版）

> ⚠️ **预发布说明**  
> 本仓库为本科毕业设计《基于 NS-3 的 5G 网络切片仿真模型设计》配套代码。  
> **版本：v1.0.0-alpha** —— 代码可复现论文全部实验，但仍在整理中，接口可能变化。  
> 欢迎测试与反馈，但不保证长期维护。

## 简介

基于 NS-3 及其 5G NR 模块，实现了一个支持 **eMBB** 与 **uRLLC** 切片共存的仿真模型。  
主要特性：

- 使用 QoS Flow（5QI）区分切片，支持 GBR 资源预留
- 可配置 TDMA QoS 调度器 / RR 调度器（对照组）
- 支持单小区、多小区、阴影衰落、用户移动性
- 输出机器可读的 CSV 报告（吞吐量、时延、丢包率等）

配套 **Python GUI 分析工具**（`ns3_slice_gui_analyzer.py`），可自动生成隔离性、效率性、参数热力图等图表。

## 文件说明

| 文件 | 说明 |
|------|------|
| `src/my-slice-auto.cc` | NS-3 仿真主程序，接受命令行参数，输出 `*_stats.txt` 和 `*_report.csv` |
| `tools/ns3_slice_gui_analyzer.py` | 基于 Tkinter 的数据分析工具，需配合 CSV 文件使用 |

## 快速使用

### 1. 编译与运行 NS-3 仿真

将 `my-slice-auto.cc` 放入 NS-3 的 `scratch/` 或 `contrib/` 目录，然后：

```bash
# 进入 NS-3 根目录
./ns3 run "my-slice-auto --help"                     # 查看所有参数
./ns3 run "my-slice-auto --enableSlicing=true --embbLoad=150 --urllcLoad=200"   # 示例：启用切片
常用参数（默认值见代码）：

--enableSlicing：true（实验组） / false（对照组）

--schedulerType：Qos（切片感知） / RR（轮询）

--embbLoad：eMBB 总负载（Mbps）

--urllcLoad：每 uRLLC UE 负载（kbps）

--embbUeNum / --urllcUeNum：用户数

--simTag：输出文件名标识

仿真结束后，在 ./results/ 目录下会生成：

*_stats.txt：人类可读统计摘要

*_report.csv：机器可读详细报告（含每个流的时延、吞吐量等）

2. 使用 Python 分析工具
bash
# 安装依赖
pip install matplotlib pandas numpy

# 运行 GUI
python ns3_slice_gui_analyzer.py
工具提供四个分析模块：

隔离性分析：对比有无切片时 uRLLC 时延/丢包率随负载变化

效率性分析：eMBB 吞吐量 / 资源利用率对比

参数敏感性分析：热力图（需批量遍历实验数据）

流量详情分析：CDF、箱线图、散点图（单文件深度统计）

使用前需通过“运行控制”标签页批量仿真，或手动将已有 CSV 文件添加到工具中。

依赖
NS-3 版本：3.38 或 3.40（含 nr 模块）

编译环境：Ubuntu 22.04，g++，Python 3.8+

Python 库：matplotlib, pandas, numpy, tkinter（通常系统自带）

许可证
本项目使用 GNU General Public License v2.0（与 NS-3 保持一致）。
详见 LICENSE 文件。
学校：东北林业大学 控制与信息工程学院 通信工程 2022 级

注意：本代码为学术研究辅助工具，不保证商业用途的可靠性。欢迎提 Issue，但不保证及时回复。
