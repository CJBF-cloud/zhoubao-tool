import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTableWidget, QTableWidgetItem,
    QGroupBox, QProgressBar, QMessageBox, QHeaderView, QTabWidget,
    QTextEdit, QSplitter, QCheckBox, QFileDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QBrush


class FileSelector(QWidget):
    """自定义文件选择器，解决Mac对话框问题"""
    file_selected = pyqtSignal(str)

    def __init__(self, label_text="选择文件", file_type="csv"):
        super().__init__()
        self.file_type = file_type
        self.initUI(label_text)

    def initUI(self, label_text):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel(label_text)
        self.label.setStyleSheet("border: 1px solid gray; padding: 5px; background-color: white;")
        self.label.setMinimumWidth(200)
        layout.addWidget(self.label)

        self.btn = QPushButton("浏览...")
        self.btn.clicked.connect(self.select_file)
        layout.addWidget(self.btn)

        self.setLayout(layout)

    def select_file(self):
        # 使用QFileDialog的静态方法，并在Mac上使用原生对话框
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog  # 在Mac上使用非原生对话框避免问题

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"选择{self.file_type.upper()}文件",
            os.path.expanduser("~"),  # 默认打开用户目录
            f"{self.file_type.upper()} Files (*.{self.file_type});;All Files (*)",
            options=options
        )

        if file_path:
            self.label.setText(os.path.basename(file_path))
            self.label.setStyleSheet("border: 1px solid green; padding: 5px; background-color: #E8F5E9;")
            self.file_selected.emit(file_path)
            return file_path
        return None


