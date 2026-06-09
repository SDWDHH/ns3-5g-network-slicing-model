#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
5G网络切片仿真配置与数据分析一体化工具
作者: 帅宏杰
用途: 毕业设计 - 自动化仿真、参数遍历、数据处理和图表生成
功能: 
    - 仿真参数配置、单次/批量运行
    - 四种数据分析工具（隔离性、效率性、参数敏感性、流量详情）
    - 中文图表、文件列表简洁、图形数据标签
修订: 2025-06 界面整合、中文修复、滚动优化、文件分类、帮助完善
"""

import os
import sys
import json
import glob
import subprocess
import threading
import time
import stat
import re
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from tkinter import font as tkfont
from datetime import datetime

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import pandas as pd
import numpy as np

# ==================== 强化 matplotlib 中文支持 ====================
# 动态检测可用中文字体，避免矩形框乱码
def configure_matplotlib_fonts():
    import platform
    import matplotlib.font_manager as fm
    """配置 matplotlib 中文字体，确保正常显示"""
    # 1. 先尝试从系统已安装字体中查找
    chinese_fonts = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 
                     'Noto Sans CJK SC', 'Source Han Sans SC', 'AR PL UMing CN', 
                     'STHeiti', 'STSong', 'SimSun']
    available = [f.name for f in fm.fontManager.ttflist]
    selected = None
    for font in chinese_fonts:
        if font in available:
            selected = font
            break

    # 2. 如果没找到，尝试扫描系统常见字体路径并动态注册
    if not selected:
        font_paths = []
        system = platform.system()
        if system == 'Windows':
            font_paths = [
                'C:/Windows/Fonts/simhei.ttf',
                'C:/Windows/Fonts/msyh.ttc',
                'C:/Windows/Fonts/simsun.ttc',
            ]
        elif system == 'Darwin':  # macOS
            font_paths = [
                '/System/Library/Fonts/PingFang.ttc',
                '/Library/Fonts/Arial Unicode MS.ttf',
            ]
        else:  # Linux
            font_paths = [
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/arphic/uming.ttc',
                '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
            ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    fm.fontManager.addfont(path)
                    prop = fm.FontProperties(fname=path)
                    selected = prop.get_name()
                    break
                except:
                    continue

    # 3. 应用字体
    if selected:
        plt.rcParams['font.sans-serif'] = [selected] + plt.rcParams['font.sans-serif']
    else:
        print("警告: 未找到中文字体，图表中的中文可能显示为方框。建议安装中文字体。")
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans'] + plt.rcParams['font.sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

configure_matplotlib_fonts()

# ==================== 配置管理 ====================
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slice_gui_analyzer_config.json")
DEFAULT_CONFIG = {
    "last_input_dir": "",
    "last_output_dir": "",
    "last_selected_files": [],
    "ns3_root": "",
    "ns3_program": "my-slice-auto"
}

class ConfigManager:
    @staticmethod
    def load():
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for k, v in DEFAULT_CONFIG.items():
                        if k not in config:
                            config[k] = v
                    return config
            except:
                pass
        return DEFAULT_CONFIG.copy()
    
    @staticmethod
    def save(config):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")

# ==================== 数据加载器 ====================
class DataLoader:
    @staticmethod
    def parse_csv(filepath):
        config_info = {}
        flow_details = []
        summaries = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('# CONFIG,'):
                    parts = line.split(',')
                    if len(parts) >= 16:   # 新格式
                        config_info['simTag'] = parts[1]
                        config_info['slicingEnabled'] = parts[2] == '1'
                        config_info['schedulerType'] = parts[3]
                        config_info['lcQosEnabled'] = parts[4] == '1'
                        config_info['urllcUeNum'] = int(parts[5])
                        config_info['embbUeNum'] = int(parts[6])
                        config_info['urllcLoadKbps'] = float(parts[7])
                        config_info['embbLoadMbps'] = float(parts[8])
                        config_info['urllcPriority'] = int(parts[9])
                        config_info['embbPriority'] = int(parts[10])
                        config_info['flowDurationSec'] = float(parts[11])
                        config_info['gNbNum'] = int(parts[12])
                        config_info['enableShadow'] = parts[13] == '1'
                        config_info['enableMobility'] = parts[14] == '1'
                        config_info['ueSpeed'] = float(parts[15])
                    elif len(parts) >= 12:  # 兼容旧格式
                        config_info['simTag'] = parts[1]
                        config_info['slicingEnabled'] = parts[2] == '1'
                        config_info['schedulerType'] = parts[3]
                        config_info['lcQosEnabled'] = parts[4] == '1'
                        config_info['urllcUeNum'] = int(parts[5])
                        config_info['embbUeNum'] = int(parts[6])
                        config_info['urllcLoadKbps'] = float(parts[7])
                        config_info['embbLoadMbps'] = float(parts[8])
                        config_info['urllcPriority'] = int(parts[9])
                        config_info['embbPriority'] = int(parts[10])
                        config_info['flowDurationSec'] = float(parts[11])
                         # 新字段设默认值
                        config_info['gNbNum'] = 1
                        config_info['enableShadow'] = False
                        config_info['enableMobility'] = False
                        config_info['ueSpeed'] = 0.0
                elif line.startswith('FLOW_DETAIL,'):
                    parts = line.split(',')
                    if len(parts) >= 16:
                        flow_details.append({
                            'type': 'FLOW_DETAIL',
                            'flow_id': int(parts[1]),
                            'flow_type': parts[2],
                            'src_ip': parts[3],
                            'dst_ip': parts[4],
                            'dst_port': int(parts[5]),
                            'tx_packets': int(parts[6]),
                            'rx_packets': int(parts[7]),
                            'lost_packets': int(parts[8]),
                            'loss_rate': float(parts[9]),
                            'throughput_mbps': float(parts[10]),
                            'delay_ms': float(parts[11]),
                            'jitter_ms': float(parts[12]),
                            'delay_sum_sec': float(parts[13]),
                            'jitter_sum_sec': float(parts[14]),
                            'rx_bytes': int(parts[15])
                        })
                elif line.startswith('SUMMARY,'):
                    parts = line.split(',')
                    if len(parts) >= 16:
                        summaries.append({
                            'type': 'SUMMARY',
                            'flow_type': parts[1],
                            'active_flows': int(parts[2]),
                            'expected_flows': int(parts[3]),
                            'total_throughput': float(parts[4]),
                            'avg_throughput': float(parts[5]),
                            'avg_delay': float(parts[6]),
                            'min_delay': float(parts[7]),
                            'max_delay': float(parts[8]),
                            'p95_delay': float(parts[9]),
                            'p99_delay': float(parts[10]),
                            'avg_jitter': float(parts[11]),
                            'tx_packets': int(parts[12]),
                            'rx_packets': int(parts[13]),
                            'lost_packets': int(parts[14]),
                            'loss_rate': float(parts[15])
                        })
            return {
                'config': config_info,
                'flows': flow_details,
                'summaries': summaries,
                'filepath': filepath,
                'filename': os.path.basename(filepath)
            }
        except Exception as e:
            raise Exception(f"解析文件失败: {str(e)}")
    
    @staticmethod
    def load_multiple_files(filepaths):
        all_data = []
        for fp in filepaths:
            try:
                all_data.append(DataLoader.parse_csv(fp))
            except Exception as e:
                print(f"跳过文件 {fp}: {e}")
        return all_data

# ==================== 图表工具基类 ====================
class ChartToolBase:
    def __init__(self, parent, title):
        self.parent = parent
        self.title = title
        self.window = None
        self.fig = None
        self.ax = None
        self.canvas = None
        self.current_data = None
        self.output_dir = ""
        self.experiment_name = ""
        
    def create_window(self):
        self.window = tk.Toplevel(self.parent)
        self.window.title(f"5G切片分析工具 - {self.title}")
        self.window.geometry("1200x800")
        self.window.minsize(1000, 700)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.create_ui()
        
    def create_ui(self):
        raise NotImplementedError
        
    def on_close(self):
        if self.fig:
            plt.close(self.fig)
        self.window.destroy()
        
    def get_unique_filename(self, base_name, ext=".png"):
        if not self.output_dir:
            self.output_dir = filedialog.askdirectory(title="选择输出目录")
            if not self.output_dir:
                return None
            config = ConfigManager.load()
            config['last_output_dir'] = self.output_dir
            ConfigManager.save(config)
        counter = 1
        while True:
            filename = f"{base_name}_{counter}{ext}"
            filepath = os.path.join(self.output_dir, filename)
            if not os.path.exists(filepath):
                return filepath
            counter += 1
            
    def save_figure(self, base_name):
        filepath = self.get_unique_filename(base_name, ".png")
        if filepath:
            self.fig.savefig(filepath, dpi=300, bbox_inches='tight')
            messagebox.showinfo("保存成功", f"图表已保存至:\n{filepath}")
            return filepath
        return None
        
    def show_in_window(self):
        if not self.fig:
            return
        preview_window = tk.Toplevel(self.window)
        preview_window.title(f"图形预览 - {self.title}")
        preview_window.geometry("1000x700")
        canvas = FigureCanvasTkAgg(self.fig, master=preview_window)
        canvas.draw()
        toolbar = NavigationToolbar2Tk(canvas, preview_window)
        toolbar.update()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        toolbar.pack(fill=tk.X)
        ttk.Button(preview_window, text="保存图片", 
                  command=lambda: self.save_figure(self.experiment_name or "chart")).pack(pady=5)

# ==================== 工具1: 隔离性分析 ====================
class IsolationAnalysisTool(ChartToolBase):
    def __init__(self, parent):
        super().__init__(parent, "隔离性分析")
        
    def create_ui(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        control_frame = ttk.LabelFrame(main_frame, text="数据选择", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(control_frame, text="选择CSV报告文件(可多选):").grid(row=0, column=0, sticky=tk.W)
        self.file_listbox = tk.Listbox(control_frame, height=8, selectmode=tk.MULTIPLE)
        self.file_listbox.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=5)
        self.file_path_map = {}
        
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=1, column=2, padx=5)
        ttk.Button(btn_frame, text="添加文件", command=self.add_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清空列表", command=self.clear_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="全部选择", command=self.select_all_files).pack(fill=tk.X, pady=2)
        
        settings_frame = ttk.LabelFrame(control_frame, text="图表设置", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)
        
        ttk.Label(settings_frame, text="实验名称:").grid(row=0, column=0, sticky=tk.W)
        self.exp_name_var = tk.StringVar(value="隔离性分析")
        ttk.Entry(settings_frame, textvariable=self.exp_name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(settings_frame, text="Y轴指标:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.metric_var = tk.StringVar(value="avg_delay")
        metric_combo = ttk.Combobox(settings_frame, textvariable=self.metric_var, 
                                   values=["avg_delay", "p95_delay", "p99_delay", "avg_jitter", "loss_rate"],
                                   state="readonly", width=15)
        metric_combo.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        ttk.Label(settings_frame, text="X轴变量:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.x_var = tk.StringVar(value="embbLoadMbps")
        x_combo = ttk.Combobox(settings_frame, textvariable=self.x_var,
                              values=["embbLoadMbps", "embbUeNum", "urllcLoadKbps", "gNbNum"],
                              state="readonly", width=15)
        x_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        action_frame = ttk.Frame(control_frame)
        action_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(action_frame, text="📊 生成图表", command=self.generate_chart, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="💾 保存图片", command=self.save_current_chart, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="👁 预览图形", command=self.show_in_window, width=15).pack(side=tk.LEFT, padx=5)
        
        self.chart_frame = ttk.LabelFrame(main_frame, text="图表预览", padding="5")
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        
        self.status_var = tk.StringVar(value="就绪 - 请选择数据文件")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, pady=(5, 0))
        
        self.load_memory_files()
        
    def load_memory_files(self):
        config = ConfigManager.load()
        for f in config.get('last_selected_files', []):
            if os.path.exists(f):
                self._add_file_item(f)
                
    def _add_file_item(self, full_path):
        display_name = os.path.basename(full_path)
        if display_name not in self.file_listbox.get(0, tk.END):
            self.file_listbox.insert(tk.END, display_name)
            self.file_path_map[display_name] = full_path
            
    def add_files(self):
        config = ConfigManager.load()
        initial_dir = config.get('last_input_dir', '')
        files = filedialog.askopenfilenames(
            title="选择CSV报告文件",
            initialdir=initial_dir if initial_dir else os.getcwd(),
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if files:
            for f in files:
                self._add_file_item(f)
            config['last_input_dir'] = os.path.dirname(files[0])
            config['last_selected_files'] = [self.file_path_map[name] for name in self.file_listbox.get(0, tk.END)]
            ConfigManager.save(config)
            
    def clear_files(self):
        self.file_listbox.delete(0, tk.END)
        self.file_path_map.clear()
        config = ConfigManager.load()
        config['last_selected_files'] = []
        ConfigManager.save(config)

    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END)
        
    def get_selected_paths(self):
        selected_indices = self.file_listbox.curselection()
        paths = []
        for idx in selected_indices:
            display_name = self.file_listbox.get(idx)
            if display_name in self.file_path_map:
                paths.append(self.file_path_map[display_name])
        return paths
        
    def generate_chart(self):
        files = self.get_selected_paths()
        if not files:
            messagebox.showwarning("警告", "请先选择数据文件")
            return
        try:
            all_data = DataLoader.load_multiple_files(files)
            if not all_data:
                messagebox.showerror("错误", "无法解析选中的文件")
                return
            metric = self.metric_var.get()
            x_var = self.x_var.get()
            metric_labels = {'avg_delay': '平均时延 (ms)', 'p95_delay': 'P95时延 (ms)',
                             'p99_delay': 'P99时延 (ms)', 'avg_jitter': '平均抖动 (ms)',
                             'loss_rate': '丢包率 (%)'}
            sliced_data = {'true': [], 'false': []}
            for data in all_data:
                config = data['config']
                for s in data['summaries']:
                    if s['flow_type'] == 'uRLLC':
                        point = {
                            'x': config.get(x_var, 0),
                            'y': s.get(metric, 0),
                            'slicing': config.get('slicingEnabled', False),
                            'scheduler': config.get('schedulerType', 'Unknown')
                        }
                        key = 'true' if point['slicing'] else 'false'
                        sliced_data[key].append(point)
                        break
            for key in sliced_data:
                sliced_data[key].sort(key=lambda p: p['x'])
            if self.fig:
                plt.close(self.fig)
            self.fig, self.ax = plt.subplots(figsize=(10, 6), dpi=100)
            colors = {'true': '#e74c3c', 'false': '#3498db'}
            labels = {'true': '启用切片', 'false': '无切片'}
            markers = {'true': 'o', 'false': 's'}
            for key in ['false', 'true']:
                if sliced_data[key]:
                    x_vals = [p['x'] for p in sliced_data[key]]
                    y_vals = [p['y'] for p in sliced_data[key]]
                    self.ax.plot(x_vals, y_vals, marker=markers[key], linewidth=2.5, 
                               markersize=8, color=colors[key], label=labels[key])
                    for xi, yi in zip(x_vals, y_vals):
                        self.ax.annotate(f'{yi:.2f}', (xi, yi), textcoords="offset points",
                                         xytext=(0,10), ha='center', fontsize=8)
            x_labels = {'embbLoadMbps': 'eMBB负载 (Mbps)', 'embbUeNum': 'eMBB用户数',
                        'urllcLoadKbps': 'uRLLC负载 (kbps)', 'gNbNum': 'gNB数量'}
            self.ax.set_xlabel(x_labels.get(x_var, x_var), fontsize=12)
            self.ax.set_ylabel(metric_labels.get(metric, metric), fontsize=12)
            self.ax.set_title(f'uRLLC {metric_labels.get(metric, metric)} 随 {x_labels.get(x_var, x_var)} 变化', 
                            fontsize=14, fontweight='bold')
            self.ax.legend(fontsize=11, loc='best')
            self.ax.grid(True, alpha=0.3, linestyle='--')
            if sliced_data['true'] and sliced_data['false']:
                improvements = []
                for p_sliced in sliced_data['true']:
                    for p_no in sliced_data['false']:
                        if abs(p_sliced['x'] - p_no['x']) < 0.01:
                            if p_no['y'] > 0:
                                imp = (p_no['y'] - p_sliced['y']) / p_no['y'] * 100
                                improvements.append(imp)
                            break
                if improvements:
                    avg_imp = np.mean(improvements)
                    self.ax.text(0.02, 0.98, f'平均性能提升: {avg_imp:.1f}%', 
                               transform=self.ax.transAxes, fontsize=10,
                               verticalalignment='top', bbox=dict(boxstyle='round', 
                               facecolor='wheat', alpha=0.5))
            plt.tight_layout()
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            toolbar = NavigationToolbar2Tk(self.canvas, self.chart_frame)
            toolbar.update()
            self.experiment_name = self.exp_name_var.get()
            self.status_var.set(f"图表生成完成 - 数据点: 切片={len(sliced_data['true'])}, 无切片={len(sliced_data['false'])}")
        except Exception as e:
            messagebox.showerror("错误", f"生成图表失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def save_current_chart(self):
        if not self.fig:
            messagebox.showwarning("警告", "请先生成图表")
            return
        self.save_figure(self.experiment_name or "隔离性分析")

# ==================== 工具2: 效率性分析 ====================
class EfficiencyAnalysisTool(ChartToolBase):
    def __init__(self, parent):
        super().__init__(parent, "效率性分析")
        
    def create_ui(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.LabelFrame(main_frame, text="数据选择", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(control_frame, text="选择CSV报告文件(可多选):").grid(row=0, column=0, sticky=tk.W)
        self.file_listbox = tk.Listbox(control_frame, height=8, selectmode=tk.MULTIPLE)
        self.file_listbox.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=5)
        self.file_path_map = {}
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=1, column=2, padx=5)
        ttk.Button(btn_frame, text="添加文件", command=self.add_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清空列表", command=self.clear_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="全部选择", command=self.select_all_files).pack(fill=tk.X, pady=2)
        settings_frame = ttk.LabelFrame(control_frame, text="图表设置", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)
        ttk.Label(settings_frame, text="实验名称:").grid(row=0, column=0, sticky=tk.W)
        self.exp_name_var = tk.StringVar(value="效率性分析")
        ttk.Entry(settings_frame, textvariable=self.exp_name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(settings_frame, text="图表类型:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.chart_type_var = tk.StringVar(value="throughput")
        ttk.Combobox(settings_frame, textvariable=self.chart_type_var,
                    values=["throughput", "utilization", "comparison"],
                    state="readonly", width=15).grid(row=0, column=3, sticky=tk.W, padx=5)
        action_frame = ttk.Frame(control_frame)
        action_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(action_frame, text="📊 生成图表", command=self.generate_chart, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="💾 保存图片", command=self.save_current_chart, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="👁 预览图形", command=self.show_in_window, width=15).pack(side=tk.LEFT, padx=5)
        self.chart_frame = ttk.LabelFrame(main_frame, text="图表预览", padding="5")
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, pady=(5, 0))
        self.load_memory_files()
        
    def load_memory_files(self):
        config = ConfigManager.load()
        for f in config.get('last_selected_files', []):
            if os.path.exists(f):
                self._add_file_item(f)
                
    def _add_file_item(self, full_path):
        display_name = os.path.basename(full_path)
        if display_name not in self.file_listbox.get(0, tk.END):
            self.file_listbox.insert(tk.END, display_name)
            self.file_path_map[display_name] = full_path
            
    def add_files(self):
        config = ConfigManager.load()
        initial_dir = config.get('last_input_dir', '')
        files = filedialog.askopenfilenames(
            title="选择CSV报告文件",
            initialdir=initial_dir if initial_dir else os.getcwd(),
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if files:
            for f in files:
                self._add_file_item(f)
            config['last_input_dir'] = os.path.dirname(files[0])
            config['last_selected_files'] = [self.file_path_map[name] for name in self.file_listbox.get(0, tk.END)]
            ConfigManager.save(config)
            
    def clear_files(self):
        self.file_listbox.delete(0, tk.END)
        self.file_path_map.clear()
        config = ConfigManager.load()
        config['last_selected_files'] = []
        ConfigManager.save(config)
    
    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END)

    def get_selected_paths(self):
        selected_indices = self.file_listbox.curselection()
        paths = []
        for idx in selected_indices:
            display_name = self.file_listbox.get(idx)
            if display_name in self.file_path_map:
                paths.append(self.file_path_map[display_name])
        return paths
        
    def generate_chart(self):
        files = self.get_selected_paths()
        if not files:
            messagebox.showwarning("警告", "请先选择数据文件")
            return
        try:
            all_data = DataLoader.load_multiple_files(files)
            if not all_data:
                messagebox.showerror("错误", "无法解析选中的文件")
                return
            chart_type = self.chart_type_var.get()
            if self.fig:
                plt.close(self.fig)
            if chart_type == "throughput":
                self._generate_throughput_chart(all_data)
            elif chart_type == "utilization":
                self._generate_utilization_chart(all_data)
            else:
                self._generate_comparison_chart(all_data)
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            toolbar = NavigationToolbar2Tk(self.canvas, self.chart_frame)
            toolbar.update()
            self.experiment_name = self.exp_name_var.get()
            self.status_var.set(f"图表生成完成 - 类型: {chart_type}")
        except Exception as e:
            messagebox.showerror("错误", f"生成图表失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def _generate_throughput_chart(self, all_data):
        self.fig, self.ax = plt.subplots(figsize=(10, 6), dpi=100)
        sliced_data = {'true': [], 'false': []}
        for data in all_data:
            config = data['config']
            for s in data['summaries']:
                if s['flow_type'] == 'eMBB':
                    point = {
                        'x': config.get('embbLoadMbps', 0),
                        'y': s.get('total_throughput', 0),
                        'slicing': config.get('slicingEnabled', False)
                    }
                    key = 'true' if point['slicing'] else 'false'
                    sliced_data[key].append(point)
                    break
        colors = {'true': '#e74c3c', 'false': '#3498db'}
        labels = {'true': '启用切片', 'false': '无切片'}
        for key in ['false', 'true']:
            if sliced_data[key]:
                sliced_data[key].sort(key=lambda p: p['x'])
                x_vals = [p['x'] for p in sliced_data[key]]
                y_vals = [p['y'] for p in sliced_data[key]]
                self.ax.plot(x_vals, y_vals, marker='o', linewidth=2.5, 
                           markersize=8, color=colors[key], label=labels[key])
                for xi, yi in zip(x_vals, y_vals):
                    self.ax.annotate(f'{yi:.1f}', (xi, yi), textcoords="offset points",
                                     xytext=(0,10), ha='center', fontsize=8)
        if sliced_data['false']:
            max_load = max([p['x'] for p in sliced_data['false']])
            self.ax.plot([0, max_load], [0, max_load], 'k--', alpha=0.3, label='理想吞吐量')
        self.ax.set_xlabel('eMBB负载 (Mbps)', fontsize=12)
        self.ax.set_ylabel('eMBB总吞吐量 (Mbps)', fontsize=12)
        self.ax.set_title('eMBB吞吐量性能对比', fontsize=14, fontweight='bold')
        self.ax.legend(fontsize=11)
        self.ax.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()
        
    def _generate_utilization_chart(self, all_data):
        self.fig, self.ax = plt.subplots(figsize=(10, 6), dpi=100)
        load_groups = {}
        for data in all_data:
            config = data['config']
            load = config.get('embbLoadMbps', 0)
            slicing = config.get('slicingEnabled', False)
            for s in data['summaries']:
                if s['flow_type'] == 'eMBB':
                    utilization = (s.get('total_throughput', 0) / load * 100) if load > 0 else 0
                    if load not in load_groups:
                        load_groups[load] = {'true': [], 'false': []}
                    key = 'true' if slicing else 'false'
                    load_groups[load][key].append(utilization)
                    break
        loads = sorted(load_groups.keys())
        categories = [f'{load}\nMbps' for load in loads]
        util_sliced = [np.mean(load_groups[load]['true']) if load_groups[load]['true'] else 0 for load in loads]
        util_no_slice = [np.mean(load_groups[load]['false']) if load_groups[load]['false'] else 0 for load in loads]
        x = np.arange(len(categories))
        width = 0.35
        bars1 = self.ax.bar(x - width/2, util_no_slice, width, label='无切片', color='#3498db')
        bars2 = self.ax.bar(x + width/2, util_sliced, width, label='启用切片', color='#e74c3c')
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                self.ax.annotate(f'{height:.1f}%',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3), textcoords="offset points",
                            ha='center', va='bottom', fontsize=8)
        self.ax.set_ylabel('资源利用率 (%)', fontsize=12)
        self.ax.set_xlabel('eMBB负载', fontsize=12)
        self.ax.set_title('eMBB资源利用率对比', fontsize=14, fontweight='bold')
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(categories)
        self.ax.legend()
        self.ax.set_ylim(0, 100)
        plt.tight_layout()
        
    def _generate_comparison_chart(self, all_data):
        self.fig, ax1 = plt.subplots(figsize=(10, 6), dpi=100)
        points = []
        for data in all_data:
            config = data['config']
            embb_summary = None
            urllc_summary = None
            for s in data['summaries']:
                if s['flow_type'] == 'eMBB':
                    embb_summary = s
                elif s['flow_type'] == 'uRLLC':
                    urllc_summary = s
            if embb_summary and urllc_summary:
                points.append({
                    'x': config.get('embbLoadMbps', 0),
                    'embb_tp': embb_summary.get('total_throughput', 0),
                    'urllc_delay': urllc_summary.get('avg_delay', 0),
                    'slicing': config.get('slicingEnabled', False)
                })
        sliced = [p for p in points if p['slicing']]
        no_sliced = [p for p in points if not p['slicing']]
        sliced.sort(key=lambda p: p['x'])
        no_sliced.sort(key=lambda p: p['x'])
        color1 = '#3498db'
        ax1.set_xlabel('eMBB负载 (Mbps)', fontsize=12)
        ax1.set_ylabel('eMBB吞吐量 (Mbps)', color=color1, fontsize=12)
        if no_sliced:
            ax1.plot([p['x'] for p in no_sliced], [p['embb_tp'] for p in no_sliced], 
                    'o-', color=color1, linewidth=2, markersize=8, label='eMBB吞吐(无切片)')
            for xi, yi in zip([p['x'] for p in no_sliced], [p['embb_tp'] for p in no_sliced]):
                ax1.annotate(f'{yi:.1f}', (xi, yi), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
        if sliced:
            ax1.plot([p['x'] for p in sliced], [p['embb_tp'] for p in sliced], 
                    's--', color=color1, linewidth=2, markersize=8, label='eMBB吞吐(切片)')
            for xi, yi in zip([p['x'] for p in sliced], [p['embb_tp'] for p in sliced]):
                ax1.annotate(f'{yi:.1f}', (xi, yi), textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
        ax1.tick_params(axis='y', labelcolor=color1)
        ax2 = ax1.twinx()
        color2 = '#e74c3c'
        ax2.set_ylabel('uRLLC平均时延 (ms)', color=color2, fontsize=12)
        if no_sliced:
            ax2.plot([p['x'] for p in no_sliced], [p['urllc_delay'] for p in no_sliced], 
                    'o-', color=color2, linewidth=2, markersize=8, label='uRLLC时延(无切片)')
            for xi, yi in zip([p['x'] for p in no_sliced], [p['urllc_delay'] for p in no_sliced]):
                ax2.annotate(f'{yi:.2f}', (xi, yi), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=8)
        if sliced:
            ax2.plot([p['x'] for p in sliced], [p['urllc_delay'] for p in sliced], 
                    's--', color=color2, linewidth=2, markersize=8, label='uRLLC时延(切片)')
            for xi, yi in zip([p['x'] for p in sliced], [p['urllc_delay'] for p in sliced]):
                ax2.annotate(f'{yi:.2f}', (xi, yi), textcoords="offset points", xytext=(0,-15), ha='center', fontsize=8)
        ax2.tick_params(axis='y', labelcolor=color2)
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        ax1.set_title('吞吐量与时延权衡分析', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, linestyle='--')
        self.ax = ax1
        plt.tight_layout()
        
    def save_current_chart(self):
        if not self.fig:
            messagebox.showwarning("警告", "请先生成图表")
            return
        self.save_figure(self.experiment_name or "效率性分析")

# ==================== 工具3: 参数敏感性分析 ====================
class ParameterSweepTool(ChartToolBase):
    def __init__(self, parent):
        super().__init__(parent, "参数敏感性分析")
        
    def create_ui(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        control_frame = ttk.LabelFrame(main_frame, text="数据与参数选择", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(control_frame, text="选择CSV文件(批量遍历结果):").grid(row=0, column=0, sticky=tk.W)
        self.file_listbox = tk.Listbox(control_frame, height=8, selectmode=tk.MULTIPLE)
        self.file_listbox.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=5)
        self.file_path_map = {}
        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=1, column=2, padx=5)
        ttk.Button(btn_frame, text="添加文件", command=self.add_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清空列表", command=self.clear_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="全部选择", command=self.select_all_files).pack(fill=tk.X, pady=2)
        settings_frame = ttk.LabelFrame(control_frame, text="热力图设置", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)
        ttk.Label(settings_frame, text="实验名称:").grid(row=0, column=0, sticky=tk.W)
        self.exp_name_var = tk.StringVar(value="参数敏感性分析")
        ttk.Entry(settings_frame, textvariable=self.exp_name_var, width=25).grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(settings_frame, text="X轴参数:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.x_param_var = tk.StringVar(value="urllcPriority")
        ttk.Combobox(settings_frame, textvariable=self.x_param_var,
                    values=["urllcPriority", "embbPriority", "urllcLoadKbps", "embbLoadMbps"],
                    state="readonly", width=15).grid(row=0, column=3, sticky=tk.W, padx=5)
        ttk.Label(settings_frame, text="Y轴参数:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.y_param_var = tk.StringVar(value="embbLoadMbps")
        ttk.Combobox(settings_frame, textvariable=self.y_param_var,
                    values=["urllcPriority", "embbPriority", "urllcLoadKbps", "embbLoadMbps"],
                    state="readonly", width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Label(settings_frame, text="颜色指标:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=5)
        self.metric_var = tk.StringVar(value="avg_delay")
        ttk.Combobox(settings_frame, textvariable=self.metric_var,
                    values=["avg_delay", "p95_delay", "total_throughput", "loss_rate"],
                    state="readonly", width=15).grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(settings_frame, text="切片类型:").grid(row=2, column=0, sticky=tk.W)
        self.slice_filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(settings_frame, text="全部", variable=self.slice_filter_var, value="all").grid(row=2, column=1, sticky=tk.W)
        ttk.Radiobutton(settings_frame, text="仅切片", variable=self.slice_filter_var, value="sliced").grid(row=2, column=2, sticky=tk.W)
        ttk.Radiobutton(settings_frame, text="仅无切片", variable=self.slice_filter_var, value="no_slice").grid(row=2, column=3, sticky=tk.W)
        action_frame = ttk.Frame(control_frame)
        action_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(action_frame, text="📊 生成热力图", command=self.generate_chart, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="💾 保存图片", command=self.save_current_chart, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="👁 预览图形", command=self.show_in_window, width=15).pack(side=tk.LEFT, padx=5)
        self.chart_frame = ttk.LabelFrame(main_frame, text="热力图预览", padding="5")
        self.chart_frame.pack(fill=tk.BOTH, expand=True)
        self.status_var = tk.StringVar(value="就绪 - 请选择包含参数遍历的CSV文件")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, pady=(5, 0))
        self.load_memory_files()
        
    def load_memory_files(self):
        config = ConfigManager.load()
        for f in config.get('last_selected_files', []):
            if os.path.exists(f):
                self._add_file_item(f)
                
    def _add_file_item(self, full_path):
        display_name = os.path.basename(full_path)
        if display_name not in self.file_listbox.get(0, tk.END):
            self.file_listbox.insert(tk.END, display_name)
            self.file_path_map[display_name] = full_path
            
    def add_files(self):
        config = ConfigManager.load()
        initial_dir = config.get('last_input_dir', '')
        files = filedialog.askopenfilenames(
            title="选择CSV报告文件",
            initialdir=initial_dir if initial_dir else os.getcwd(),
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if files:
            for f in files:
                self._add_file_item(f)
            config['last_input_dir'] = os.path.dirname(files[0])
            config['last_selected_files'] = [self.file_path_map[name] for name in self.file_listbox.get(0, tk.END)]
            ConfigManager.save(config)
            
    def clear_files(self):
        self.file_listbox.delete(0, tk.END)
        self.file_path_map.clear()
        config = ConfigManager.load()
        config['last_selected_files'] = []
        ConfigManager.save(config)

    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END)

    def get_selected_paths(self):
        selected_indices = self.file_listbox.curselection()
        paths = []
        for idx in selected_indices:
            display_name = self.file_listbox.get(idx)
            if display_name in self.file_path_map:
                paths.append(self.file_path_map[display_name])
        return paths
        
    def generate_chart(self):
        files = self.get_selected_paths()
        if not files:
            messagebox.showwarning("警告", "请先选择数据文件")
            return
        try:
            all_data = DataLoader.load_multiple_files(files)
            if not all_data:
                messagebox.showerror("错误", "无法解析选中的文件")
                return
            x_param = self.x_param_var.get()
            y_param = self.y_param_var.get()
            metric = self.metric_var.get()
            slice_filter = self.slice_filter_var.get()
            filtered_data = []
            for data in all_data:
                config = data['config']
                if slice_filter == "sliced" and not config.get('slicingEnabled'):
                    continue
                if slice_filter == "no_slice" and config.get('slicingEnabled'):
                    continue
                x_val = config.get(x_param, 0)
                y_val = config.get(y_param, 0)
                for s in data['summaries']:
                    if s['flow_type'] == 'uRLLC' and metric in ['avg_delay', 'p95_delay', 'loss_rate']:
                        filtered_data.append({'x': x_val, 'y': y_val, 'value': s.get(metric, 0)})
                        break
                    elif s['flow_type'] == 'eMBB' and metric == 'total_throughput':
                        filtered_data.append({'x': x_val, 'y': y_val, 'value': s.get(metric, 0)})
                        break
            if not filtered_data:
                messagebox.showwarning("警告", "没有符合条件的数据")
                return
            df = pd.DataFrame(filtered_data)
            pivot = df.pivot_table(values='value', index='y', columns='x', aggfunc='mean')
            if self.fig:
                plt.close(self.fig)
            self.fig, self.ax = plt.subplots(figsize=(10, 8), dpi=100)
            im = self.ax.imshow(pivot.values, cmap='RdYlGn_r', aspect='auto', interpolation='nearest')
            self.ax.set_xticks(range(len(pivot.columns)))
            self.ax.set_yticks(range(len(pivot.index)))
            self.ax.set_xticklabels([f'{x:.0f}' if x == int(x) else f'{x:.2f}' for x in pivot.columns])
            self.ax.set_yticklabels([f'{y:.0f}' if y == int(y) else f'{y:.2f}' for y in pivot.index])
            for i in range(len(pivot.index)):
                for j in range(len(pivot.columns)):
                    self.ax.text(j, i, f'{pivot.values[i, j]:.2f}',
                               ha="center", va="center", color="black", fontsize=8)
            cbar = plt.colorbar(im, ax=self.ax)
            metric_labels = {'avg_delay': '平均时延 (ms)', 'p95_delay': 'P95时延 (ms)',
                             'total_throughput': '总吞吐量 (Mbps)', 'loss_rate': '丢包率 (%)'}
            cbar.set_label(metric_labels.get(metric, metric), rotation=270, labelpad=20)
            param_labels = {'urllcPriority': 'uRLLC优先级', 'embbPriority': 'eMBB优先级',
                            'urllcGbr': 'uRLLC GBR (kbps)', 'urllcMbr': 'uRLLC MBR (kbps)',
                            'embbLoadMbps': 'eMBB负载 (Mbps)'}
            self.ax.set_xlabel(param_labels.get(x_param, x_param), fontsize=12)
            self.ax.set_ylabel(param_labels.get(y_param, y_param), fontsize=12)
            self.ax.set_title(f'{metric_labels.get(metric, metric)} 热力图\n({param_labels.get(x_param, x_param)} vs {param_labels.get(y_param, y_param)})', 
                            fontsize=14, fontweight='bold')
            plt.tight_layout()
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            toolbar = NavigationToolbar2Tk(self.canvas, self.chart_frame)
            toolbar.update()
            self.experiment_name = self.exp_name_var.get()
            self.status_var.set(f"热力图生成完成 - 数据点: {len(filtered_data)}")
        except Exception as e:
            messagebox.showerror("错误", f"生成热力图失败: {str(e)}")
            import traceback
            traceback.print_exc()
            
    def save_current_chart(self):
        if not self.fig:
            messagebox.showwarning("警告", "请先生成图表")
            return
        self.save_figure(self.experiment_name or "参数敏感性分析")

# ==================== 工具4: 流量详情分析 ====================
class FlowDetailTool(ChartToolBase):
    def __init__(self, parent):
        super().__init__(parent, "流量详情分析")

    def create_ui(self):
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 文件选择区域（多选）
        control_frame = ttk.LabelFrame(main_frame, text="数据选择（可多选，用于对比）", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="选择CSV报告文件(可多选):").grid(row=0, column=0, sticky=tk.W)
        self.file_listbox = tk.Listbox(control_frame, height=8, selectmode=tk.MULTIPLE)
        self.file_listbox.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=5)
        self.file_path_map = {}   # 显示名 -> 实际路径

        btn_frame = ttk.Frame(control_frame)
        btn_frame.grid(row=1, column=2, padx=5)
        ttk.Button(btn_frame, text="添加文件", command=self.add_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="清空列表", command=self.clear_files).pack(fill=tk.X, pady=2)
        ttk.Button(btn_frame, text="全部选择", command=self.select_all_files).pack(fill=tk.X, pady=2)

        # 图表设置区域
        settings_frame = ttk.LabelFrame(control_frame, text="图表设置", padding="5")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=tk.EW, pady=10)

        ttk.Label(settings_frame, text="实验名称:").grid(row=0, column=0, sticky=tk.W)
        self.exp_name_var = tk.StringVar(value="流量详情分析")
        ttk.Entry(settings_frame, textvariable=self.exp_name_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(settings_frame, text="图表类型:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.chart_type_var = tk.StringVar(value="cdf")
        ttk.Combobox(settings_frame, textvariable=self.chart_type_var,
                    values=["cdf", "boxplot", "bar", "scatter"],
                    state="readonly", width=15).grid(row=0, column=3, sticky=tk.W, padx=5)

        ttk.Label(settings_frame, text="分析指标:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.metric_var = tk.StringVar(value="delay_ms")
        ttk.Combobox(settings_frame, textvariable=self.metric_var,
                    values=["delay_ms", "jitter_ms", "throughput_mbps", "loss_rate"],
                    state="readonly", width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        # 分组依据（用于对比不同配置）
        ttk.Label(settings_frame, text="分组依据:").grid(row=1, column=2, sticky=tk.W, padx=(20, 0), pady=5)
        self.group_by_var = tk.StringVar(value="filename")
        group_combo = ttk.Combobox(settings_frame, textvariable=self.group_by_var,
                                   values=["filename", "gNbNum", "enableShadow", "enableMobility", "slicingEnabled"],
                                   state="readonly", width=15)
        group_combo.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        ttk.Label(settings_frame, text="注: 分组依据决定图例/对比维度", foreground="gray").grid(row=2, column=0, columnspan=4, sticky=tk.W)

        action_frame = ttk.Frame(control_frame)
        action_frame.grid(row=3, column=0, columnspan=3, pady=10)
        ttk.Button(action_frame, text="📊 生成图表", command=self.generate_chart, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="💾 保存图片", command=self.save_current_chart, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="👁 预览图形", command=self.show_in_window, width=15).pack(side=tk.LEFT, padx=5)

        # 文件信息显示区域（显示所有加载文件的摘要）
        self.info_frame = ttk.LabelFrame(main_frame, text="已加载文件摘要", padding="5")
        self.info_frame.pack(fill=tk.X, pady=(0, 10))
        self.info_text = scrolledtext.ScrolledText(self.info_frame, height=6, wrap=tk.WORD)
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # 图表预览区域
        self.chart_frame = ttk.LabelFrame(main_frame, text="图表预览", padding="5")
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="就绪 - 请选择CSV文件（可多选）进行深度分析")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, pady=(5, 0))

        self.load_memory_files()

    # ---------- 文件管理方法 ----------
    def load_memory_files(self):
        config = ConfigManager.load()
        for f in config.get('last_selected_files', []):
            if os.path.exists(f):
                self._add_file_item(f)
        self.update_info_text()

    def _add_file_item(self, full_path):
        display_name = os.path.basename(full_path)
        if display_name not in self.file_listbox.get(0, tk.END):
            self.file_listbox.insert(tk.END, display_name)
            self.file_path_map[display_name] = full_path

    def add_files(self):
        config = ConfigManager.load()
        initial_dir = config.get('last_input_dir', '')
        files = filedialog.askopenfilenames(
            title="选择CSV报告文件",
            initialdir=initial_dir if initial_dir else os.getcwd(),
            filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
        )
        if files:
            for f in files:
                self._add_file_item(f)
            config['last_input_dir'] = os.path.dirname(files[0])
            config['last_selected_files'] = [self.file_path_map[name] for name in self.file_listbox.get(0, tk.END)]
            ConfigManager.save(config)
            self.update_info_text()

    def clear_files(self):
        self.file_listbox.delete(0, tk.END)
        self.file_path_map.clear()
        config = ConfigManager.load()
        config['last_selected_files'] = []
        ConfigManager.save(config)
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(tk.END, "未加载任何文件")

    def select_all_files(self):
        self.file_listbox.select_set(0, tk.END)

    def get_selected_paths(self):
        selected_indices = self.file_listbox.curselection()
        paths = []
        for idx in selected_indices:
            display_name = self.file_listbox.get(idx)
            if display_name in self.file_path_map:
                paths.append(self.file_path_map[display_name])
        return paths

    def update_info_text(self):
        """更新文件信息显示区域"""
        self.info_text.delete(1.0, tk.END)
        all_paths = list(self.file_path_map.values())
        if not all_paths:
            self.info_text.insert(tk.END, "未加载任何文件")
            return
        for fp in all_paths:
            try:
                data = DataLoader.parse_csv(fp)
                config = data['config']
                summaries = data['summaries']
                info = f"📄 {os.path.basename(fp)}\n"
                info += f"   切片启用: {'是' if config.get('slicingEnabled') else '否'}\n"
                info += f"   gNB数: {config.get('gNbNum', 1)}, 阴影: {config.get('enableShadow', False)}, 移动: {config.get('enableMobility', False)}"
                if config.get('enableMobility'):
                    info += f"({config.get('ueSpeed',0)}m/s)"
                info += "\n"
                for s in summaries:
                    info += f"   {s['flow_type']}: 吞吐={s['total_throughput']:.2f}Mbps, 时延={s['avg_delay']:.3f}ms\n"
                self.info_text.insert(tk.END, info + "\n")
            except Exception as e:
                self.info_text.insert(tk.END, f"❌ {os.path.basename(fp)}: 解析失败 - {str(e)}\n\n")

    # ---------- 图表生成主入口 ----------
    def generate_chart(self):
        files = self.get_selected_paths()
        if not files:
            messagebox.showwarning("警告", "请先选择至少一个数据文件")
            return
        try:
            all_data = []
            for fp in files:
                try:
                    all_data.append(DataLoader.parse_csv(fp))
                except Exception as e:
                    messagebox.showerror("错误", f"解析文件 {os.path.basename(fp)} 失败: {str(e)}")
                    return
            chart_type = self.chart_type_var.get()
            metric = self.metric_var.get()
            group_by = self.group_by_var.get()

            if self.fig:
                plt.close(self.fig)
            if chart_type == "cdf":
                self._generate_cdf(all_data, metric, group_by)
            elif chart_type == "boxplot":
                self._generate_boxplot(all_data, metric, group_by)
            elif chart_type == "bar":
                self._generate_bar(all_data, group_by)
            else:  # scatter
                self._generate_scatter(all_data, group_by)

            # 清空并显示新图表
            for widget in self.chart_frame.winfo_children():
                widget.destroy()
            self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            toolbar = NavigationToolbar2Tk(self.canvas, self.chart_frame)
            toolbar.update()
            self.experiment_name = self.exp_name_var.get()
            self.status_var.set(f"图表生成完成 - 类型: {chart_type}, 文件数: {len(all_data)}")
        except Exception as e:
            messagebox.showerror("错误", f"生成图表失败: {str(e)}")
            import traceback
            traceback.print_exc()

    # ---------- 图表绘制函数（支持多文件对比） ----------
    def _get_group_label(self, data, group_by):
        """根据分组依据生成标签"""
        config = data['config']
        if group_by == "filename":
            return os.path.basename(data['filepath'])
        elif group_by == "gNbNum":
            return f"gNB={config.get('gNbNum', 1)}"
        elif group_by == "enableShadow":
            return "阴影开启" if config.get('enableShadow', False) else "阴影关闭"
        elif group_by == "enableMobility":
            mob = config.get('enableMobility', False)
            speed = config.get('ueSpeed', 0)
            return f"移动{mob}({speed}m/s)" if mob else "静态"
        elif group_by == "slicingEnabled":
            return "切片启用" if config.get('slicingEnabled', False) else "无切片"
        else:
            return os.path.basename(data['filepath'])

    def _generate_cdf(self, all_data, metric, group_by):
        self.fig, self.ax = plt.subplots(figsize=(10, 6), dpi=100)
        metric_labels = {'delay_ms': '时延 (ms)', 'jitter_ms': '抖动 (ms)',
                         'throughput_mbps': '吞吐量 (Mbps)', 'loss_rate': '丢包率 (%)'}
        colors = plt.cm.tab10(np.linspace(0, 1, len(all_data)))
        for idx, data in enumerate(all_data):
            flows = data['flows']
            # 根据 metric 提取值（默认使用 uRLLC，也可以让用户选择流类型，简化起见用 uRLLC）
            values = [f[metric] for f in flows if f['flow_type'] == 'uRLLC' and metric in f]
            if not values:
                # 若 uRLLC 无数据，尝试 eMBB
                values = [f[metric] for f in flows if f['flow_type'] == 'eMBB' and metric in f]
            if values:
                sorted_data = np.sort(values)
                yvals = np.arange(len(sorted_data)) / float(len(sorted_data) - 1) * 100
                label = self._get_group_label(data, group_by)
                self.ax.plot(sorted_data, yvals, linewidth=2.5, label=label, color=colors[idx])
            else:
                print(f"警告: {data['filename']} 中无有效 {metric} 数据")
        self.ax.set_xlabel(metric_labels.get(metric, metric), fontsize=12)
        self.ax.set_ylabel('CDF (%)', fontsize=12)
        self.ax.set_title(f'{metric_labels.get(metric, metric)} 累积分布对比', fontsize=14, fontweight='bold')
        self.ax.legend(fontsize=10, loc='best')
        self.ax.grid(True, alpha=0.3, linestyle='--')
        self.ax.set_ylim(0, 100)
        plt.tight_layout()

    def _generate_boxplot(self, all_data, metric, group_by):
        self.fig, self.ax = plt.subplots(figsize=(10, 6), dpi=100)
        metric_labels = {'delay_ms': '时延 (ms)', 'jitter_ms': '抖动 (ms)',
                         'throughput_mbps': '吞吐量 (Mbps)', 'loss_rate': '丢包率 (%)'}
        data_to_plot = []
        labels = []
        for data in all_data:
            flows = data['flows']
            values = [f[metric] for f in flows if f['flow_type'] == 'uRLLC' and metric in f]
            if not values:
                values = [f[metric] for f in flows if f['flow_type'] == 'eMBB' and metric in f]
            if values:
                data_to_plot.append(values)
                labels.append(self._get_group_label(data, group_by))
        if not data_to_plot:
            raise ValueError("无有效数据")
        bp = self.ax.boxplot(data_to_plot, labels=labels, patch_artist=True, showmeans=True)
        # 颜色自动分配
        colors = plt.cm.tab10(np.linspace(0, 1, len(data_to_plot)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)
        self.ax.set_ylabel(metric_labels.get(metric, metric), fontsize=12)
        self.ax.set_title(f'{metric_labels.get(metric, metric)} 分布对比', fontsize=14, fontweight='bold')
        self.ax.grid(True, axis='y', alpha=0.3)
        plt.xticks(rotation=15, ha='right')
        plt.tight_layout()

    def _generate_bar(self, all_data, group_by):
        """柱状图：对比每个文件的 uRLLC 时延 和 eMBB 吞吐量（双柱）"""
        self.fig, self.ax = plt.subplots(figsize=(10, 6), dpi=100)
        labels = []
        urllc_delays = []
        embb_throughputs = []
        for data in all_data:
            summaries = data['summaries']
            urllc_delay = None
            embb_tp = None
            for s in summaries:
                if s['flow_type'] == 'uRLLC':
                    urllc_delay = s.get('avg_delay', 0)
                elif s['flow_type'] == 'eMBB':
                    embb_tp = s.get('total_throughput', 0)
            if urllc_delay is not None and embb_tp is not None:
                labels.append(self._get_group_label(data, group_by))
                urllc_delays.append(urllc_delay)
                embb_throughputs.append(embb_tp)
        if not labels:
            raise ValueError("缺少有效摘要数据")
        x = np.arange(len(labels))
        width = 0.35
        ax2 = self.ax.twinx()
        bars1 = self.ax.bar(x - width/2, embb_throughputs, width, label='eMBB吞吐量 (Mbps)', color='#3498db', alpha=0.8)
        bars2 = ax2.bar(x + width/2, urllc_delays, width, label='uRLLC平均时延 (ms)', color='#e74c3c', alpha=0.8)
        self.ax.set_ylabel('eMBB吞吐量 (Mbps)', color='#3498db', fontsize=12)
        ax2.set_ylabel('uRLLC时延 (ms)', color='#e74c3c', fontsize=12)
        self.ax.set_title('不同场景性能对比', fontsize=14, fontweight='bold')
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(labels, rotation=15, ha='right')
        # 添加数值标签
        for bar in bars1:
            height = bar.get_height()
            self.ax.annotate(f'{height:.1f}', xy=(bar.get_x() + bar.get_width()/2, height),
                             xytext=(0,3), textcoords="offset points", ha='center', fontsize=8, color='#3498db')
        for bar in bars2:
            height = bar.get_height()
            ax2.annotate(f'{height:.2f}', xy=(bar.get_x() + bar.get_width()/2, height),
                         xytext=(0,3), textcoords="offset points", ha='center', fontsize=8, color='#e74c3c')
        self.ax.legend(loc='upper left')
        ax2.legend(loc='upper right')
        plt.tight_layout()

    def _generate_scatter(self, all_data, group_by):
        """散点图：时延 vs 吞吐量，不同颜色代表不同文件"""
        self.fig, self.ax = plt.subplots(figsize=(10, 6), dpi=100)
        colors = plt.cm.tab10(np.linspace(0, 1, len(all_data)))
        for idx, data in enumerate(all_data):
            flows = data['flows']
            urllc_points = [(f['delay_ms'], f['throughput_mbps']) for f in flows if f['flow_type'] == 'uRLLC']
            embb_points = [(f['delay_ms'], f['throughput_mbps']) for f in flows if f['flow_type'] == 'eMBB']
            label = self._get_group_label(data, group_by)
            if urllc_points:
                delays, tps = zip(*urllc_points)
                self.ax.scatter(delays, tps, label=f"{label} (uRLLC)", alpha=0.6, s=80, color=colors[idx], marker='o')
            if embb_points:
                delays, tps = zip(*embb_points)
                self.ax.scatter(delays, tps, label=f"{label} (eMBB)", alpha=0.6, s=80, color=colors[idx], marker='s')
        self.ax.set_xlabel('时延 (ms)', fontsize=12)
        self.ax.set_ylabel('吞吐量 (Mbps)', fontsize=12)
        self.ax.set_title('时延-吞吐量散点分布对比', fontsize=14, fontweight='bold')
        self.ax.legend(fontsize=9, loc='best', ncol=2)
        self.ax.grid(True, alpha=0.3, linestyle='--')
        plt.tight_layout()

    def save_current_chart(self):
        if not self.fig:
            messagebox.showwarning("警告", "请先生成图表")
            return
        self.save_figure(self.experiment_name or "流量详情分析")

# ==================== 仿真 GUI 部分 ====================
def find_ns3_root(start_path=None):
    if start_path is None:
        start_path = os.path.dirname(os.path.abspath(__file__))
    current = start_path
    while current != os.path.dirname(current):
        if os.path.exists(os.path.join(current, 'ns3')) or os.path.exists(os.path.join(current, 'waf')):
            return current
        current = os.path.dirname(current)
    return None

class ParamConfigFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.widgets = {}
        canvas = tk.Canvas(self, borderwidth=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件，使canvas可滚动
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
            canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")
        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        
        PARAM_META = {
            "enableSlicing": {"type": "bool", "group": "实验控制"},
            "schedulerType": {"type": "combo", "options": ["RR", "PF", "Qos"], "group": "实验控制"},
            "enableLcQos": {"type": "bool", "group": "实验控制"},
            "embbUeNum": {"type": "int", "min": 1, "max": 50, "group": "切片负载规模"},
            "urllcUeNum": {"type": "int", "min": 1, "max": 20, "group": "切片负载规模"},
            "urllcPriority": {"type": "int", "min": 1, "max": 127, "group": "切片权重/优先级"},
            "embbPriority": {"type": "int", "min": 1, "max": 127, "group": "切片权重/优先级"},
            "urllcGbr": {"type": "float", "min": 0, "max": 10000, "group": "切片权重/优先级"},
            "urllcMbr": {"type": "float", "min": 0, "max": 10000, "group": "切片权重/优先级"},
            "urllcLoad": {"type": "float", "min": 0, "max": 1e6, "group": "业务负载强度"},
            "embbLoad": {"type": "float", "min": 0, "max": 10000, "group": "业务负载强度"},
            "urllcPacketSize": {"type": "int", "min": 32, "max": 2000, "group": "业务特征"},
            "embbPacketSize": {"type": "int", "min": 500, "max": 2000, "group": "业务特征"},
            "bandwidth": {"type": "combo", "options": [20e6, 40e6, 100e6], "group": "无线环境"},
            "numerology": {"type": "combo", "options": [0, 1, 2, 3, 4], "group": "无线环境"},
            "enableShadow": {"type": "bool", "group": "无线环境"},
            "enableMobility": {"type": "bool", "group": "无线环境"},
            "ueSpeed": {"type": "float", "min": 0, "max": 10, "group": "无线环境"},
            "gNbNum": {"type": "int", "min": 1, "max": 7, "group": "无线环境"},
            "simTag": {"type": "str", "group": "输出设置"},
            "outputDir": {"type": "str", "group": "输出设置"}
        }
        DEFAULT_PARAMS = {
            "enableSlicing": True, "schedulerType": "Qos", "enableLcQos": True,
            "embbUeNum": 4, "urllcUeNum": 2, "urllcPriority": 1, "embbPriority": 20,
            "urllcGbr": 400.0, "urllcMbr": 800.0, "urllcLoad": 200000.0, "embbLoad": 5000.0,
            "urllcPacketSize": 100, "embbPacketSize": 1252, "bandwidth": 100e6, "numerology": 4,
            "enableShadow": False, "enableMobility": False, "ueSpeed": 1.0, "gNbNum": 1,
            "simTag": "default", "outputDir": "./results/"
        }
        groups = {}
        for key, meta in PARAM_META.items():
            groups.setdefault(meta["group"], []).append(key)
        row = 0
        for group_name, keys in groups.items():
            labelframe = ttk.LabelFrame(scrollable_frame, text=group_name)
            labelframe.grid(row=row, column=0, padx=10, pady=5, sticky="ew")
            labelframe.columnconfigure(1, weight=1)
            for i, key in enumerate(keys):
                meta = PARAM_META[key]
                default_val = DEFAULT_PARAMS[key]
                label_text = key
                if meta["type"] == "bool":
                    label_text += " (布尔)"
                elif meta["type"] == "int":
                    label_text += f" (整数 {meta.get('min','')}-{meta.get('max','')})"
                elif meta["type"] == "float":
                    label_text += f" (浮点数 {meta.get('min','')}-{meta.get('max','')})"
                elif meta["type"] == "combo":
                    opt_str = ",".join(str(o) for o in meta["options"])
                    label_text += f" (选项: {opt_str})"
                else:
                    label_text += " (字符串)"
                label = ttk.Label(labelframe, text=label_text + ":")
                label.grid(row=i, column=0, padx=5, pady=2, sticky="w")
                if meta["type"] == "bool":
                    var = tk.BooleanVar(value=default_val)
                    widget = ttk.Checkbutton(labelframe, variable=var)
                elif meta["type"] == "combo":
                    var = tk.StringVar(value=str(default_val))
                    widget = ttk.Combobox(labelframe, textvariable=var, values=meta["options"], state="readonly")
                elif meta["type"] == "int":
                    var = tk.IntVar(value=default_val)
                    widget = ttk.Spinbox(labelframe, from_=meta.get("min",0), to=meta.get("max",100000), textvariable=var)
                elif meta["type"] == "float":
                    var = tk.DoubleVar(value=default_val)
                    widget = ttk.Entry(labelframe, textvariable=var)
                else:
                    var = tk.StringVar(value=str(default_val))
                    widget = ttk.Entry(labelframe, textvariable=var)
                widget.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
                self.widgets[key] = {"var": var, "widget": widget, "meta": meta}
            row += 1
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.grid(row=row, column=0, pady=10)
        ttk.Button(btn_frame, text="恢复默认值", command=self.reset_defaults).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="加载配置", command=self.app.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="保存配置", command=self.app.save_config).pack(side=tk.LEFT, padx=5)
        self.defaults = DEFAULT_PARAMS

    def get_params(self):
        params = {}
        for key, item in self.widgets.items():
            var = item["var"]
            meta = item["meta"]
            if meta["type"] == "bool":
                params[key] = var.get()
            elif meta["type"] == "int":
                params[key] = var.get()
            elif meta["type"] == "float":
                try:
                    params[key] = float(var.get())
                except:
                    params[key] = self.defaults[key]
            else:
                val = var.get()
                if meta["type"] == "combo":
                    if isinstance(self.defaults[key], float):
                        try:
                            val = float(val)
                        except:
                            pass
                    elif isinstance(self.defaults[key], int):
                        try:
                            val = int(float(val))
                        except:
                            pass
                params[key] = val
        return params

    def set_params(self, params):
        for key, value in params.items():
            if key in self.widgets:
                var = self.widgets[key]["var"]
                meta = self.widgets[key]["meta"]
                if meta["type"] == "bool":
                    var.set(bool(value))
                elif meta["type"] in ("int", "float"):
                    var.set(value)
                else:
                    var.set(str(value))

    def reset_defaults(self):
        self.set_params(self.defaults)

class RunControlFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        single_frame = ttk.LabelFrame(self, text="单次仿真")
        single_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        single_frame.columnconfigure(0, weight=1)
        ttk.Label(single_frame, text="命令行预览:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.cmd_preview = tk.Text(single_frame, height=3, wrap=tk.WORD)
        self.cmd_preview.grid(row=1, column=0, padx=5, pady=2, sticky="ew")
        self.cmd_preview.config(state=tk.DISABLED)
        btn_single_frame = ttk.Frame(single_frame)
        btn_single_frame.grid(row=2, column=0, pady=5)
        self.btn_run = ttk.Button(btn_single_frame, text="▶ 开始仿真", command=self.start_single_sim)
        self.btn_run.pack(side=tk.LEFT, padx=5)
        self.btn_stop = ttk.Button(btn_single_frame, text="■ 停止", command=self.stop_sim, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_single_frame, text="刷新预览", command=self.update_cmd_preview).pack(side=tk.LEFT, padx=5)
        batch_frame = ttk.LabelFrame(self, text="批量遍历 (单变量)")
        batch_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        batch_frame.columnconfigure(1, weight=1)
        ttk.Label(batch_frame, text="说明: 批量遍历时，除了被遍历的参数，其他所有参数均使用当前“参数配置”页中的值。",
                  foreground="blue").grid(row=0, column=0, columnspan=6, padx=5, pady=2, sticky="w")
        ttk.Label(batch_frame, text="遍历参数:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.batch_var_combo = ttk.Combobox(batch_frame, state="readonly")
        self.batch_var_combo.grid(row=1, column=1, padx=5, pady=2, sticky="w")
        numeric_keys = ["embbUeNum", "urllcUeNum", "urllcPriority", "embbPriority", "urllcGbr", "urllcMbr", "urllcLoad", "embbLoad", "urllcPacketSize", "embbPacketSize", "gNbNum"]
        self.batch_var_combo['values'] = numeric_keys
        if numeric_keys:
            self.batch_var_combo.current(0)
        ttk.Label(batch_frame, text="起始值:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.batch_start = ttk.Entry(batch_frame, width=10)
        self.batch_start.grid(row=2, column=1, padx=5, pady=2, sticky="w")
        ttk.Label(batch_frame, text="结束值:").grid(row=2, column=2, padx=5, pady=2, sticky="w")
        self.batch_end = ttk.Entry(batch_frame, width=10)
        self.batch_end.grid(row=2, column=3, padx=5, pady=2, sticky="w")
        ttk.Label(batch_frame, text="步长:").grid(row=2, column=4, padx=5, pady=2, sticky="w")
        self.batch_step = ttk.Entry(batch_frame, width=10)
        self.batch_step.grid(row=2, column=5, padx=5, pady=2, sticky="w")
        btn_batch_frame = ttk.Frame(batch_frame)
        btn_batch_frame.grid(row=3, column=0, columnspan=6, pady=5)
        ttk.Button(btn_batch_frame, text="生成命令列表", command=self.generate_batch_commands).pack(side=tk.LEFT, padx=5)
        self.btn_batch_run = ttk.Button(btn_batch_frame, text="▶ 执行批量仿真", command=self.start_batch_sim, state=tk.DISABLED)
        self.btn_batch_run.pack(side=tk.LEFT, padx=5)
        log_frame = ttk.LabelFrame(self, text="运行日志")
        log_frame.grid(row=2, column=0, padx=10, pady=5, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        ttk.Button(log_frame, text="清空日志", command=self.clear_log).grid(row=1, column=0, pady=2)
        self.batch_commands = []
        self.update_cmd_preview()

    def update_cmd_preview(self):
        params = self.app.param_frame.get_params()
        cmd = self.app.get_command_line(params)
        self.cmd_preview.config(state=tk.NORMAL)
        self.cmd_preview.delete(1.0, tk.END)
        self.cmd_preview.insert(1.0, cmd)
        self.cmd_preview.config(state=tk.DISABLED)

    def log_message(self, msg):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.update()

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def start_single_sim(self):
        if self.app.current_process is not None:
            messagebox.showwarning("警告", "已有仿真正在运行")
            return
        params = self.app.param_frame.get_params()
        cmd = self.app.get_command_line(params)
        self.run_command(cmd)

    def run_command(self, cmd):
        self.app.stop_requested = False
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_batch_run.config(state=tk.DISABLED)
        self.log_message(f"[执行] {cmd.strip()}")
        def target():
            try:
                ns3_dir = self.app.ns3_root
                ns3_script = os.path.join(ns3_dir, 'ns3')
                if os.path.exists(ns3_script) and not os.access(ns3_script, os.X_OK):
                    os.chmod(ns3_script, os.stat(ns3_script).st_mode | stat.S_IEXEC)
                self.app.current_process = subprocess.Popen(
                    cmd, shell=True, cwd=ns3_dir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                for line in iter(self.app.current_process.stdout.readline, ''):
                    if self.app.stop_requested:
                        self.app.current_process.terminate()
                        break
                    self.log_message(line.rstrip())
                self.app.current_process.wait()
                if self.app.current_process.returncode == 0:
                    self.log_message("[完成] 仿真成功结束")
                    self.app.result_frame.refresh_file_list()
                else:
                    self.log_message(f"[错误] 仿真异常退出，返回码: {self.app.current_process.returncode}")
            except Exception as e:
                self.log_message(f"[异常] {e}")
            finally:
                self.app.current_process = None
                self.btn_run.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.DISABLED)
                if self.batch_commands:
                    self.btn_batch_run.config(state=tk.NORMAL)
        threading.Thread(target=target, daemon=True).start()

    def stop_sim(self):
        if self.app.current_process:
            self.app.stop_requested = True
            self.log_message("[用户] 正在终止仿真...")

    def generate_batch_commands(self):
        var_name = self.batch_var_combo.get()
        if not var_name:
            messagebox.showerror("错误", "请选择遍历参数")
            return
        try:
            start = float(self.batch_start.get())
            end = float(self.batch_end.get())
            step = float(self.batch_step.get())
        except ValueError:
            messagebox.showerror("错误", "起始/结束/步长必须是数字")
            return
        if step <= 0:
            messagebox.showerror("错误", "步长必须大于0")
            return
        self.batch_commands = []
        base_params = self.app.param_frame.get_params()
        current = start
        is_int = isinstance(base_params.get(var_name, 0), int)
        self.log_message(f"[批量] 生成遍历命令: {var_name} 从 {start} 到 {end} 步长 {step}")
        idx = 1
        while current <= end + 1e-9:
            params = base_params.copy()
            if is_int:
                val = int(round(current))
                params[var_name] = val
            else:
                val = current
                params[var_name] = val
            if is_int:
                val_str = str(val)
            else:
                val_str = f"{val:.6g}".replace('.', '_')
            extra_tag = f"{var_name}_{idx}_{val_str}"
            cmd = self.app.get_command_line(params, extra_tag=extra_tag)
            self.batch_commands.append((extra_tag, cmd))
            self.log_message(f"  {extra_tag}: {cmd.strip()}")
            current += step
            idx += 1
        self.btn_batch_run.config(state=tk.NORMAL)
        messagebox.showinfo("完成", f"已生成 {len(self.batch_commands)} 条命令")

    def start_batch_sim(self):
        if not self.batch_commands:
            return
        if self.app.current_process is not None:
            messagebox.showwarning("警告", "已有仿真正在运行")
            return
        def run_batch():
            self.btn_run.config(state=tk.DISABLED)
            self.btn_batch_run.config(state=tk.DISABLED)
            for idx, (tag, cmd) in enumerate(self.batch_commands):
                if self.app.stop_requested:
                    self.log_message("[批量] 用户终止批量运行")
                    break
                self.log_message(f"[批量 {idx+1}/{len(self.batch_commands)}] 开始 {tag}")
                try:
                    ns3_dir = self.app.ns3_root
                    ns3_script = os.path.join(ns3_dir, 'ns3')
                    if os.path.exists(ns3_script) and not os.access(ns3_script, os.X_OK):
                        os.chmod(ns3_script, os.stat(ns3_script).st_mode | stat.S_IEXEC)
                    proc = subprocess.Popen(
                        cmd, shell=True, cwd=ns3_dir,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True
                    )
                    for line in proc.stdout:
                        if self.app.stop_requested:
                            proc.terminate()
                            break
                        self.log_message(line.rstrip())
                    proc.wait()
                    if proc.returncode == 0:
                        self.log_message(f"[批量 {idx+1}] {tag} 完成")
                        self.app.result_frame.refresh_file_list()
                    else:
                        self.log_message(f"[批量 {idx+1}] {tag} 失败，返回码 {proc.returncode}")
                except Exception as e:
                    self.log_message(f"[批量异常] {e}")
                time.sleep(1)
            self.log_message("[批量] 全部任务执行完毕")
            self.btn_run.config(state=tk.NORMAL)
            self.btn_batch_run.config(state=tk.NORMAL)
            self.app.stop_requested = False
        self.app.stop_requested = False
        threading.Thread(target=run_batch, daemon=True).start()

class ResultViewerFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        # 上下分离 TXT 和 CSV 列表
        txt_frame = ttk.LabelFrame(left_frame, text="TXT 统计文件")
        txt_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        txt_list_frame = ttk.Frame(txt_frame)
        txt_list_frame.pack(fill=tk.BOTH, expand=True)
        txt_scroll = ttk.Scrollbar(txt_list_frame)
        txt_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_listbox = tk.Listbox(txt_list_frame, yscrollcommand=txt_scroll.set)
        self.txt_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        txt_scroll.config(command=self.txt_listbox.yview)
        csv_frame = ttk.LabelFrame(left_frame, text="CSV 报告文件")
        csv_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        csv_list_frame = ttk.Frame(csv_frame)
        csv_list_frame.pack(fill=tk.BOTH, expand=True)
        csv_scroll = ttk.Scrollbar(csv_list_frame)
        csv_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.csv_listbox = tk.Listbox(csv_list_frame, yscrollcommand=csv_scroll.set)
        self.csv_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        csv_scroll.config(command=self.csv_listbox.yview)
        btn_left = ttk.Frame(left_frame)
        btn_left.pack(pady=5)
        ttk.Button(btn_left, text="刷新列表", command=self.refresh_file_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_left, text="打开目录", command=self.open_output_dir).pack(side=tk.LEFT, padx=2)
        ttk.Label(right_frame, text="文件内容预览").pack(pady=2)
        self.content_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD)
        self.content_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.file_paths = {}  # 仍使用单一映射，通过显示名区分
        self.txt_listbox.bind('<<ListboxSelect>>', lambda e: self.on_file_select(e, self.txt_listbox))
        self.csv_listbox.bind('<<ListboxSelect>>', lambda e: self.on_file_select(e, self.csv_listbox))
        self.refresh_file_list()

    def get_output_dir(self):
        params = self.app.param_frame.get_params()
        rel_path = params.get("outputDir", "./results/")
        if os.path.isabs(rel_path):
            return rel_path
        else:
            return os.path.join(self.app.ns3_root, rel_path)

    def refresh_file_list(self):
        self.txt_listbox.delete(0, tk.END)
        self.csv_listbox.delete(0, tk.END)
        self.file_paths.clear()
        output_dir = self.get_output_dir()
        os.makedirs(output_dir, exist_ok=True)
        txt_files = glob.glob(os.path.join(output_dir, "*_stats.txt"))
        csv_files = glob.glob(os.path.join(output_dir, "*_report.csv"))
        # 按文件名排序
        txt_files.sort(key=lambda x: os.path.basename(x))
        csv_files.sort(key=lambda x: os.path.basename(x))
        for f in txt_files:
            basename = os.path.basename(f)
            display = f"[TXT] {basename}"
            self.txt_listbox.insert(tk.END, display)
            self.file_paths[display] = f
        for f in csv_files:
            basename = os.path.basename(f)
            display = f"[CSV] {basename}"
            self.csv_listbox.insert(tk.END, display)
            self.file_paths[display] = f

    def open_output_dir(self):
        output_dir = self.get_output_dir()
        os.makedirs(output_dir, exist_ok=True)
        subprocess.Popen(["xdg-open", output_dir])

    def on_file_select(self, event, listbox):
        selection = listbox.curselection()
        if not selection:
            return
        display_name = listbox.get(selection[0])
        filepath = self.file_paths.get(display_name)
        if not filepath or not os.path.exists(filepath):
            self.content_text.config(state=tk.NORMAL)
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(1.0, "文件不存在或已被删除")
            self.content_text.config(state=tk.DISABLED)
            return
        self.content_text.config(state=tk.NORMAL)
        self.content_text.delete(1.0, tk.END)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            self.content_text.insert(1.0, content)
        except Exception as e:
            self.content_text.insert(1.0, f"读取文件失败: {e}")
        self.content_text.config(state=tk.DISABLED)

class SliceSimulatorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("5G网络切片仿真配置与数据分析平台")
        self.geometry("1000x700")
        self.resizable(True, True)
        self.ns3_root = find_ns3_root()
        if self.ns3_root is None:
            self.ns3_root = os.getcwd()
            messagebox.showwarning("警告", "未自动检测到NS-3根目录，使用当前目录。请确保能执行./ns3或./waf命令。")
        else:
            print(f"检测到NS-3根目录: {self.ns3_root}")
        self.ns3_program = "my-slice-auto"
        self.current_process = None
        self.stop_requested = False
        self.create_menu()
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.param_frame = ParamConfigFrame(self.notebook, self)
        self.run_frame = RunControlFrame(self.notebook, self)
        self.result_frame = ResultViewerFrame(self.notebook, self)
        # 新增数据分析标签页（取代原菜单和底部按钮）
        self.analyzer_frame = self.create_analyzer_tab()
        self.notebook.add(self.param_frame, text="参数配置")
        self.notebook.add(self.run_frame, text="运行控制")
        self.notebook.add(self.result_frame, text="结果查看")
        self.notebook.add(self.analyzer_frame, text="数据分析工具")

    def create_analyzer_tab(self):
        """创建数据分析工具标签页，包含四个卡片入口"""
        frame = ttk.Frame(self.notebook, padding="20")
        header = ttk.Frame(frame)
        header.pack(fill=tk.X, pady=(0,20))
        ttk.Label(header, text="5G网络切片仿真数据分析平台", font=('Microsoft YaHei', 14, 'bold')).pack()
        ttk.Label(header, text="选择分析工具", font=('Microsoft YaHei', 11)).pack(pady=(5,0))
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X)
        tools_frame = ttk.Frame(frame)
        tools_frame.pack(fill=tk.BOTH, expand=True)
        def create_card(parent, title, desc, command):
            card = ttk.Frame(parent, relief=tk.RIDGE, borderwidth=2)
            card.pack(fill=tk.X, pady=5)
            content = ttk.Frame(card, padding="15")
            content.pack(fill=tk.BOTH, expand=True)
            left = ttk.Frame(content)
            left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ttk.Label(left, text=title, font=('Microsoft YaHei', 11, 'bold')).pack(anchor=tk.W)
            ttk.Label(left, text=desc, font=('Microsoft YaHei', 9), foreground="#555").pack(anchor=tk.W, pady=(5,0))
            ttk.Button(content, text="打开工具", command=command, width=12).pack(side=tk.RIGHT, padx=10)
            # 点击卡片任意位置也可打开
            for w in (card, content, left):
                w.bind('<Button-1>', lambda e: command())
        create_card(tools_frame, "🔒 隔离性分析工具",
                   "分析uRLLC时延/抖动随eMBB负载变化，验证切片隔离保护效果",
                   self.open_isolation_tool)
        create_card(tools_frame, "⚡ 效率性分析工具",
                   "分析eMBB吞吐量与资源利用率，评估切片整体资源效率",
                   self.open_efficiency_tool)
        create_card(tools_frame, "🌡️ 参数敏感性分析",
                   "热力图展示不同参数组合下的性能，辅助寻找最优配置",
                   self.open_parameter_tool)
        create_card(tools_frame, "📈 流量详情分析",
                   "CDF分布、箱线图、散点图，深度分析单个仿真文件的流量特征",
                   self.open_flow_tool)
        return frame

    def create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="加载配置...", command=self.load_config)
        file_menu.add_command(label="保存配置...", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)
        # 移除原有的“数据分析”菜单，将其功能移至标签页
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="参数说明", command=self.show_param_help)
        help_menu.add_command(label="工具说明", command=self.show_tool_help)
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=self.show_about)

    def load_config(self):
        filepath = filedialog.askopenfilename(title="加载配置文件", filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")])
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    params = json.load(f)
                self.param_frame.set_params(params)
                messagebox.showinfo("成功", "配置加载完成")
            except Exception as e:
                messagebox.showerror("错误", f"加载失败: {e}")

    def save_config(self):
        filepath = filedialog.asksaveasfilename(title="保存配置文件", defaultextension=".json", filetypes=[("JSON文件", "*.json")])
        if filepath:
            try:
                params = self.param_frame.get_params()
                with open(filepath, 'w') as f:
                    json.dump(params, f, indent=4)
                messagebox.showinfo("成功", f"配置已保存至 {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")

    def show_param_help(self):
        help_win = tk.Toplevel(self)
        help_win.title("参数说明")
        help_win.geometry("700x500")
        text = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=('Microsoft YaHei', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        content = """
