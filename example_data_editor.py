import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json

# 初始数据（可与 example.py 保持同步）
destinations = ["Shanghai", "Xian", "Qingdao", "Chengde"]
params = {
    "Shanghai": {"U": 9, "D": 5},
    "Xian":     {"U": 8, "D": 4},
    "Qingdao":  {"U": 6, "D": 3},
    "Chengde":  {"U": 4, "D": 2},
}
outbound_trips = {
    "Shanghai": {
        "SH_G1": {"dep_time": 8,  "arr_time": 12.5, "cost": 550},
        "SH_G7": {"dep_time": 14, "arr_time": 18.5, "cost": 560},
    },
    "Xian": {
        "XA_G651": {"dep_time": 7,  "arr_time": 11.5, "cost": 515},
        "XA_G657": {"dep_time": 15, "arr_time": 19.5, "cost": 520},
    },
    "Qingdao": {
        "QD_G205": {"dep_time": 9,  "arr_time": 13,   "cost": 314},
        "QD_G209": {"dep_time": 16, "arr_time": 20,   "cost": 320},
    },
    "Chengde": {
        "CD_G3681": {"dep_time": 10, "arr_time": 11.5, "cost": 110},
        "CD_G3685": {"dep_time": 17, "arr_time": 18.5, "cost": 115},
    },
}
return_trips = {
    "Shanghai": {
        "SH_G8": {"dep_time": 82, "arr_time": 86.5, "cost": 550},
        "SH_G2": {"dep_time": 111,"arr_time": 115.5,"cost": 570},
    },
    "Xian": {
        "XA_G658": {"dep_time": 83, "arr_time": 87.5, "cost": 515},
        "XA_G652": {"dep_time": 105,"arr_time": 109.5,"cost": 525},
    },
    "Qingdao": {
        "QD_G210": {"dep_time": 88, "arr_time": 92,   "cost": 314},
        "QD_G206": {"dep_time": 111,"arr_time": 115,  "cost": 325},
    },
    "Chengde": {
        "CD_G3682": {"dep_time": 81, "arr_time": 82.5, "cost": 110},
        "CD_G3686": {"dep_time": 110,"arr_time": 111.5,"cost": 120},
    },
}

class DataEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("目的地与车次数据可视化编辑器")
        self.geometry("950x620")
        self.create_widgets()
        self.refresh_dest_list()
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

    def create_widgets(self):
        # 左侧目的地列表
        self.dest_listbox = tk.Listbox(self, width=20, exportselection=False)
        self.dest_listbox.grid(row=0, column=0, rowspan=6, sticky="ns")
        self.dest_listbox.bind("<<ListboxSelect>>", self.on_dest_select)
        self.dest_listbox.bind("<Double-Button-1>", self.edit_dest_name)

        # 目的地参数编辑
        tk.Label(self, text="效用U:").grid(row=0, column=1, sticky="e")
        self.u_entry = tk.Entry(self, width=8)
        self.u_entry.grid(row=0, column=2, sticky="w")
        tk.Label(self, text="难度D:").grid(row=1, column=1, sticky="e")
        self.d_entry = tk.Entry(self, width=8)
        self.d_entry.grid(row=1, column=2, sticky="w")

        # 目的地操作按钮
        tk.Button(self, text="新增目的地", command=self.add_dest).grid(row=2, column=1, columnspan=2, sticky="ew")
        tk.Button(self, text="删除目的地", command=self.del_dest).grid(row=3, column=1, columnspan=2, sticky="ew")
        tk.Button(self, text="保存参数", command=self.save_params).grid(row=4, column=1, columnspan=2, sticky="ew")

        # 去程车次表
        tk.Label(self, text="去程车次").grid(row=0, column=3)
        self.out_tree = ttk.Treeview(self, columns=("dep", "arr", "cost"), show="headings", height=8)
        for i, col in enumerate(["dep", "arr", "cost"]):
            self.out_tree.heading(col, text=["发车", "到达", "票价"][i])
            self.out_tree.column(col, width=70)
        self.out_tree.grid(row=1, column=3, rowspan=4)
        self.out_tree.bind("<Double-1>", self.edit_outbound)
        tk.Button(self, text="新增去程", command=self.add_outbound).grid(row=5, column=3, sticky="ew")
        tk.Button(self, text="删除选中去程", command=self.del_outbound).grid(row=6, column=3, sticky="ew")

        # 返程车次表
        tk.Label(self, text="返程车次").grid(row=0, column=4)
        self.ret_tree = ttk.Treeview(self, columns=("dep", "arr", "cost"), show="headings", height=8)
        for i, col in enumerate(["dep", "arr", "cost"]):
            self.ret_tree.heading(col, text=["发车", "到达", "票价"][i])
            self.ret_tree.column(col, width=70)
        self.ret_tree.grid(row=1, column=4, rowspan=4)
        self.ret_tree.bind("<Double-1>", self.edit_return)
        tk.Button(self, text="新增返程", command=self.add_return).grid(row=5, column=4, sticky="ew")
        tk.Button(self, text="删除选中返程", command=self.del_return).grid(row=6, column=4, sticky="ew")

        # 保存数据按钮
        tk.Button(self, text="保存为JSON", command=self.save_json).grid(row=7, column=1, columnspan=2, sticky="ew")
        tk.Button(self, text="退出", command=self.on_exit).grid(row=7, column=3, columnspan=2, sticky="ew")

    def refresh_dest_list(self):
        self.dest_listbox.delete(0, tk.END)
        for d in destinations:
            self.dest_listbox.insert(tk.END, d)
        if destinations:
            self.dest_listbox.selection_set(0)
            self.on_dest_select()

    def on_dest_select(self, event=None):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            self.u_entry.delete(0, tk.END)
            self.d_entry.delete(0, tk.END)
            self.out_tree.delete(*self.out_tree.get_children())
            self.ret_tree.delete(*self.ret_tree.get_children())
            return
        d = destinations[idxs[0]]
        # 参数
        self.u_entry.delete(0, tk.END)
        self.u_entry.insert(0, params[d]["U"])
        self.d_entry.delete(0, tk.END)
        self.d_entry.insert(0, params[d]["D"])
        # 去程
        self.out_tree.delete(*self.out_tree.get_children())
        for tid, info in outbound_trips[d].items():
            self.out_tree.insert("", tk.END, iid=tid, values=(info["dep_time"], info["arr_time"], info["cost"]))
        # 返程
        self.ret_tree.delete(*self.ret_tree.get_children())
        for tid, info in return_trips[d].items():
            self.ret_tree.insert("", tk.END, iid=tid, values=(info["dep_time"], info["arr_time"], info["cost"]))

    def add_dest(self):
        name = simpledialog.askstring("新增目的地", "输入新目的地名称：")
        if not name or name in destinations:
            messagebox.showerror("错误", "名称不能为空且不能重复。")
            return
        destinations.append(name)
        params[name] = {"U": 5, "D": 2}
        outbound_trips[name] = {}
        return_trips[name] = {}
        self.refresh_dest_list()
        self.dest_listbox.selection_clear(0, tk.END)
        self.dest_listbox.selection_set(destinations.index(name))
        self.on_dest_select()

    def edit_dest_name(self, event):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        old = destinations[idxs[0]]
        new = simpledialog.askstring("重命名目的地", f"将 {old} 重命名为：", initialvalue=old)
        if not new or new == old or new in destinations:
            return
        # 修改所有相关数据
        destinations[idxs[0]] = new
        params[new] = params.pop(old)
        outbound_trips[new] = outbound_trips.pop(old)
        return_trips[new] = return_trips.pop(old)
        self.refresh_dest_list()
        self.dest_listbox.selection_clear(0, tk.END)
        self.dest_listbox.selection_set(idxs[0])
        self.on_dest_select()

    def del_dest(self):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = destinations[idxs[0]]
        if messagebox.askyesno("确认", f"确定删除目的地 {d} 及其所有车次？"):
            destinations.remove(d)
            params.pop(d)
            outbound_trips.pop(d)
            return_trips.pop(d)
            self.refresh_dest_list()

    def save_params(self):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = destinations[idxs[0]]
        try:
            u = float(self.u_entry.get())
            dd = float(self.d_entry.get())
        except:
            messagebox.showerror("错误", "U和D必须为数字")
            return
        params[d]["U"] = u
        params[d]["D"] = dd
        # messagebox.showinfo("成功", "参数已保存")

    def add_outbound(self):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = destinations[idxs[0]]
        tid = simpledialog.askstring("新增去程车次", "输入车次编号：")
        if not tid or tid in outbound_trips[d]:
            messagebox.showerror("错误", "编号不能为空且不能重复。")
            return
        try:
            dep = float(simpledialog.askstring("发车时间", "发车时间（小时）："))
            arr = float(simpledialog.askstring("到达时间", "到达时间（小时）："))
            cost = float(simpledialog.askstring("票价", "票价："))
        except:
            messagebox.showerror("错误", "时间和票价必须为数字")
            return
        outbound_trips[d][tid] = {"dep_time": dep, "arr_time": arr, "cost": cost}
        self.on_dest_select()

    def edit_outbound(self, event):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = destinations[idxs[0]]
        sel = self.out_tree.selection()
        if not sel:
            return
        tid = sel[0]
        info = outbound_trips[d][tid]
        new_tid = simpledialog.askstring("编辑去程车次", "车次编号：", initialvalue=tid)
        if not new_tid:
            return
        try:
            dep = float(simpledialog.askstring("发车时间", "发车时间（小时）：", initialvalue=info["dep_time"]))
            arr = float(simpledialog.askstring("到达时间", "到达时间（小时）：", initialvalue=info["arr_time"]))
            cost = float(simpledialog.askstring("票价", "票价：", initialvalue=info["cost"]))
        except:
            messagebox.showerror("错误", "时间和票价必须为数字")
            return
        # 修改编号
        if new_tid != tid:
            if new_tid in outbound_trips[d]:
                messagebox.showerror("错误", "车次编号已存在。")
                return
            outbound_trips[d][new_tid] = outbound_trips[d].pop(tid)
            tid = new_tid
        outbound_trips[d][tid] = {"dep_time": dep, "arr_time": arr, "cost": cost}
        self.on_dest_select()

    def del_outbound(self):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = destinations[idxs[0]]
        sel = self.out_tree.selection()
        for tid in sel:
            outbound_trips[d].pop(tid)
        self.on_dest_select()

    def add_return(self):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = destinations[idxs[0]]
        tid = simpledialog.askstring("新增返程车次", "输入车次编号：")
        if not tid or tid in return_trips[d]:
            messagebox.showerror("错误", "编号不能为空且不能重复。")
            return
        try:
            dep = float(simpledialog.askstring("发车时间", "发车时间（小时）："))
            arr = float(simpledialog.askstring("到达时间", "到达时间（小时）："))
            cost = float(simpledialog.askstring("票价", "票价："))
        except:
            messagebox.showerror("错误", "时间和票价必须为数字")
            return
        return_trips[d][tid] = {"dep_time": dep, "arr_time": arr, "cost": cost}
        self.on_dest_select()

    def edit_return(self, event):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = destinations[idxs[0]]
        sel = self.ret_tree.selection()
        if not sel:
            return
        tid = sel[0]
        info = return_trips[d][tid]
        new_tid = simpledialog.askstring("编辑返程车次", "车次编号：", initialvalue=tid)
        if not new_tid:
            return
        try:
            dep = float(simpledialog.askstring("发车时间", "发车时间（小时）：", initialvalue=info["dep_time"]))
            arr = float(simpledialog.askstring("到达时间", "到达时间（小时）：", initialvalue=info["arr_time"]))
            cost = float(simpledialog.askstring("票价", "票价：", initialvalue=info["cost"]))
        except:
            messagebox.showerror("错误", "时间和票价必须为数字")
            return
        # 修改编号
        if new_tid != tid:
            if new_tid in return_trips[d]:
                messagebox.showerror("错误", "车次编号已存在。")
                return
            return_trips[d][new_tid] = return_trips[d].pop(tid)
            tid = new_tid
        return_trips[d][tid] = {"dep_time": dep, "arr_time": arr, "cost": cost}
        self.on_dest_select()

    def del_return(self):
        idxs = self.dest_listbox.curselection()
        if not idxs:
            return
        d = destinations[idxs[0]]
        sel = self.ret_tree.selection()
        for tid in sel:
            return_trips[d].pop(tid)
        self.on_dest_select()

    def save_json(self):
        data = {
            "destinations": destinations,
            "params": params,
            "outbound_trips": outbound_trips,
            "return_trips": return_trips
        }
        with open("edited_travel_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("保存成功", "数据已保存到 edited_travel_data.json")

    def on_exit(self):
        if messagebox.askokcancel("退出", "确定要退出编辑器吗？"):
            self.destroy()

if __name__ == "__main__":
    app = DataEditor()
    app.mainloop()
