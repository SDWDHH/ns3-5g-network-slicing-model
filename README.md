# NS-3 5G 网络切片仿真模型（测试/训练版）

> **⚠️ 预发布声明**  
> 本代码随本科毕业设计论文《基于NS-3的5G网络切片仿真模型设计》发布。  
> 目前仅为**测试/训练用途**，非完整工程，不承诺提供长期维护或技术支持。  
> 欢迎参考，但不建议直接用于生产或正式科研。

## 项目简介

基于 NS-3 仿真平台及其 5G NR 模块，实现了一个支持 **eMBB** 与 **uRLLC** 两类切片共存的仿真模型。  
主要特性：

- 支持 QoS Flow（GBR/NGBR）的切片标识与映射  
- 可配置调度器类型（RR / PF / QoS）及逻辑信道 QoS  
- 提供配套的 Python GUI 数据分析工具（四种分析图表）  
- 仿真结果自动输出 `_stats.txt`（人类可读）和 `_report.csv`（机器可读）  

**适用范围**：学习 NS-3 网络切片仿真方法、复现论文实验、做简单的参数遍历测试。

## 文件说明

- `my-slice-auto.cc` ：主仿真程序，基于 NS-3 的 `nr` 模块编写  
- `ns3_slice_gui_analyzer.py` ：数据分析 GUI 工具，依赖 Python 3

## 环境要求

- **操作系统**：Ubuntu 22.04（推荐） / 其他 Linux 发行版  
- **NS-3**：3.38 或 3.40（已测试），需包含 `nr` 模块  
- **Python**：3.8+，需要以下库：
  ```bash
  pip install matplotlib pandas numpy
  ```

## 快速使用（编译与仿真）

1. 将 `my-slice-auto.cc` 放入 NS-3 的 `scratch/` 目录（或 `contrib/` 并重新配置）。
2. 在 NS-3 根目录下编译：
   ```bash
   ./ns3 build
   ```
3. 运行单个仿真（示例：关闭切片，使用 RR 调度器，eMBB 负载 200 Mbps）：
   ```bash
   ./ns3 run "my-slice-auto --enableSlicing=false --schedulerType=RR --embbLoad=200"
   ```
4. 运行切片实验组（启用 QoS 调度与 GBR 预留）：
   ```bash
   ./ns3 run "my-slice-auto --enableSlicing=true --schedulerType=Qos --enableLcQos=true --urllcGbr=400 --urllcLoad=200"
   ```
   仿真结果会保存在 `./results/` 目录下（可通过 `--outputDir` 修改）。

## 常用命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `enableSlicing` | 是否启用切片（实验组开关） | true |
| `schedulerType` | 调度器类型 `RR` / `PF` / `Qos` | Qos |
| `enableLcQos` | 启用逻辑信道 QoS | true |
| `embbUeNum` | eMBB 用户数 | 4 |
| `urllcUeNum` | uRLLC 用户数 | 2 |
| `embbLoad` | eMBB 总负载 (Mbps) | 5000 |
| `urllcLoad` | 每个 uRLLC UE 负载 (kbps) | 200000 |
| `urllcGbr` | uRLLC 保证比特率 (kbps) | 400 |
| `simTag` | 输出文件标识 | default |
| `outputDir` | 结果目录 | ./results/ |

完整参数列表可在代码中查看或运行 `--help` 自动生成。

## 数据分析 GUI 工具

运行 Python 脚本即可启动图形界面：

```bash
python3 ns3_slice_gui_analyzer.py
```

工具提供四个分析模块：

1. **隔离性分析** – 对比有/无切片时 uRLLC 时延/丢包率随负载的变化  
2. **效率性分析** – 观察 eMBB 吞吐量与资源利用率  
3. **参数敏感性分析** – 热力图展示双参数变化对性能的影响  
4. **流量详情分析** – 绘制 CDF、箱线图、散点图等

使用步骤：  
- 先通过仿真生成 CSV 报告文件（`*_report.csv`）。  
- 在 GUI 中打开对应工具 → 添加文件 → 设置图表参数 → 生成图表。

## 已知局限

- 当前主要测试了**单小区静态场景**；多小区/移动性/阴影衰落的实验代码已集成但未充分验证。  
- 业务模型使用 CBR（恒定比特率），未实现 On-Off 突发模型（因为会大幅增加仿真时间）。  
- 调度策略为**静态优先级 + 固定 GBR**，未实现动态自适应调整。  
- 本代码仅作为毕业设计的辅助材料，不保证完全无 Bug。

## 许可证

本项目使用 **GNU General Public License v2.0**（与 NS-3 保持一致）。详见 `LICENSE` 文件。

## 引用信息（BibTeX）

```bibtex
@misc{Shuai2026Slice,
  author = {Shuai, Hongjie},
  title  = {Design of 5G Network Slicing Simulation Model Based on NS-3},
  year   = {2026},
  note   = {Undergraduate thesis, Northeast Forestry University},
  howpublished = {\url{https://github.com/SDWDHH/ns3-5g-network-slicing-model}}
}
```

## 联系方式

如有问题，欢迎提交 GitHub Issue，但不保证及时回复（个人毕业项目）。
