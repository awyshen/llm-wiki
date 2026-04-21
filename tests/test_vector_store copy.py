"""
测试向量存储功能
"""

import time
from src.storage.vector import get_vector_store, get_embedding_service


def test_embedding_service():
    """
    测试嵌入服务
    """
    print("测试嵌入服务...")
    embedding_service = get_embedding_service()
    
    # 测试单个文本嵌入
    text = "这是一个测试文本"
    start_time = time.time()
    embedding = embedding_service.generate_embedding(text)
    print(f"单个文本嵌入耗时: {time.time() - start_time:.3f}秒")
    print(f"嵌入向量长度: {len(embedding)}")
    
    # 测试批量文本嵌入
    texts = ["测试文本1", "测试文本2", "测试文本3"]
    start_time = time.time()
    embeddings = embedding_service.generate_embeddings(texts)
    print(f"批量文本嵌入耗时: {time.time() - start_time:.3f}秒")
    print(f"批量嵌入数量: {len(embeddings)}")
    
    # 测试缓存
    start_time = time.time()
    cached_embedding = embedding_service.generate_embedding(text)
    print(f"缓存文本嵌入耗时: {time.time() - start_time:.3f}秒")
    
    print("嵌入服务测试完成!")


def test_vector_store():
    """
    测试向量存储
    """
    print("\n测试向量存储...")
    vector_store = get_vector_store()
    
    if not vector_store:
        print("向量存储未初始化，测试跳过")
        return
    
    # 测试添加文档
    documents = [
        "这是第一个测试文档，关于Python编程",
        "这是第二个测试文档，关于机器学习",
        "这是第三个测试文档，关于人工智能"
    ]
    ids = ["doc1", "doc2", "doc3"]
    metadatas = [
        {"category": "programming", "language": "zh"},
        {"category": "machine learning", "language": "zh"},
        {"category": "ai", "language": "zh"}
    ]
    
    start_time = time.time()
    vector_store.add(documents, ids, metadatas)
    print(f"添加文档耗时: {time.time() - start_time:.3f}秒")
    print(f"向量存储文档数量: {vector_store.count()}")
    
    # 测试搜索
    query = "Python编程"
    start_time = time.time()
    results = vector_store.search(query, top_k=3)
    print(f"搜索耗时: {time.time() - start_time:.3f}秒")
    print(f"搜索结果数量: {len(results)}")
    
    for i, (doc_id, score, metadata) in enumerate(results):
        print(f"结果{i+1}: ID={doc_id}, 分数={score:.4f}, 元数据={metadata}")
    
    # 测试搜索缓存
    start_time = time.time()
    cached_results = vector_store.search(query, top_k=3)
    print(f"缓存搜索耗时: {time.time() - start_time:.3f}秒")
    
    # 测试更新文档
    updated_documents = ["这是更新后的第一个测试文档，关于Python高级编程"]
    updated_metadatas = [{"category": "programming", "language": "zh", "updated": True}]
    start_time = time.time()
    vector_store.update(["doc1"], updated_documents, updated_metadatas)
    print(f"更新文档耗时: {time.time() - start_time:.3f}秒")
    
    # 测试删除文档
    start_time = time.time()
    vector_store.delete(["doc3"])
    print(f"删除文档耗时: {time.time() - start_time:.3f}秒")
    print(f"删除后文档数量: {vector_store.count()}")
    
    # 测试清空
    vector_store.clear()
    print(f"清空后文档数量: {vector_store.count()}")
    
    print("向量存储测试完成!")


if __name__ == "__main__":
    test_embedding_service()
    test_vector_store()