class DataProcessor(QThread):
    """后台处理数据的线程"""
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, pv_file, uv_file, prev_pv_file=None, prev_uv_file=None):
        super().__init__()
        self.pv_file = pv_file
        self.uv_file = uv_file
        self.prev_pv_file = prev_pv_file
        self.prev_uv_file = prev_uv_file

    def run(self):
        try:
            self.log.emit("开始处理数据...")
            self.progress.emit(10)

            # 1. 处理本周PV数据
            self.log.emit(f"读取本周PV文件: {os.path.basename(self.pv_file)}")
            df_pv = pd.read_csv(self.pv_file)
            self.progress.emit(15)

            # 清理percent列
            df_pv['percent'] = df_pv['percent'].str.rstrip('%').astype(float)

            # 筛选条件：total_request >= 5000 且 percent >= 10.0
            filtered_df = df_pv[(df_pv['total_request'] >= 5000) & (df_pv['percent'] >= 10.0)]
            filtered_df['percent'] = filtered_df['percent'].map(lambda x: f"{x:.2f}%")
            self.log.emit(f"本周PV数据筛选完成，保留 {len(filtered_df)} 条记录")
            self.progress.emit(30)

            # 2. 处理本周UV数据
            self.log.emit(f"读取本周UV文件: {os.path.basename(self.uv_file)}")
            df_uv = pd.read_csv(self.uv_file)
            self.progress.emit(40)

            # 3. 左关联合并本周数据
            current_df = pd.merge(filtered_df, df_uv, on='activity_id', how='left')
            self.log.emit(f"本周PV-UV合并完成，共 {len(current_df)} 条记录")
            self.progress.emit(50)

            # 4. 如果有上周数据，进行周对比
            has_prev_data = self.prev_pv_file and os.path.exists(self.prev_pv_file) and \
                            self.prev_uv_file and os.path.exists(self.prev_uv_file)

            if has_prev_data:
                self.log.emit("开始处理上周数据...")

                # 处理上周PV数据
                self.log.emit(f"读取上周PV文件: {os.path.basename(self.prev_pv_file)}")
                prev_df_pv = pd.read_csv(self.prev_pv_file)

                # 清理percent列
                prev_df_pv['percent'] = prev_df_pv['percent'].str.rstrip('%').astype(float)

                # 筛选条件：total_request >= 5000 且 percent >= 10.0
                prev_filtered_df = prev_df_pv[(prev_df_pv['total_request'] >= 5000) & (prev_df_pv['percent'] >= 10.0)]
                prev_filtered_df['percent'] = prev_filtered_df['percent'].map(lambda x: f"{x:.2f}%")
                self.log.emit(f"上周PV数据筛选完成，保留 {len(prev_filtered_df)} 条记录")
                self.progress.emit(65)

                # 处理上周UV数据
                self.log.emit(f"读取上周UV文件: {os.path.basename(self.prev_uv_file)}")
                prev_df_uv = pd.read_csv(self.prev_uv_file)
                self.progress.emit(75)

                # 左关联合并上周数据
                prev_merged_df = pd.merge(prev_filtered_df, prev_df_uv, on='activity_id', how='left')
                self.log.emit(f"上周PV-UV合并完成，共 {len(prev_merged_df)} 条记录")
                self.progress.emit(80)

                # 数据预处理用于对比
                current_df['percent_x'] = current_df['percent_x'].str.rstrip('%').astype(float) / 100
                current_df['percent_y'] = current_df['percent_y'].str.rstrip('%').astype(float) / 100
                prev_merged_df['percent_x'] = prev_merged_df['percent_x'].str.rstrip('%').astype(float) / 100
                prev_merged_df['percent_y'] = prev_merged_df['percent_y'].str.rstrip('%').astype(float) / 100

                # 合并对比
                compare_df = pd.merge(current_df, prev_merged_df, on='activity_id',
                                      suffixes=('_this', '_prev'), how='left')

                # 计算周对比
                compare_df['percent_x_comparison'] = compare_df['percent_x_this'] - compare_df['percent_x_prev']
                compare_df['percent_y_comparison'] = compare_df['percent_y_this'] - compare_df['percent_y_prev']

                # 计算调用次数变化
                compare_df['total_request_x_comparison'] = compare_df['total_request_x_this'] - compare_df[
                    'total_request_x_prev']
                compare_df['total_request_y_comparison'] = compare_df['total_request_y_this'] - compare_df[
                    'total_request_y_prev']

                # 选择列
                final_columns = [
                    'activity_id',
                    'activity_name_x_this',
                    'total_request_x_this',
                    'total_request_x_comparison',
                    'level1_cnt_x_this',
                    'level2_cnt_x_this',
                    'percent_x_this',
                    'percent_x_comparison',
                    'total_request_y_this',
                    'total_request_y_comparison',
                    'level1_cnt_y_this',
                    'level2_cnt_y_this',
                    'percent_y_this',
                    'percent_y_comparison'
                ]
                result_df = compare_df[final_columns]

                # 重命名列
                column_renames = {
                    'activity_id': '活动ID',
                    'activity_name_x_this': '活动名称',
                    'total_request_x_this': '调用次数（PV）',
                    'total_request_x_comparison': '调用次数变化（PV）',
                    'level1_cnt_x_this': '1级调用数（PV）',
                    'level2_cnt_x_this': '2级调用数（PV）',
                    'percent_x_this': '风险比例（PV）',
                    'percent_x_comparison': '风险比例变化（PV）',
                    'total_request_y_this': '调用次数（UV）',
                    'total_request_y_comparison': '调用次数变化（UV）',
                    'level1_cnt_y_this': '1级调用数（UV）',
                    'level2_cnt_y_this': '2级调用数（UV）',
                    'percent_y_this': '风险比例（UV）',
                    'percent_y_comparison': '风险比例变化（UV）'
                }
                result_df = result_df.rename(columns=column_renames)

                # 格式化百分比显示
                for col in ['风险比例（PV）', '风险比例变化（PV）', '风险比例（UV）', '风险比例变化（UV）']:
                    if col in result_df.columns:
                        result_df[col] = result_df[col].apply(
                            lambda x: f"{x:.2%}" if pd.notna(x) and isinstance(x, (int, float)) else x
                        )

                self.log.emit("周对比计算完成")
                self.progress.emit(95)

            else:
                # 如果没有上周数据，直接使用当前数据
                result_df = current_df
                # 重命名列（简化版）
                column_renames = {
                    'activity_id': '活动ID',
                    'activity_name_x': '活动名称',
                    'total_request_x': '调用次数（PV）',
                    'level1_cnt_x': '1级调用数（PV）',
                    'level2_cnt_x': '2级调用数（PV）',
                    'percent_x': '风险比例（PV）',
                    'total_request_y': '调用次数（UV）',
                    'level1_cnt_y': '1级调用数（UV）',
                    'level2_cnt_y': '2级调用数（UV）',
                    'percent_y': '风险比例（UV）'
                }
                result_df = result_df.rename(columns=column_renames)
                self.log.emit("未提供上周数据，仅进行PV-UV合并")
                self.progress.emit(90)

            # 填充NaN值为空字符串（用于显示）
            result_df = result_df.fillna('')

            self.progress.emit(100)
            self.log.emit("数据处理完成！")
            self.finished.emit(result_df)

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            self.log.emit(f"错误详情: {error_detail}")
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.pv_file = None
        self.uv_file = None
        self.prev_pv_file = None
        self.prev_uv_file = None
        self.result_df = None

    def initUI(self):
        self.setWindowTitle('周报数据对比工具 v2.0 (Mac优化版)')
        self.setGeometry(100, 100, 1500, 900)

        # 设置全局字体
        font = QFont('Microsoft YaHei', 9)
        self.setFont(font)

        # 主布局
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # 顶部控制区域
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        splitter.addWidget(control_widget)

        # 本周数据区域
        current_group = QGroupBox("📅 本周数据（必选）")
        current_layout = QVBoxLayout(current_group)

        # PV文件选择器
        self.pv_selector = FileSelector("选择本周PV文件", "csv")
        self.pv_selector.file_selected.connect(lambda path: setattr(self, 'pv_file', path))
        current_layout.addWidget(self.pv_selector)

        # UV文件选择器
        self.uv_selector = FileSelector("选择本周UV文件", "csv")
        self.uv_selector.file_selected.connect(lambda path: setattr(self, 'uv_file', path))
        current_layout.addWidget(self.uv_selector)

        control_layout.addWidget(current_group)

        # 上周数据区域
        prev_group = QGroupBox("📆 上周数据（可选，用于周对比）")
        prev_layout = QVBoxLayout(prev_group)

        # 上周PV文件选择器
        self.prev_pv_selector = FileSelector("选择上周PV文件（可选）", "csv")
        self.prev_pv_selector.file_selected.connect(lambda path: setattr(self, 'prev_pv_file', path))
        prev_layout.addWidget(self.prev_pv_selector)

        # 上周UV文件选择器
        self.prev_uv_selector = FileSelector("选择上周UV文件（可选）", "csv")
        self.prev_uv_selector.file_selected.connect(lambda path: setattr(self, 'prev_uv_file', path))
        prev_layout.addWidget(self.prev_uv_selector)

        control_layout.addWidget(prev_group)

        # 按钮和进度条区域
        btn_layout = QHBoxLayout()
        self.process_btn = QPushButton("🚀 开始处理")
        self.process_btn.clicked.connect(self.process_data)
        self.process_btn.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-size: 14px; 
                padding: 10px; 
                font-weight: bold; 
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        btn_layout.addWidget(self.process_btn)

        self.save_btn = QPushButton("💾 保存结果")
        self.save_btn.clicked.connect(self.save_result)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:enabled {
                background-color: #2196F3;
                color: white;
            }
            QPushButton:enabled:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        btn_layout.addWidget(self.save_btn)

        self.clear_btn = QPushButton("🗑️ 清空")
        self.clear_btn.clicked.connect(self.clear_all)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                padding: 10px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        btn_layout.addWidget(self.clear_btn)

        btn_layout.addStretch()
        control_layout.addLayout(btn_layout)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #BDBDBD;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
        """)
        control_layout.addWidget(self.progress_bar)

        # 日志区域
        log_group = QGroupBox("📝 处理日志")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 11px;
            }
        """)
        log_layout.addWidget(self.log_text)
        control_layout.addWidget(log_group)

        # 数据展示区域
        table_group = QGroupBox("📊 数据预览")
        table_layout = QVBoxLayout(table_group)
        self.table_widget = QTableWidget()
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)
        table_layout.addWidget(self.table_widget)
        splitter.addWidget(table_group)

        # 设置分割比例
        splitter.setSizes([350, 550])

        # 统计信息标签
        self.stats_label = QLabel("📊 统计信息：等待处理...")
        self.stats_label.setStyleSheet("padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
        main_layout.addWidget(self.stats_label)

        # 状态栏
        self.statusBar().showMessage('就绪')
        self.statusBar().setStyleSheet("QStatusBar { padding: 5px; }")

    def process_data(self):
        if not self.pv_file or not self.uv_file:
            QMessageBox.warning(self, "警告", "请先选择本周的PV文件和UV文件！")
            return

        # 检查上周数据是否完整
        has_prev_pv = self.prev_pv_file and os.path.exists(self.prev_pv_file)
        has_prev_uv = self.prev_uv_file and os.path.exists(self.prev_uv_file)

        if has_prev_pv != has_prev_uv:
            QMessageBox.warning(self, "警告", "上周数据需要同时选择PV和UV文件，或者都不选择！")
            return

        self.process_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.statusBar().showMessage('正在处理数据...')

        # 启动后台线程
        self.worker = DataProcessor(
            self.pv_file,
            self.uv_file,
            self.prev_pv_file,
            self.prev_uv_file
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_data_ready)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def append_log(self, message):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def on_data_ready(self, result_df):
        self.result_df = result_df
        self.display_data(result_df)
        self.process_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # 更新统计信息
        total_records = len(result_df)
        has_comparison = '调用次数变化（PV）' in result_df.columns if len(result_df.columns) > 0 else False
        self.stats_label.setText(
            f"📊 统计信息：共 {total_records} 条记录 | "
            f"列数：{len(result_df.columns)} | "
            f"{'包含周对比数据 ✅' if has_comparison else '仅包含本周数据'}"
        )
        self.statusBar().showMessage(f'✅ 数据处理完成，共 {total_records} 条记录')

        # 添加成功提示
        QMessageBox.information(self, "✅ 完成", f"数据处理完成！\n共处理 {total_records} 条记录")

    def on_error(self, error_msg):
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.statusBar().showMessage('❌ 处理出错')
        self.append_log(f"❌ 错误: {error_msg}")
        QMessageBox.critical(self, "❌ 错误", f"数据处理失败：\n{error_msg}")

    def display_data(self, df):
        if df.empty:
            self.table_widget.setRowCount(0)
            self.table_widget.setColumnCount(0)
            return

        self.table_widget.setRowCount(len(df))
        self.table_widget.setColumnCount(len(df.columns))
        self.table_widget.setHorizontalHeaderLabels(df.columns)

        # 设置列宽自适应
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        # 填充数据
        for row_idx, row in df.iterrows():
            for col_idx, col_name in enumerate(df.columns):
                value = row[col_name]
                item = QTableWidgetItem(str(value) if pd.notna(value) else '')
                item.setTextAlignment(Qt.AlignCenter)

                # 根据变化值设置颜色
                if '变化' in col_name and pd.notna(value) and isinstance(value, str):
                    try:
                        # 尝试解析数值
                        if value.endswith('%'):
                            num_val = float(value.strip('%'))
                        else:
                            num_val = float(value)

                        if num_val > 0:
                            item.setForeground(QBrush(QColor(220, 50, 50)))  # 红色
                            # 添加向上箭头
                            item.setText(f"▲ {value}")
                        elif num_val < 0:
                            item.setForeground(QBrush(QColor(50, 180, 50)))  # 绿色
                            # 添加向下箭头
                            item.setText(f"▼ {value}")
                    except:
                        pass

                self.table_widget.setItem(row_idx, col_idx, item)

    def save_result(self):
        if self.result_df is None or self.result_df.empty:
            QMessageBox.warning(self, "警告", "没有数据可保存！")
            return

        # 生成文件名
        now = datetime.now().strftime("%Y%m%d")
        default_name = f"{now}_周对比结果.csv"

        # 使用非原生对话框避免Mac问题
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存结果",
            os.path.join(os.path.expanduser("~"), default_name),
            "CSV Files (*.csv);;All Files (*)",
            options=options
        )

        if file_path:
            try:
                self.result_df.to_csv(file_path, index=False, encoding='utf-8-sig')
                QMessageBox.information(self, "✅ 成功", f"数据已保存到：\n{file_path}")
                self.statusBar().showMessage(f'✅ 数据已保存: {os.path.basename(file_path)}')
            except Exception as e:
                QMessageBox.critical(self, "❌ 错误", f"保存失败：\n{str(e)}")

    def clear_all(self):
        self.pv_file = None
        self.uv_file = None
        self.prev_pv_file = None
        self.prev_uv_file = None
        self.result_df = None

        # 重置所有选择器
        self.pv_selector.label.setText("选择本周PV文件")
        self.pv_selector.label.setStyleSheet("border: 1px solid gray; padding: 5px; background-color: white;")
        self.uv_selector.label.setText("选择本周UV文件")
        self.uv_selector.label.setStyleSheet("border: 1px solid gray; padding: 5px; background-color: white;")
        self.prev_pv_selector.label.setText("选择上周PV文件（可选）")
        self.prev_pv_selector.label.setStyleSheet("border: 1px solid gray; padding: 5px; background-color: white;")
        self.prev_uv_selector.label.setText("选择上周UV文件（可选）")
        self.prev_uv_selector.label.setStyleSheet("border: 1px solid gray; padding: 5px; background-color: white;")

        self.table_widget.clear()
        self.table_widget.setRowCount(0)
        self.table_widget.setColumnCount(0)
        self.log_text.clear()
        self.save_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.stats_label.setText("📊 统计信息：等待处理...")
        self.statusBar().showMessage('已清空')


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格，在Mac上表现更好

    # 设置应用程序图标（可选）
    # app.setWindowIcon(QIcon('icon.png'))

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()