【仿真参数说明】

1. 实验控制
   - enableSlicing: 是否启用网络切片功能 (true/false)
   - schedulerType: 调度算法类型 (RR轮询 / PF比例公平 / Qos服务质量)
   - enableLcQos: 是否启用逻辑信道QoS支持

2. 切片负载规模
   - embbUeNum: eMBB切片用户数量
   - urllcUeNum: uRLLC切片用户数量

3. 切片权重/优先级
   - urllcPriority / embbPriority: 优先级值，越小优先级越高 (1~127)
   - urllcGbr: uRLLC保证比特率 (kbps)
   - urllcMbr: uRLLC最大比特率 (kbps)

4. 业务负载强度
   - urllcLoad: uRLLC业务负载 (kbps)
   - embbLoad: eMBB业务负载 (Mbps)

5. 业务特征
   - urllcPacketSize / embbPacketSize: 数据包大小 (字节)

6. 无线环境
   - bandwidth: 系统带宽 (Hz)
   - numerology: 5G NR子载波间隔配置 (0~4)

7. 输出设置
   - simTag: 仿真标识，用于区分不同运行
   - outputDir: 结果输出目录（相对或绝对路径）
"""
        text.insert(tk.END, content)
        text.config(state=tk.DISABLED)

    def show_tool_help(self):
        help_win = tk.Toplevel(self)
        help_win.title("工具说明")
        help_win.geometry("700x500")
        text = scrolledtext.ScrolledText(help_win, wrap=tk.WORD, font=('Microsoft YaHei', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        content = """
