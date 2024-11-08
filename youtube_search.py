import sys
import os
import vlc
import tempfile
import yt_dlp
from threading import Thread
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLineEdit, QPushButton, QLabel, 
                            QTableWidget, QTableWidgetItem, QHeaderView, QFrame)
from PyQt5.QtCore import Qt, pyqtSlot, QTimer, QMetaType, QThread
from functools import partial
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl
import webbrowser

class YouTubeSearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Search App")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建主窗口部件
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # 创建主布局
        layout = QVBoxLayout(main_widget)
        
        # 搜索框和按钮
        search_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_button = QPushButton("搜索")
        self.search_button.clicked.connect(self.start_search)
        self.status_label = QLabel("")
        
        search_layout.addWidget(self.search_entry)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.status_label)
        
        # 搜索结果表格
        self.result_table = QTableWidget()
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels(["视频标题", "时长", "观看次数", "操作"])
        self.result_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.result_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.result_table.setColumnWidth(3, 100)
        
        # 添加到主布局
        layout.addLayout(search_layout)
        layout.addWidget(self.result_table)
        
        # 初始化变量
        self.current_video = None
        self.videos = []
        
        # 加载初始视频
        self.load_trending_tech_videos()

    def start_search(self):
        """开始搜索"""
        self.status_label.setText("搜索中...")
        self.search_button.setEnabled(False)
        self.search_videos()  # 直接调用搜索，不使用线程

    def search_videos(self):
        query = self.search_entry.text()
        if not query:
            return
            
        try:
            # 简化的搜索配置
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'format': 'best',
                'ignoreerrors': True,
            }
            
            print(f"开始搜索: {query}")
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                try:
                    results = ydl.extract_info(f"ytsearch10:{query}", download=False)
                    print(f"搜索完成: {results is not None}")
                    
                    if results and 'entries' in results:
                        entries = []
                        for entry in results['entries']:
                            if entry:
                                print(f"找到视频: {entry.get('title', 'Unknown')}")
                                entries.append(entry)
                        
                        if entries:
                            self.videos = entries
                            self.update_table_safe(entries)
                        else:
                            print("没有找到视频")
                            QTimer.singleShot(0, lambda: self.show_error("未找到视频"))
                    else:
                        print("搜索结果为空")
                        QTimer.singleShot(0, lambda: self.show_error("搜索结果为空"))
                        
                except Exception as e:
                    print(f"搜索出错: {str(e)}")
                    QTimer.singleShot(0, lambda: self.show_error(f"搜索失败: {str(e)}"))
                
        except Exception as e:
            print(f"搜索系统错误: {str(e)}")
            QTimer.singleShot(0, lambda: self.show_error(f"系统错误: {str(e)}"))
        
        finally:
            QTimer.singleShot(0, lambda: self.status_label.setText(""))
            QTimer.singleShot(0, lambda: self.search_button.setEnabled(True))

    def update_table_safe(self, entries):
        """安全地更新表格"""
        try:
            def update():
                self.result_table.setRowCount(0)  # 清空表格
                
                for index, video in enumerate(entries):
                    self.result_table.insertRow(index)
                    
                    # 获取视频信息
                    title = video.get('title', 'Unknown')
                    duration = video.get('duration', 0)
                    views = video.get('view_count', 0)
                    
                    # 创建表格项
                    title_item = QTableWidgetItem(title)
                    duration_item = QTableWidgetItem(f"{int(duration)} 秒" if duration else "未知")
                    views_item = QTableWidgetItem(f"{int(views):,} 次观看" if views else "未知")
                    
                    # 设置表格项
                    self.result_table.setItem(index, 0, title_item)
                    self.result_table.setItem(index, 1, duration_item)
                    self.result_table.setItem(index, 2, views_item)
                    
                    # 创建播放按钮
                    button_widget = QWidget()
                    layout = QHBoxLayout(button_widget)
                    play_button = QPushButton("播放")
                    
                    # 使用 partial 来避免 lambda 的闭包问题
                    play_button.clicked.connect(partial(self.play_video_at_row, index))
                    
                    layout.addWidget(play_button)
                    layout.setAlignment(Qt.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    self.result_table.setCellWidget(index, 3, button_widget)
                
                print(f"更新了 {len(entries)} 个搜索结果")
            
            # 确保在主线程中更新UI
            if QThread.currentThread() == QApplication.instance().thread():
                update()
            else:
                QTimer.singleShot(0, update)
                
        except Exception as e:
            print(f"更新表格失败: {str(e)}")
            QTimer.singleShot(0, lambda: self.show_error(f"更新表格失败: {str(e)}"))

    def play_video_at_row(self, row):
        """处理特定行的播放按钮点击"""
        try:
            if 0 <= row < len(self.videos):
                self.current_video = self.videos[row]
                video_id = self.current_video.get('id')
                if not video_id:
                    raise Exception("无法获取视频ID")
                    
                print(f"开始播放第 {row + 1} 个视频: {self.current_video.get('title', 'Unknown')} (ID: {video_id})")
                
                # 使用系统默认浏览器打开视频
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                webbrowser.open(video_url)
                print(f"在浏览器中打开视频: {video_url}")
                
            else:
                print(f"无效的行索引: {row}")
        except Exception as e:
            print(f"播放视频失败: {str(e)}")
            self.show_error(f"播放视频失败: {str(e)}")

    def update_status(self, text):
        self.status_label.setText(text)

    def show_error(self, message):
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.critical(self, "错误", message)

    def load_trending_tech_videos(self):
        """加载热门技术视频"""
        self.search_entry.setText("programming tutorial")
        self.start_search()

    def handle_error(self, e):
        print(f"错误详情: {str(e)}")
        if hasattr(e, 'exc_info'):
            print(f"异常信息: {e.exc_info[1]}")
        QTimer.singleShot(0, lambda: self.show_error(f"操作失败: {str(e)}"))

def register_qt_types():
    try:
        # 新版本 PyQt5 的注册方法
        from PyQt5.QtCore import qRegisterMetaType
        qRegisterMetaType("QVector<int>")
    except Exception as e:
        print(f"注册 QVector<int> 类型失败: {str(e)}")
        # 这个警告不影响主要功能，可以继续运行

if __name__ == '__main__':
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    app = QApplication(sys.argv)
    window = YouTubeSearchApp()
    window.show()
    sys.exit(app.exec_())