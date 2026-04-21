"""
测试collect模块的功能
"""

import os
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

from src.collect.file_collector import FileCollector
from src.collect.watcher import FileWatcher
from src.collect.web_collector import WebCollector
from src.core.config import get_config


class TestFileCollector(unittest.TestCase):
    """测试文件收集器"""

    def setUp(self):
        """设置测试环境"""
        self.collector = FileCollector()
        self.config = get_config()
        
        # 创建临时测试文件
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test_file.txt")
        with open(self.test_file, 'w') as f:
            f.write("This is a test file for FileCollector.")

    def tearDown(self):
        """清理测试环境"""
        # 删除临时文件
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_import_file(self):
        """测试导入单个文件"""
        doc_id = self.collector.import_file(self.test_file)
        self.assertIsInstance(doc_id, str)
        self.assertTrue(len(doc_id) > 0)

    def test_import_directory(self):
        """测试导入目录"""
        # 创建另一个测试文件
        test_file2 = os.path.join(self.temp_dir, "test_file2.txt")
        with open(test_file2, 'w') as f:
            f.write("This is another test file.")

        doc_ids = self.collector.import_directory(self.temp_dir)
        self.assertIsInstance(doc_ids, list)
        self.assertEqual(len(doc_ids), 2)

        # 清理
        os.remove(test_file2)

    def test_get_supported_file_types(self):
        """测试获取支持的文件类型"""
        supported_types = self.collector.get_supported_file_types()
        self.assertIsInstance(supported_types, list)
        self.assertTrue(len(supported_types) > 0)

    def test_validate_file(self):
        """测试验证文件"""
        # 测试支持的文件
        self.assertTrue(self.collector.validate_file(self.test_file))
        
        # 测试不支持的文件
        test_file_unsupported = os.path.join(self.temp_dir, "test_file.unsupported")
        with open(test_file_unsupported, 'w') as f:
            f.write("This is an unsupported file.")
        self.assertFalse(self.collector.validate_file(test_file_unsupported))
        os.remove(test_file_unsupported)


class TestFileWatcher(unittest.TestCase):
    """测试文件系统监控器"""

    def setUp(self):
        """设置测试环境"""
        self.watcher = FileWatcher()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理测试环境"""
        # 停止监控
        if self.watcher.is_running():
            self.watcher.stop()
        # 删除临时目录
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_add_monitored_directory(self):
        """测试添加监控目录"""
        self.watcher.add_monitored_directory(self.temp_dir)
        monitored_dirs = self.watcher.get_monitored_directories()
        self.assertIn(self.temp_dir, monitored_dirs)

    def test_remove_monitored_directory(self):
        """测试移除监控目录"""
        self.watcher.add_monitored_directory(self.temp_dir)
        self.watcher.remove_monitored_directory(self.temp_dir)
        monitored_dirs = self.watcher.get_monitored_directories()
        self.assertNotIn(self.temp_dir, monitored_dirs)

    def test_start_stop(self):
        """测试启动和停止监控"""
        self.watcher.add_monitored_directory(self.temp_dir)
        self.watcher.start()
        self.assertTrue(self.watcher.is_running())
        
        self.watcher.stop()
        self.assertFalse(self.watcher.is_running())


class TestWebCollector(unittest.TestCase):
    """测试网络内容收集器"""

    def setUp(self):
        """设置测试环境"""
        self.collector = WebCollector()

    @patch('requests.get')
    def test_import_url(self, mock_get):
        """测试导入单个URL"""
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<html><head><title>Test Page</title></head><body><h1>Test Page</h1><p>This is a test page.</p></body></html>'
        mock_response.text = '<html><head><title>Test Page</title></head><body><h1>Test Page</h1><p>This is a test page.</p></body></html>'
        mock_get.return_value = mock_response

        url = "https://example.com/test"
        doc_id = self.collector.import_url(url)
        self.assertIsInstance(doc_id, str)
        self.assertTrue(len(doc_id) > 0)

    @patch('requests.get')
    def test_import_urls(self, mock_get):
        """测试导入多个URL"""
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<html><head><title>Test Page</title></head><body><h1>Test Page</h1><p>This is a test page.</p></body></html>'
        mock_response.text = '<html><head><title>Test Page</title></head><body><h1>Test Page</h1><p>This is a test page.</p></body></html>'
        mock_get.return_value = mock_response

        urls = ["https://example.com/test1", "https://example.com/test2"]
        doc_ids = self.collector.import_urls(urls)
        self.assertIsInstance(doc_ids, list)
        self.assertEqual(len(doc_ids), 2)

    def test_validate_url(self):
        """测试验证URL"""
        # 测试有效的URL
        valid_url = "https://example.com"
        # 注意：这里会实际发送网络请求，可能会失败
        # 为了避免网络依赖，我们可以使用mock
        with patch('requests.head') as mock_head:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_head.return_value = mock_response
            self.assertTrue(self.collector.validate_url(valid_url))

        # 测试无效的URL
        invalid_url = "invalid-url"
        self.assertFalse(self.collector.validate_url(invalid_url))

    @patch('requests.get')
    def test_get_url_info(self, mock_get):
        """测试获取URL信息"""
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<html><head><title>Test Page</title></head><body><h1>Test Page</h1><p>This is a test page.</p></body></html>'
        mock_response.headers = {'Content-Type': 'text/html', 'Content-Length': '100'}
        mock_get.return_value = mock_response

        url = "https://example.com/test"
        url_info = self.collector.get_url_info(url)
        self.assertIsInstance(url_info, dict)
        self.assertEqual(url_info['url'], url)
        self.assertEqual(url_info['title'], "Test Page")


if __name__ == '__main__':
    unittest.main()