【数据分析工具说明】

1. 隔离性分析工具
   - 用途：评估切片隔离效果，观察uRLLC性能是否受eMBB负载增加而恶化。
   - X轴：eMBB负载 / eMBB用户数 / uRLLC负载
   - Y轴：uRLLC平均时延 / P95时延 / P99时延 / 抖动 / 丢包率
   - 可对比启用/未启用切片的两条曲线，并计算平均性能提升百分比。

2. 效率性分析工具
   - 用途：分析切片对资源利用率的影响，确保在保护高优先级业务的同时不浪费资源。
   - 三种图表：
       * 吞吐量对比：eMBB实际吞吐量随负载变化曲线
       * 资源利用率：柱状图对比有无切片时的资源利用率
       * 权衡分析：双Y轴同时展示eMBB吞吐量与uRLLC时延

3. 参数敏感性分析
   - 用途：通过热力图展示两个参数同时变化时对性能指标的影响，辅助参数调优。
   - X轴/Y轴参数：从urllcPriority、embbPriority、urllcGbr、urllcMbr、embbLoadMbps中选择
   - 颜色指标：uRLLC时延 / eMBB吞吐量 / 丢包率
   - 切片类型过滤：可只分析启用切片或未启用切片的数据

4. 流量详情分析
   - 用途：对单个仿真文件进行深度统计，展示每条流的分布特征。
   - 图表类型：
       * CDF累积分布：展示时延、抖动、吞吐量的概率分布
       * 箱线图：对比uRLLC与eMBB的指标分布
       * 柱状图：总吞吐量与时延双指标对比
       * 散点图：时延-吞吐量关系

