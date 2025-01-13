import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QPushButton, QLabel, QFileDialog, QSpinBox, QDoubleSpinBox,
                             QScrollArea, QFrame, QHBoxLayout, QMessageBox, QGroupBox)
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPalette, QLinearGradient
import numpy as np
from scipy import signal
import soundfile as sf
import os
from datetime import datetime

class StyledButton(QPushButton):
    def __init__(self, text, parent=None, primary=True):
        super().__init__(text, parent)
        self.setMinimumHeight(32)
        self.setFont(QFont("Microsoft YaHei", 9))
        if primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1976D2;
                    color: white;
                    border: none;
                    border-radius: 16px;
                    padding: 5px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1565C0;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
                QPushButton:disabled {
                    background-color: #90CAF9;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: white;
                    color: #1976D2;
                    border: 2px solid #1976D2;
                    border-radius: 16px;
                    padding: 5px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #E3F2FD;
                }
                QPushButton:pressed {
                    background-color: #BBDEFB;
                }
                QPushButton:disabled {
                    color: #90CAF9;
                    border-color: #90CAF9;
                }
            """)

class WaveformWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        self.setMaximumHeight(250)
        self.setFrameStyle(QFrame.NoFrame)
        self.setStyleSheet("""
            WaveformWidget {
                background-color: white;
                border-radius: 10px;
                border: 1px solid #E0E0E0;
            }
        """)
        self.waveform_data = None
        self.scale_factor = 1.0
        self.offset = 0
        self.silent_regions = []
        
    def set_waveform(self, data, samplerate):
        self.waveform_data = data
        self.samplerate = samplerate
        self.scale_factor = self.width() / len(data)
        self.update()
        
    def set_silent_regions(self, regions):
        self.silent_regions = regions
        self.update()
        
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.waveform_data is None:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont("Microsoft YaHei", 10))
            text = "请选择音频文件..."
            rect = self.rect()
            painter.drawText(rect, Qt.AlignCenter, text)
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制网格
        painter.setPen(QPen(QColor(240, 240, 240), 1, Qt.SolidLine))
        height = self.height()
        width = self.width()
        
        # 横线
        for i in range(4):
            y = height * (i + 1) / 4
            painter.drawLine(0, y, width, y)
            
        # 竖线
        for i in range(8):
            x = width * (i + 1) / 8
            painter.drawLine(x, 0, x, height)
        
        # 绘制波形
        gradient = QLinearGradient(0, height/2, 0, height)
        gradient.setColorAt(0, QColor(25, 118, 210))
        gradient.setColorAt(1, QColor(13, 71, 161))
        pen = QPen(gradient, 1.5)
        painter.setPen(pen)
        
        height = self.height()
        middle = height // 2
        scale = height // 3
        
        points = []
        step = max(1, len(self.waveform_data) // self.width())
        for i in range(0, len(self.waveform_data), step):
            x = int(i * self.scale_factor)
            y = middle + int(self.waveform_data[i] * scale)
            points.append(QPoint(x, y))
            
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])
            
        # 绘制检测到的静音区域
        for start, end in self.silent_regions:
            start_x = int(start * self.samplerate * self.scale_factor)
            end_x = int(end * self.samplerate * self.scale_factor)
            gradient = QLinearGradient(start_x, 0, end_x, 0)
            gradient.setColorAt(0, QColor(244, 67, 54, 20))
            gradient.setColorAt(0.5, QColor(244, 67, 54, 40))
            gradient.setColorAt(1, QColor(244, 67, 54, 20))
            painter.fillRect(
                QRect(start_x, 0, end_x - start_x, height),
                gradient
            )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("自动删除音频停顿")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #FAFAFA;
            }
            QLabel {
                color: #424242;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QSpinBox, QDoubleSpinBox {
                background-color: white;
                color: #424242;
                border: 1px solid #E0E0E0;
                padding: 4px 8px;
                min-height: 20px;
                font-size: 12px;
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border-color: #1976D2;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border-color: #1976D2;
                background-color: white;
            }
            QGroupBox {
                color: #424242;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                background-color: white;
            }
        """)
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # 文件选择区域
        file_group = QGroupBox("文件选择")
        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(12, 12, 12, 12)
        self.file_btn = StyledButton("选择音频文件", primary=True)
        self.file_btn.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_btn)
        
        self.file_label = QLabel("未选择文件")
        self.file_label.setStyleSheet("""
            padding: 0 12px;
            color: #757575;
            font-size: 12px;
        """)
        file_layout.addWidget(self.file_label)
        file_layout.addStretch()
        layout.addWidget(file_group)
        
        # 参数设置区域
        params_group = QGroupBox("参数设置")
        params_layout = QHBoxLayout(params_group)
        params_layout.setContentsMargins(12, 12, 12, 12)
        params_layout.setSpacing(20)
        
        # 音量阈值设置
        volume_layout = QVBoxLayout()
        volume_label = QLabel("音量阈值 (dB):")
        volume_label.setStyleSheet("font-size: 12px; margin-bottom: 4px;")
        self.volume_threshold = QDoubleSpinBox()
        self.volume_threshold.setRange(-60, 0)
        self.volume_threshold.setValue(-40)
        self.volume_threshold.valueChanged.connect(self.detect_silence)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_threshold)
        params_layout.addLayout(volume_layout)
        
        # 最小静音时长设置
        duration_layout = QVBoxLayout()
        duration_label = QLabel("最小静音时长 (ms):")
        duration_label.setStyleSheet("font-size: 12px; margin-bottom: 4px;")
        self.duration_threshold = QSpinBox()
        self.duration_threshold.setRange(10, 5000)
        self.duration_threshold.setValue(200)
        self.duration_threshold.valueChanged.connect(self.detect_silence)
        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_threshold)
        params_layout.addLayout(duration_layout)
        
        params_layout.addStretch()
        layout.addWidget(params_group)
        
        # 波形显示区域
        wave_group = QGroupBox("波形显示")
        wave_layout = QVBoxLayout(wave_group)
        wave_layout.setContentsMargins(12, 12, 12, 12)
        self.waveform_widget = WaveformWidget()
        wave_layout.addWidget(self.waveform_widget)
        layout.addWidget(wave_group)
        
        # 操作按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.process_btn = StyledButton("删除检测到的静音", primary=True)
        self.process_btn.clicked.connect(self.process_audio)
        self.process_btn.setEnabled(False)
        button_layout.addWidget(self.process_btn)
        
        self.export_btn = StyledButton("导出到...", primary=False)
        self.export_btn.clicked.connect(self.export_audio)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # 状态显示
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #2E7D32;
                padding: 8px 12px;
                background-color: #E8F5E9;
                border-radius: 8px;
                font-size: 12px;
                border: 1px solid #C8E6C9;
            }
        """)
        layout.addWidget(self.status_label)
        
        # 存储音频数据
        self.audio_data = None
        self.samplerate = None
        self.silent_regions = []
        self.processed_data = None
        self.input_filename = None
        
    def select_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择音频文件",
            "",
            "音频文件 (*.wav *.mp3)"
        )
        if file_name:
            self.input_filename = file_name
            self.file_label.setText(file_name)
            self.load_audio(file_name)
            
    def load_audio(self, file_name):
        try:
            # 加载音频文件
            data, samplerate = sf.read(file_name)
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)  # 转换为单声道
                
            self.audio_data = data
            self.samplerate = samplerate
            self.processed_data = None  # 重置处理后的数据
            self.waveform_widget.set_waveform(data, samplerate)
            self.process_btn.setEnabled(True)
            self.export_btn.setEnabled(False)  # 禁用导出按钮，直到处理完成
            
            # 检测静音
            self.detect_silence()
            
        except Exception as e:
            self.status_label.setText(f"加载失败：{str(e)}")
            
    def detect_silence(self):
        if self.audio_data is None:
            return
            
        try:
            # 计算RMS音量
            window_size = int(self.samplerate * 0.02)  # 20ms窗口
            windows = np.array_split(self.audio_data, len(self.audio_data) // window_size)
            rms = np.array([np.sqrt(np.mean(np.square(window))) for window in windows])
            db = 20 * np.log10(rms / np.max(np.abs(self.audio_data)) + 1e-10)
            
            # 获取设置的阈值
            volume_threshold = self.volume_threshold.value()
            duration_threshold = self.duration_threshold.value() / 1000  # 转换为秒
            
            # 找到低于阈值的片段
            self.silent_regions = []
            start = None
            frame_duration = window_size / self.samplerate
            
            for i, vol in enumerate(db):
                time = i * frame_duration
                if vol < volume_threshold:
                    if start is None:
                        start = time
                elif start is not None:
                    duration = time - start
                    if duration >= duration_threshold:
                        self.silent_regions.append((start, time))
                    start = None
                    
            # 处理最后一个片段
            if start is not None:
                time = len(db) * frame_duration
                duration = time - start
                if duration >= duration_threshold:
                    self.silent_regions.append((start, time))
                    
            # 更新波形显示
            self.waveform_widget.set_silent_regions(self.silent_regions)
            
            # 更新状态
            total_silence = sum(end - start for start, end in self.silent_regions)
            self.status_label.setText(f"检测到 {len(self.silent_regions)} 个静音片段，总时长 {total_silence:.2f} 秒")
            
        except Exception as e:
            self.status_label.setText(f"检测失败：{str(e)}")
            
    def process_audio(self):
        if self.audio_data is None or not self.silent_regions:
            return
            
        try:
            # 创建新的音频数据，跳过静音区域
            output_data = np.array([])
            last_end = 0
            
            for start, end in self.silent_regions:
                # 转换时间到采样点
                start_sample = int(start * self.samplerate)
                end_sample = int(end * self.samplerate)
                
                # 添加非静音部分
                output_data = np.concatenate([output_data, self.audio_data[last_end:start_sample]])
                last_end = end_sample
            
            # 添加最后一段
            if last_end < len(self.audio_data):
                output_data = np.concatenate([output_data, self.audio_data[last_end:]])
            
            # 保存处理后的数据
            self.processed_data = output_data
            
            # 更新波形显示
            self.audio_data = output_data
            self.waveform_widget.set_waveform(output_data, self.samplerate)
            self.silent_regions = []
            self.waveform_widget.set_silent_regions([])
            
            # 启用导出按钮
            self.export_btn.setEnabled(True)
            
            self.status_label.setText("处理完成！请选择导出位置...")
            
        except Exception as e:
            self.status_label.setText(f"处理失败：{str(e)}")
            
    def export_audio(self):
        if self.processed_data is None:
            return
            
        try:
            # 生成默认文件名
            input_dir = os.path.dirname(self.input_filename)
            input_name = os.path.splitext(os.path.basename(self.input_filename))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"{input_name}_无停顿_{timestamp}"
            default_ext = os.path.splitext(self.input_filename)[1][1:]
            
            # 打开保存文件对话框
            file_name, selected_filter = QFileDialog.getSaveFileName(
                self,
                "导出音频文件",
                os.path.join(input_dir, default_name),
                f"音频文件 (*.{default_ext});;WAV文件 (*.wav);;MP3文件 (*.mp3)"
            )
            
            if file_name:
                # 确保文件有正确的扩展名
                if not file_name.lower().endswith(('.wav', '.mp3')):
                    file_name += f".{default_ext}"
                
                # 导出文件
                sf.write(file_name, self.processed_data, self.samplerate)
                self.status_label.setText(f"导出完成！已保存到：{file_name}")
                
                # 询问是否打开所在文件夹
                reply = QMessageBox.question(
                    self,
                    "导出成功",
                    "文件已导出，是否打开所在文件夹？",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if reply == QMessageBox.Yes:
                    os.startfile(os.path.dirname(file_name))
                
        except Exception as e:
            self.status_label.setText(f"导出失败：{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 
