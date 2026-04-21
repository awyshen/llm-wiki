"""
性能测试文件

测试向量存储的性能优化效果，包括嵌入生成速度、搜索响应时间等。
"""

import time
import random
from src.storage.vector import get_vector_store, get_embedding_service


def test_embedding_performance():
    """
    测试嵌入生成性能
    """
    print("测试嵌入生成性能...")
    embedding_service = get_embedding_service()
    
    # 生成测试文本
    test_texts = []
    for i in range(100):
        test_texts.append(f"这是测试文本{i}: {' '.join([f'单词{j}' for j in range(random.randint(10, 100))])}")
    
    # 测试首次生成嵌入
    start_time = time.time()
    embeddings = embedding_service.generate_embeddings(test_texts)
    first_time = time.time() - start_time
    print(f"首次生成100个文本嵌入耗时: {first_time:.3f}秒")
    
    # 测试缓存生成嵌入
    start_time = time.time()
    cached_embeddings = embedding_service.generate_embeddings(test_texts)
    cached_time = time.time() - start_time
    print(f"缓存生成100个文本嵌入耗时: {cached_time:.3f}秒")
    print(f"缓存加速比: {first_time / cached_time:.2f}x")
    
    return first_time, cached_time


def test_search_performance():
    """
    测试搜索性能
    """
    print("\n测试搜索性能...")
    vector_store = get_vector_store()
    
    if not vector_store:
        print("向量存储未初始化，测试跳过")
        return 0, 0
    
    # 准备测试数据
    test_documents = []
    test_ids = []
    test_metadatas = []
    
    for i in range(1000):
        test_documents.append(f"这是测试文档{i}: {' '.join([f'主题{j}' for j in range(random.randint(5, 20))])}")
        test_ids.append(f"doc{i}")
        test_metadatas.append({"category": f"category{random.randint(1, 10)}", "language": "zh"})
    
    # 添加文档
    start_time = time.time()
    vector_store.add(test_documents, test_ids, test_metadatas)
    add_time = time.time() - start_time
    print(f"添加1000个文档耗时: {add_time:.3f}秒")
    
    # 测试首次搜索
    test_queries = ["测试文档", "主题1", "category5", "随机搜索"]
    first_search_times = []
    
    for query in test_queries:
        start_time = time.time()
        results = vector_store.search(query, top_k=10)
        search_time = time.time() - start_time
        first_search_times.append(search_time)
        print(f"首次搜索 '{query}' 耗时: {search_time:.3f}秒")
    
    # 测试缓存搜索
    cached_search_times = []
    
    for query in test_queries:
        start_time = time.time()
        results = vector_store.search(query, top_k=10)
        search_time = time.time() - start_time
        cached_search_times.append(search_time)
        print(f"缓存搜索 '{query}' 耗时: {search_time:.3f}秒")
    
    # 计算平均搜索时间
    avg_first_search = sum(first_search_times) / len(first_search_times)
    avg_cached_search = sum(cached_search_times) / len(cached_search_times)
    print(f"平均首次搜索耗时: {avg_first_search:.3f}秒")
    print(f"平均缓存搜索耗时: {avg_cached_search:.3f}秒")
    print(f"搜索缓存加速比: {avg_first_search / avg_cached_search:.2f}x")
    
    # 清空向量存储
    vector_store.clear()
    
    return avg_first_search, avg_cached_search


def test_memory_usage():
    """
    测试内存使用情况
    """
    print("\n测试内存使用情况...")
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    start_memory = process.memory_info().rss / 1024 / 1024
    print(f"初始内存使用: {start_memory:.2f} MB")
    
    # 生成大量嵌入
    embedding_service = get_embedding_service()
    test_texts = [f"测试文本{i}: {' '.join([f'单词{j}' for j in range(50)])}" for i in range(500)]
    
    start_time = time.time()
    embeddings = embedding_service.generate_embeddings(test_texts)
    end_time = time.time()
    
    end_memory = process.memory_info().rss / 1024 / 1024
    print(f"生成500个嵌入后内存使用: {end_memory:.2f} MB")
    print(f"内存增加: {end_memory - start_memory:.2f} MB")
    print(f"生成500个嵌入耗时: {end_time - start_time:.3f}秒")
    
    return end_memory - start_memory


def main():
    """
    主测试函数
    """
    print("=== 向量存储性能测试 ===")
    
    # 测试嵌入性能
    embedding_first, embedding_cached = test_embedding_performance()
    
    # 测试搜索性能
    search_first, search_cached = test_search_performance()
    
    # 测试内存使用
    memory_increase = test_memory_usage()
    
    print("\n=== 性能测试总结 ===")
    print(f"嵌入生成加速比: {embedding_first / embedding_cached:.2f}x")
    if search_first > 0:
        print(f"搜索加速比: {search_first / search_cached:.2f}x")
    print(f"生成500个嵌入内存增加: {memory_increase:.2f} MB")
    print("性能测试完成!")


if __name__ == "__main__":
    main()