【操作提示】
- 先通过“参数配置”和“运行控制”生成CSV报告文件。
- 在“数据分析工具”标签页选择对应工具，点击打开工具窗口。
- 在工具窗口中添加CSV文件（可多选），设置图表参数后点击“生成图表”。
- 图表支持缩放、平移、保存为PNG图片。
"""
        text.insert(tk.END, content)
        text.config(state=tk.DISABLED)

    def show_about(self):
        messagebox.showinfo("关于", "5G网络切片仿真配置与数据分析平台 v2.1\n"
                            "毕业设计：基于NS-3的5G网络切片仿真模型设计\n"
                            "作者：帅宏杰\n"
                            "东北林业大学 计算机与控制工程学院\n"
                            "功能：仿真配置运行 + 四种数据分析工具")

    def get_command_line(self, params, extra_tag=""):
        if extra_tag:
            params = params.copy()
            params["simTag"] = extra_tag
        cmd_parts = []
        for key, value in params.items():
            arg_name = key
            if isinstance(value, bool):
                cmd_parts.append(f"--{arg_name}=" + ("true" if value else "false"))
            elif isinstance(value, str):
                cmd_parts.append(f"--{arg_name}={value}")
            else:
                cmd_parts.append(f"--{arg_name}={value}")
        inner_cmd = f"{self.ns3_program} " + " ".join(cmd_parts)
        if os.path.exists(os.path.join(self.ns3_root, 'ns3')):
            runner = './ns3'
        else:
            runner = './waf'
        cmd = f'{runner} run "{inner_cmd}"'
        return cmd

    def open_isolation_tool(self):
        tool = IsolationAnalysisTool(self)
        tool.create_window()

    def open_efficiency_tool(self):
        tool = EfficiencyAnalysisTool(self)
        tool.create_window()

    def open_parameter_tool(self):
        tool = ParameterSweepTool(self)
        tool.create_window()

    def open_flow_tool(self):
        tool = FlowDetailTool(self)
        tool.create_window()

def main():
    try:
        import matplotlib, pandas, numpy
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请安装: pip install matplotlib pandas numpy")
        sys.exit(1)
    app = SliceSimulatorApp()
    app.mainloop()

if __name__ == "__main__":
    main()