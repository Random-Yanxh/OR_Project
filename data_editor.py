import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os # 用于检查文件是否存在
from datetime import datetime, timedelta
import calendar

# --- Function to load data ---
def load_data(filename="edited_travel_data.json"):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 基本结构检查
                if all(k in data for k in ["destinations", "params", "outbound_trips", "return_trips"]):
                    print(f"成功从 {filename} 加载数据。")
                    # 确保 params 包含新键 (如果加载旧文件)
                    for dest, p_data in data["params"].items():
                        p_data.setdefault('min_stay_hours', 48) # 提供默认值
                        p_data.setdefault('max_stay_hours', 96) # 提供默认值
                    return data["destinations"], data["params"], data["outbound_trips"], data["return_trips"]
                else:
                    print(f"警告: {filename} 文件结构不完整，将使用内置默认数据。")
        except json.JSONDecodeError:
            print(f"警告: {filename} 文件格式无效，将使用内置默认数据。")
        except Exception as e:
            print(f"加载 {filename} 时发生错误: {e}，将使用内置默认数据。")

    # 如果加载失败或文件不存在，使用内置默认数据
    print("使用内置默认数据。")
    default_destinations = ["Shanghai", "Xian", "Qingdao", "Chengde"]
    default_params = {
        "Shanghai": {"U": 9, "D": 5, "min_stay_hours": 72, "max_stay_hours": 120},
        "Xian":     {"U": 8, "D": 4, "min_stay_hours": 48, "max_stay_hours": 96},
        "Qingdao":  {"U": 6, "D": 3, "min_stay_hours": 48, "max_stay_hours": 72},
        "Chengde":  {"U": 4, "D": 2, "min_stay_hours": 24, "max_stay_hours": 48},
    }
    default_outbound_trips = {
        "Shanghai": {"SH_G1": {"dep_time": 8, "arr_time": 12.5, "cost": 550}, "SH_G7": {"dep_time": 14, "arr_time": 18.5, "cost": 560}},
        "Xian": {"XA_G651": {"dep_time": 7, "arr_time": 11.5, "cost": 515}, "XA_G657": {"dep_time": 15, "arr_time": 19.5, "cost": 520}},
        "Qingdao": {"QD_G205": {"dep_time": 9, "arr_time": 13, "cost": 314}, "QD_G209": {"dep_time": 16, "arr_time": 20, "cost": 320}},
        "Chengde": {"CD_G3681": {"dep_time": 10, "arr_time": 11.5, "cost": 110}, "CD_G3685": {"dep_time": 17, "arr_time": 18.5, "cost": 115}},
    }
    default_return_trips = {
        "Shanghai": {"SH_G8": {"dep_time": 82, "arr_time": 86.5, "cost": 550}, "SH_G2": {"dep_time": 111, "arr_time": 115.5, "cost": 570}},
        "Xian": {"XA_G658": {"dep_time": 83, "arr_time": 87.5, "cost": 515}, "XA_G652": {"dep_time": 105, "arr_time": 109.5, "cost": 525}},
        "Qingdao": {"QD_G210": {"dep_time": 88, "arr_time": 92, "cost": 314}, "QD_G206": {"dep_time": 111, "arr_time": 115, "cost": 325}},
        "Chengde": {"CD_G3682": {"dep_time": 81, "arr_time": 82.5, "cost": 110}, "CD_G3686": {"dep_time": 110, "arr_time": 111.5, "cost": 120}},
    }
    return default_destinations, default_params, default_outbound_trips, default_return_trips


class DataEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        # 加载数据
        self.current_file = "edited_travel_data.json"  # 默认文件名
        self.destinations, self.params, self.outbound_trips, self.return_trips = load_data()

        # 设置默认起始时间（当前时间）
        now = datetime.now()
        self.start_month = now.month
        self.start_day = now.day
        self.start_hour = now.hour

        self.title(f"目的地与车次数据可视化编辑器 - {self.current_file}")
        self.geometry("950x700")  # 增加高度以容纳时间选择控件
        self.create_widgets()
        self.refresh_dest_list()
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def create_widgets(self):
        # --- 左侧目的地列表 ---
        self.dest_listbox = tk.Listbox(self, width=25, exportselection=False) # 稍微加宽
        self.dest_listbox.grid(row=0, column=0, rowspan=8, padx=5, pady=5, sticky="nsew") # 增加rowspan
        self.dest_listbox.bind("<<ListboxSelect>>", self.on_dest_select)
        self.dest_listbox.bind("<Double-Button-1>", self.edit_dest_name)
        self.grid_rowconfigure(0, weight=1) # 让列表可以垂直拉伸

        # --- 中间目的地参数编辑 ---
        param_frame = tk.Frame(self)
        param_frame.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="nw")

        tk.Label(param_frame, text="参数编辑:", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky="w")

        tk.Label(param_frame, text="效用U:").grid(row=1, column=0, sticky="e", padx=5, pady=2)
        self.u_entry = tk.Entry(param_frame, width=10)
        self.u_entry.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        tk.Label(param_frame, text="难度D:").grid(row=2, column=0, sticky="e", padx=5, pady=2)
        self.d_entry = tk.Entry(param_frame, width=10)
        self.d_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        # 新增：最短停留时间
        tk.Label(param_frame, text="最短停留(h):").grid(row=3, column=0, sticky="e", padx=5, pady=2)
        self.min_stay_entry = tk.Entry(param_frame, width=10)
        self.min_stay_entry.grid(row=3, column=1, sticky="w", padx=5, pady=2)

        # 新增：最长停留时间
        tk.Label(param_frame, text="最长停留(h):").grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self.max_stay_entry = tk.Entry(param_frame, width=10)
        self.max_stay_entry.grid(row=4, column=1, sticky="w", padx=5, pady=2)

        # 目的地操作按钮
        btn_frame = tk.Frame(self)
        btn_frame.grid(row=1, column=1, columnspan=2, padx=5, pady=10, sticky="nw") # 放到参数下方

        tk.Button(btn_frame, text="新增目的地", command=self.add_dest).grid(row=0, column=0, padx=2, pady=2, sticky="ew")
        tk.Button(btn_frame, text="删除目的地", command=self.del_dest).grid(row=0, column=1, padx=2, pady=2, sticky="ew")
        tk.Button(btn_frame, text="保存参数", command=self.save_params).grid(row=1, column=0, columnspan=2, padx=2, pady=5, sticky="ew")

        # --- 右侧车次编辑 ---
        trip_frame = tk.Frame(self)
        trip_frame.grid(row=0, column=3, rowspan=8, padx=5, pady=5, sticky="nsew") # 调整布局
        self.grid_columnconfigure(3, weight=1) # 让车次部分可以水平拉伸

        # 去程车次
        tk.Label(trip_frame, text="去程车次", font=("Arial", 11)).grid(row=0, column=0, pady=(0, 5))
        self.out_tree = ttk.Treeview(trip_frame, columns=("train", "dep", "arr", "cost"), show="headings", height=8)
        for i, col in enumerate(["train", "dep", "arr", "cost"]):
            self.out_tree.heading(col, text=["车次", "发车(h)", "到达(h)", "票价"][i])
            self.out_tree.column(col, width=[100, 80, 80, 80][i], anchor='center')
        self.out_tree.grid(row=1, column=0, padx=5, pady=2, sticky="nsew")
        self.out_tree.bind("<Double-1>", self.edit_outbound)
        tk.Button(trip_frame, text="新增去程", command=self.add_outbound).grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        tk.Button(trip_frame, text="删除选中去程", command=self.del_outbound).grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        # 返程车次
        tk.Label(trip_frame, text="返程车次", font=("Arial", 11)).grid(row=0, column=1, pady=(0, 5))
        self.ret_tree = ttk.Treeview(trip_frame, columns=("train", "dep", "arr", "cost"), show="headings", height=8)
        for i, col in enumerate(["train", "dep", "arr", "cost"]):
            self.ret_tree.heading(col, text=["车次", "发车(h)", "到达(h)", "票价"][i])
            self.ret_tree.column(col, width=[100, 80, 80, 80][i], anchor='center')
        self.ret_tree.grid(row=1, column=1, padx=5, pady=2, sticky="nsew")
        self.ret_tree.bind("<Double-1>", self.edit_return)
        tk.Button(trip_frame, text="新增返程", command=self.add_return).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        tk.Button(trip_frame, text="删除选中返程", command=self.del_return).grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        trip_frame.grid_rowconfigure(1, weight=1) # 让 Treeview 可以垂直拉伸
        trip_frame.grid_columnconfigure(0, weight=1)
        trip_frame.grid_columnconfigure(1, weight=1)

        # --- 起始时间选择 ---
        time_frame = tk.Frame(self)
        time_frame.grid(row=8, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

        tk.Label(time_frame, text="起始时间:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        
        # 月份选择
        self.month_var = tk.StringVar(value=str(self.start_month))
        month_cb = ttk.Combobox(time_frame, textvariable=self.month_var, width=3, values=[str(i) for i in range(1, 13)])
        month_cb.pack(side=tk.LEFT, padx=2)
        tk.Label(time_frame, text="月").pack(side=tk.LEFT)

        # 日期选择
        self.day_var = tk.StringVar(value=str(self.start_day))
        self.day_cb = ttk.Combobox(time_frame, textvariable=self.day_var, width=3)
        self.day_cb.pack(side=tk.LEFT, padx=2)
        tk.Label(time_frame, text="日").pack(side=tk.LEFT)
        
        # 小时选择
        self.hour_var = tk.StringVar(value=str(self.start_hour))
        hour_cb = ttk.Combobox(time_frame, textvariable=self.hour_var, width=3, values=[str(i).zfill(2) for i in range(24)])
        hour_cb.pack(side=tk.LEFT, padx=2)
        tk.Label(time_frame, text="时").pack(side=tk.LEFT)

        # 初始化日期选项和绑定更新事件
        self.update_days()  # 现在所有变量都已创建，可以安全调用
        month_cb.bind('<<ComboboxSelected>>', lambda e: self.update_days())
        self.day_cb.bind('<<ComboboxSelected>>', lambda e: self.update_start_time())
        hour_cb.bind('<<ComboboxSelected>>', lambda e: self.update_start_time())

        # --- 底部全局操作按钮 ---
        bottom_frame = tk.Frame(self)
        bottom_frame.grid(row=9, column=0, columnspan=4, padx=5, pady=10, sticky="ew")

        # 添加文件操作按钮
        tk.Button(bottom_frame, text="打开JSON文件", command=self.load_json, width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(bottom_frame, text="新建JSON文件", command=self.new_json, width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(bottom_frame, text="保存为JSON", command=self.save_json, width=15).pack(side=tk.LEFT, padx=10)
        tk.Button(bottom_frame, text="退出", command=self.on_exit, width=15).pack(side=tk.RIGHT, padx=10)

    def refresh_dest_list(self):
        self.dest_listbox.delete(0, tk.END)
        for d in self.destinations:
            self.dest_listbox.insert(tk.END, d)
        if self.destinations:
            self.dest_listbox.selection_set(0)
            self.on_dest_select()
        else: # 如果列表为空，清空所有字段
             self.on_dest_select(clear_all=True)


    def on_dest_select(self, event=None, clear_all=False):
        if clear_all:
            idxs = []
        else:
            idxs = self.dest_listbox.curselection()

        if not idxs:
            # 清空参数输入框
            self.u_entry.delete(0, tk.END)
            self.d_entry.delete(0, tk.END)
            self.min_stay_entry.delete(0, tk.END)
            self.max_stay_entry.delete(0, tk.END)
            # 清空车次表
            self.out_tree.delete(*self.out_tree.get_children())
            self.ret_tree.delete(*self.ret_tree.get_children())
            return

        # 获取选中的目的地
        d = self.destinations[idxs[0]]
        d_params = self.params.get(d, {}) # 使用 get 以防万一

        # 填充参数
        self.u_entry.delete(0, tk.END)
        self.u_entry.insert(0, d_params.get("U", "")) # 使用 get 提供默认空字符串
        self.d_entry.delete(0, tk.END)
        self.d_entry.insert(0, d_params.get("D", ""))
        self.min_stay_entry.delete(0, tk.END)
        self.min_stay_entry.insert(0, d_params.get("min_stay_hours", "")) # 显示已存或空
        self.max_stay_entry.delete(0, tk.END)
        self.max_stay_entry.insert(0, d_params.get("max_stay_hours", "")) # 显示已存或空

        # 填充去程车次
        self.out_tree.delete(*self.out_tree.get_children())
        if d in self.outbound_trips:
            for tid, info in self.outbound_trips[d].items():
                values = (tid, info.get("dep_time", "-"), info.get("arr_time", "-"), info.get("cost", "-"))
                self.out_tree.insert("", tk.END, iid=tid, values=values)

        # 填充返程车次
        self.ret_tree.delete(*self.ret_tree.get_children())
        if d in self.return_trips:
            for tid, info in self.return_trips[d].items():
                values = (tid, info.get("dep_time", "-"), info.get("arr_time", "-"), info.get("cost", "-"))
                self.ret_tree.insert("", tk.END, iid=tid, values=values)

    def add_dest(self):
        name = simpledialog.askstring("新增目的地", "输入新目的地名称：")
        if not name:
            return
        if name in self.destinations:
            messagebox.showerror("错误", "目的地名称已存在，请使用其他名称。")
            return

        self.destinations.append(name)
        # 初始化参数，包括新增的停留时间，给个默认值
        self.params[name] = {"U": 5, "D": 2, "min_stay_hours": 48, "max_stay_hours": 96}
        self.outbound_trips[name] = {}
        self.return_trips[name] = {}

        self.refresh_dest_list()
        # 选中新添加的目的地
        new_index = self.destinations.index(name)
        self.dest_listbox.selection_clear(0, tk.END)
        self.dest_listbox.selection_set(new_index)
        self.dest_listbox.see(new_index) # 滚动到可见
        self.on_dest_select()

    def edit_dest_name(self, event):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        old_name = self.destinations[idxs[0]]
        new_name = simpledialog.askstring("重命名目的地", f"将 '{old_name}' 重命名为：", initialvalue=old_name)

        if not new_name or new_name == old_name:
            return
        if new_name in self.destinations:
            messagebox.showerror("错误", "新名称已存在，请使用其他名称。")
            return

        # 修改列表
        self.destinations[idxs[0]] = new_name
        # 修改字典键
        self.params[new_name] = self.params.pop(old_name)
        self.outbound_trips[new_name] = self.outbound_trips.pop(old_name)
        self.return_trips[new_name] = self.return_trips.pop(old_name)

        # 刷新列表并保持选中
        current_index = idxs[0]
        self.refresh_dest_list()
        self.dest_listbox.selection_set(current_index)
        self.dest_listbox.see(current_index)
        self.on_dest_select()

    def del_dest(self):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = self.destinations[idxs[0]]
        if messagebox.askyesno("确认删除", f"确定要删除目的地 '{d}' 及其所有相关数据（参数、车次）吗？此操作不可撤销。"):
            self.destinations.pop(idxs[0])
            self.params.pop(d, None) # 使用 pop 带默认值以防万一
            self.outbound_trips.pop(d, None)
            self.return_trips.pop(d, None)
            self.refresh_dest_list() # 列表刷新后会自动选中第一个或清空

    def save_params(self):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            messagebox.showwarning("提示", "请先在左侧选择一个目的地。")
            return
        d = self.destinations[idxs[0]]

        try:
            u_val = float(self.u_entry.get())
            d_val = float(self.d_entry.get())
            min_stay_val = float(self.min_stay_entry.get())
            max_stay_val = float(self.max_stay_entry.get())

            # 可选：添加逻辑检查，例如 min_stay <= max_stay
            if min_stay_val < 0 or max_stay_val < 0:
                 messagebox.showerror("错误", "停留时间不能为负数。")
                 return
            if min_stay_val > max_stay_val:
                messagebox.showerror("错误", "最短停留时间不能大于最长停留时间。")
                return

        except ValueError:
            messagebox.showerror("输入错误", "U, D, 最短停留, 最长停留 都必须是有效的数字。")
            return

        # 保存到内存中的数据结构
        if d in self.params:
            self.params[d]["U"] = u_val
            self.params[d]["D"] = d_val
            self.params[d]["min_stay_hours"] = min_stay_val
            self.params[d]["max_stay_hours"] = max_stay_val
            # messagebox.showinfo("成功", f"目的地 '{d}' 的参数已更新（内存中）。\n请记得最后点击 '保存为JSON' 以持久化存储。") # 可以加提示，但可能有点烦
            print(f"目的地 '{d}' 的参数已更新（内存中）。")
        else:
             messagebox.showerror("内部错误", f"找不到目的地 '{d}' 的参数记录。")


    # --- 车次编辑方法 (add_outbound, edit_outbound, del_outbound, add_return, edit_return, del_return) ---
    # 这些方法基本不变，只是确保它们操作的是 self.outbound_trips 和 self.return_trips
    def update_days(self, event=None):
        """根据选择的月份更新日期选项"""
        try:
            month = int(self.month_var.get())
            year = datetime.now().year
            _, days_in_month = calendar.monthrange(year, month)
            self.day_cb['values'] = [str(i) for i in range(1, days_in_month + 1)]
            # 如果当前选择的日期超出了新月份的最大天数，调整为最后一天
            if int(self.day_var.get()) > days_in_month:
                self.day_var.set(str(days_in_month))
        except ValueError:
            pass
        self.update_start_time()

    def update_start_time(self, event=None):
        """更新起始时间"""
        try:
            self.start_month = int(self.month_var.get())
            self.start_day = int(self.day_var.get())
            self.start_hour = int(self.hour_var.get())
        except ValueError:
            pass

    def get_time_input(self, title, prompt):
        """获取时间输入（月-日-时-分）并转换为相对小时数"""
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.geometry("300x180")
        dialog.transient(self)
        dialog.grab_set()

        result = {'success': False, 'hours': 0}

        # 创建输入框
        input_frame = tk.Frame(dialog)
        input_frame.pack(pady=10)

        # 月份选择
        month_var = tk.StringVar(value=str(self.start_month))
        tk.Label(input_frame, text="月:").grid(row=0, column=0, padx=5)
        month_cb = ttk.Combobox(input_frame, textvariable=month_var, width=3, values=[str(i) for i in range(1, 13)])
        month_cb.grid(row=0, column=1)

        # 日期选择
        day_var = tk.StringVar(value=str(self.start_day))
        tk.Label(input_frame, text="日:").grid(row=0, column=2, padx=5)
        day_cb = ttk.Combobox(input_frame, textvariable=day_var, width=3, values=[str(i) for i in range(1, 32)])
        day_cb.grid(row=0, column=3)

        # 时间选择（HH-MM）
        time_frame = tk.Frame(input_frame)
        time_frame.grid(row=1, column=0, columnspan=4, pady=10)
        
        tk.Label(time_frame, text="时间:").pack(side=tk.LEFT)
        hour_var = tk.StringVar(value="00")
        hour_entry = ttk.Combobox(time_frame, textvariable=hour_var, width=3, values=[str(i).zfill(2) for i in range(24)])
        hour_entry.pack(side=tk.LEFT, padx=2)
        
        tk.Label(time_frame, text="-").pack(side=tk.LEFT)
        
        minute_var = tk.StringVar(value="00")
        minute_entry = ttk.Combobox(time_frame, textvariable=minute_var, width=3, values=[str(i).zfill(2) for i in range(0, 60, 5)])
        minute_entry.pack(side=tk.LEFT, padx=2)

        # 提示标签
        tk.Label(dialog, text=prompt, wraplength=250).pack(pady=5)

        def validate_and_close():
            try:
                month = int(month_var.get())
                day = int(day_var.get())
                hour = int(hour_var.get())
                minute = int(minute_var.get())
                
                if not (1 <= month <= 12 and 1 <= day <= 31 and 0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time format")

                # 计算与起始时间的差值
                input_date = datetime(datetime.now().year, month, day, hour, minute)
                start_date = datetime(datetime.now().year, self.start_month, self.start_day, self.start_hour, 0)
                
                # 计算小时差
                time_diff = input_date - start_date
                hours = time_diff.total_seconds() / 3600
                
                # 根据分钟数进行四舍五入
                if minute >= 30:
                    hours = int(hours) + 1
                else:
                    hours = int(hours)

                result['success'] = True
                result['hours'] = hours
                dialog.destroy()
            except ValueError as e:
                messagebox.showerror("错误", "请输入有效的时间格式(HH:MM)")

        # 确认按钮
        tk.Button(dialog, text="确认", command=validate_and_close).pack(pady=10)

        dialog.wait_window()
        return result

    def add_outbound(self):
        idxs = self.dest_listbox.curselection()
        if not idxs: return
        d = self.destinations[idxs[0]]
        tid = simpledialog.askstring("新增去程车次", f"为 '{d}' 输入新去程车次编号：")
        if not tid: return
        if tid in self.outbound_trips.get(d, {}):
            messagebox.showerror("错误", f"车次编号 '{tid}' 在目的地 '{d}' 的去程中已存在。")
            return

        # 获取发车时间
        dep_result = self.get_time_input("发车时间", "请选择发车时间\n时间格式: HH:MM (24小时制)")
        if not dep_result['success']: return
        dep = dep_result['hours']

        # 获取到达时间
        arr_result = self.get_time_input("到达时间", "请选择到达时间\n时间格式: HH:MM (24小时制)")
        if not arr_result['success']: return
        arr = arr_result['hours']

        # 获取票价
        try:
            cost = float(simpledialog.askstring("票价", "票价：", parent=self))
            if cost < 0: raise ValueError("票价不能为负")
        except (ValueError, TypeError):
            messagebox.showerror("错误", "票价必须是有效的非负数字。")
            return

        if dep >= arr:
            messagebox.showwarning("提示", "发车时间应早于到达时间。")

        if d not in self.outbound_trips: self.outbound_trips[d] = {}
        self.outbound_trips[d][tid] = {"dep_time": dep, "arr_time": arr, "cost": cost}
        self.on_dest_select()

    def edit_outbound(self, event):
        idxs = self.dest_listbox.curselection()
        if not idxs: return
        d = self.destinations[idxs[0]]
        sel = self.out_tree.selection()
        if not sel: return
        tid = sel[0]
        info = self.outbound_trips[d][tid]

        new_tid = simpledialog.askstring("编辑去程车次", f"编辑 '{d}' 的去程车次 '{tid}'\n车次编号：", initialvalue=tid, parent=self)
        if not new_tid: return

        # 获取发车时间
        dep_result = self.get_time_input("发车时间", "请选择发车时间\n时间格式: HH:MM (24小时制)")
        if not dep_result['success']: return
        dep = dep_result['hours']

        # 获取到达时间
        arr_result = self.get_time_input("到达时间", "请选择到达时间\n时间格式: HH:MM (24小时制)")
        if not arr_result['success']: return
        arr = arr_result['hours']

        # 获取票价
        try:
            cost = float(simpledialog.askstring("票价", "票价：", initialvalue=info.get("cost", ""), parent=self))
            if cost < 0: raise ValueError("票价不能为负")
        except (ValueError, TypeError):
            messagebox.showerror("错误", "票价必须是有效的非负数字。")
            return

        if dep >= arr:
            messagebox.showwarning("提示", "发车时间应早于到达时间。")

        # 处理车次编号更改
        if new_tid != tid:
            if new_tid in self.outbound_trips[d]:
                messagebox.showerror("错误", f"新车次编号 '{new_tid}' 已存在于 '{d}' 的去程中。")
                return
            self.outbound_trips[d].pop(tid)
            tid = new_tid

        self.outbound_trips[d][tid] = {"dep_time": dep, "arr_time": arr, "cost": cost}
        self.on_dest_select()

    def del_outbound(self):
        idxs = self.dest_listbox.curselection()
        if not idxs: return
        d = self.destinations[idxs[0]]
        sels = self.out_tree.selection() # 可能选中多个
        if not sels:
            messagebox.showinfo("提示", "请先在右侧的去程列表中选择要删除的车次。")
            return
        if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(sels)} 个去程车次吗？"):
            if d in self.outbound_trips:
                for tid in sels:
                    self.outbound_trips[d].pop(tid, None) # 使用 pop 带默认值
            self.on_dest_select() # 刷新

    def add_return(self):
        idxs = self.dest_listbox.curselection()
        if not idxs: return
        d = self.destinations[idxs[0]]
        tid = simpledialog.askstring("新增返程车次", f"为 '{d}' 输入新返程车次编号：")
        if not tid: return
        if tid in self.return_trips.get(d, {}):
            messagebox.showerror("错误", f"车次编号 '{tid}' 在目的地 '{d}' 的返程中已存在。")
            return

        # 获取发车时间
        dep_result = self.get_time_input("发车时间", "请选择发车时间\n时间格式: HH:MM (24小时制)")
        if not dep_result['success']: return
        dep = dep_result['hours']

        # 获取到达时间
        arr_result = self.get_time_input("到达时间", "请选择到达时间\n时间格式: HH:MM (24小时制)")
        if not arr_result['success']: return
        arr = arr_result['hours']

        # 获取票价
        try:
            cost = float(simpledialog.askstring("票价", "票价：", parent=self))
            if cost < 0: raise ValueError("票价不能为负")
        except (ValueError, TypeError):
            messagebox.showerror("错误", "票价必须是有效的非负数字。")
            return

        if dep >= arr:
            messagebox.showwarning("提示", "发车时间应早于到达时间。")

        if d not in self.return_trips: self.return_trips[d] = {}
        self.return_trips[d][tid] = {"dep_time": dep, "arr_time": arr, "cost": cost}
        self.on_dest_select()

    def edit_return(self, event):
        idxs = self.dest_listbox.curselection()
        if not idxs: return
        d = self.destinations[idxs[0]]
        sel = self.ret_tree.selection()
        if not sel: return
        tid = sel[0]
        info = self.return_trips[d][tid]

        new_tid = simpledialog.askstring("编辑返程车次", f"编辑 '{d}' 的返程车次 '{tid}'\n车次编号：", initialvalue=tid, parent=self)
        if not new_tid: return

        # 获取发车时间
        dep_result = self.get_time_input("发车时间", "请选择发车时间\n时间格式: HH:MM (24小时制)")
        if not dep_result['success']: return
        dep = dep_result['hours']

        # 获取到达时间
        arr_result = self.get_time_input("到达时间", "请选择到达时间\n时间格式: HH:MM (24小时制)")
        if not arr_result['success']: return
        arr = arr_result['hours']

        # 获取票价
        try:
            cost = float(simpledialog.askstring("票价", "票价：", initialvalue=info.get("cost", ""), parent=self))
            if cost < 0: raise ValueError("票价不能为负")
        except (ValueError, TypeError):
            messagebox.showerror("错误", "票价必须是有效的非负数字。")
            return

        if dep >= arr:
            messagebox.showwarning("提示", "发车时间应早于到达时间。")

        # 处理车次编号更改
        if new_tid != tid:
            if new_tid in self.return_trips[d]:
                messagebox.showerror("错误", f"新车次编号 '{new_tid}' 已存在于 '{d}' 的返程中。")
                return
            self.return_trips[d].pop(tid)
            tid = new_tid

        self.return_trips[d][tid] = {"dep_time": dep, "arr_time": arr, "cost": cost}
        self.on_dest_select()

    def del_return(self): # 与 del_outbound 类似
        idxs = self.dest_listbox.curselection()
        if not idxs: return
        d = self.destinations[idxs[0]]
        sels = self.ret_tree.selection()
        if not sels:
            messagebox.showinfo("提示", "请先在右侧的返程列表中选择要删除的车次。")
            return
        if messagebox.askyesno("确认删除", f"确定要删除选中的 {len(sels)} 个返程车次吗？"):
            if d in self.return_trips:
                for tid in sels:
                    self.return_trips[d].pop(tid, None)
            self.on_dest_select()

    # --- 保存与退出 ---
    def update_title(self, filename=None):
        """更新窗口标题以显示当前文件名"""
        if filename:
            self.current_file = filename
        self.title(f"目的地与车次数据可视化编辑器 - {self.current_file}")

    def load_json(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON文件", "*.json")],
            title="打开数据文件"
        )
        if filename:
            try:
                self.destinations, self.params, self.outbound_trips, self.return_trips = load_data(filename)
                self.refresh_dest_list()
                self.update_title(os.path.basename(filename))
                messagebox.showinfo("成功", f"成功加载文件：{filename}")
            except Exception as e:
                messagebox.showerror("错误", f"加载文件失败：{str(e)}")

    def new_json(self):
        if messagebox.askokcancel("确认", "创建新文件将清空当前所有数据，确定要继续吗？"):
            self.destinations = []
            self.params = {}
            self.outbound_trips = {}
            self.return_trips = {}
            self.refresh_dest_list()
            self.update_title("新文件.json")
            messagebox.showinfo("成功", "已创建新文件，请添加目的地和相关数据。")

    def save_json(self):
        # 将当前内存中的数据保存到文件
        data_to_save = {
            "destinations": self.destinations,
            "params": self.params,
            "outbound_trips": self.outbound_trips,
            "return_trips": self.return_trips
        }
        
        # 让用户选择保存位置和文件名
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json")],
            initialfile="edited_travel_data.json",
            title="保存数据文件"
        )
        
        if not filename:  # 用户取消了保存
            return
            
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            self.update_title(os.path.basename(filename))
            messagebox.showinfo("保存成功", f"数据已成功保存到 {filename}")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法将数据写入文件 {filename}。\n错误: {e}")

    def on_exit(self):
        # 可以在这里添加一个检查，看是否有未保存的修改
        # （简化起见，这里直接询问退出）
        if messagebox.askokcancel("退出确认", "您确定要退出编辑器吗？\n（请确保已保存您的修改）"):
            self.destroy()

if __name__ == "__main__":
    app = DataEditor()
    
    # 添加命令行参数解析
    import sys
    if len(sys.argv) > 1:
        # 如果提供了文件路径参数，尝试加载该文件
        filename = sys.argv[1]
        try:
            app.destinations, app.params, app.outbound_trips, app.return_trips = load_data(filename)
            app.refresh_dest_list()
            app.update_title(os.path.basename(filename))
        except Exception as e:
            print(f"警告：加载文件 {filename} 失败，将使用默认数据。错误：{e}")
    
    app.mainloop()
