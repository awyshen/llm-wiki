import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [activeTab, setActiveTab] = useState('home')
  const [documents, setDocuments] = useState([])
  const [wikiPages, setWikiPages] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showSearchModal, setShowSearchModal] = useState(false)
  const [showGraphModal, setShowGraphModal] = useState(false)
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [isLoading, setIsLoading] = useState(false)
  const [notification, setNotification] = useState({ show: false, message: '', type: 'info' })
  const [healthStatus, setHealthStatus] = useState(null)

  // API base URL
  const API_BASE_URL = 'http://localhost:5050/api'

  // Fetch documents
  useEffect(() => {
    fetchDocuments()
    fetchWikiPages()
  }, [])

  const fetchDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents`)
      if (response.ok) {
        const data = await response.json()
        setDocuments(data)
      }
    } catch (error) {
      console.error('Error fetching documents:', error)
    }
  }

  const fetchWikiPages = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/wiki/pages`)
      if (response.ok) {
        const data = await response.json()
        setWikiPages(data)
      }
    } catch (error) {
      console.error('Error fetching wiki pages:', error)
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return

    setIsSearching(true)
    try {
      const response = await fetch(`${API_BASE_URL}/wiki/search?q=${encodeURIComponent(searchQuery)}`)
      if (response.ok) {
        const data = await response.json()
        setSearchResults(data)
        setShowSearchModal(true)
      }
    } catch (error) {
      console.error('Error searching:', error)
      showNotification('搜索失败，请稍后重试', 'error')
    } finally {
      setIsSearching(false)
    }
  }

  const saveSearchResultAsWikiPage = async (result) => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/wiki/save-answer`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: searchQuery,
          answer: result.content,
          related_results: [result]
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        showNotification(`已保存为Wiki页面: ${data.title}`, 'success')
        fetchWikiPages()
      } else {
        showNotification('保存失败，请稍后重试', 'error')
      }
    } catch (error) {
      console.error('Error saving search result:', error)
      showNotification('保存失败，请稍后重试', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileUpload = async (e) => {
    e.preventDefault()
    if (!uploadFile) return

    setIsLoading(true)
    setUploadProgress(0)

    const formData = new FormData()
    formData.append('file', uploadFile)

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        const data = await response.json()
        showNotification('文件上传成功', 'success')
        setShowUploadModal(false)
        setUploadFile(null)
        fetchDocuments()
      } else {
        showNotification('文件上传失败', 'error')
      }
    } catch (error) {
      console.error('Error uploading file:', error)
      showNotification('文件上传失败，请稍后重试', 'error')
    } finally {
      setIsLoading(false)
      setUploadProgress(0)
    }
  }

  const processDocuments = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/process/documents`, {
        method: 'POST'
      })

      if (response.ok) {
        const data = await response.json()
        showNotification(`处理完成：成功 ${data.success} 个，失败 ${data.failed} 个`, 'success')
        fetchWikiPages()
      } else {
        showNotification('处理文档失败', 'error')
      }
    } catch (error) {
      console.error('Error processing documents:', error)
      showNotification('处理文档失败，请稍后重试', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchGraphData = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/graph/data`)
      if (response.ok) {
        const data = await response.json()
        setGraphData(data)
        setShowGraphModal(true)
      } else {
        showNotification('获取图谱数据失败', 'error')
      }
    } catch (error) {
      console.error('Error fetching graph data:', error)
      showNotification('获取图谱数据失败，请稍后重试', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchHealthStatus = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/health`)
      if (response.ok) {
        const data = await response.json()
        setHealthStatus(data)
      } else {
        showNotification('获取健康状态失败', 'error')
      }
    } catch (error) {
      console.error('Error fetching health status:', error)
      showNotification('获取健康状态失败，请稍后重试', 'error')
    } finally {
      setIsLoading(false)
    }
  }

  const showNotification = (message, type = 'info') => {
    setNotification({ show: true, message, type })
    setTimeout(() => {
      setNotification({ show: false, message: '', type: 'info' })
    }, 3000)
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="logo">
          <h1>LLM Wiki</h1>
        </div>
        <div className="search-bar">
          <input
            type="text"
            placeholder="搜索知识..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <button onClick={handleSearch} disabled={isSearching}>
            {isSearching ? '搜索中...' : '搜索'}
          </button>
        </div>
        <div className="header-actions">
          <button onClick={() => setShowUploadModal(true)} className="primary-button">
            上传文档
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Navigation */}
        <nav className="navigation">
          <ul>
            <li className={activeTab === 'home' ? 'active' : ''}>
              <button onClick={() => setActiveTab('home')}>首页</button>
            </li>
            <li className={activeTab === 'documents' ? 'active' : ''}>
              <button onClick={() => setActiveTab('documents')}>文档管理</button>
            </li>
            <li className={activeTab === 'wiki' ? 'active' : ''}>
              <button onClick={() => setActiveTab('wiki')}>Wiki页面</button>
            </li>
            <li className={activeTab === 'graph' ? 'active' : ''}>
              <button onClick={() => {
                setActiveTab('graph')
                fetchGraphData()
              }}>知识图谱</button>
            </li>
            <li className={activeTab === 'health' ? 'active' : ''}>
              <button onClick={() => setActiveTab('health')}>健康检查</button>
            </li>
          </ul>
        </nav>

        {/* Content Area */}
        <div className="content-area">
          {activeTab === 'home' && (
            <div className="home-section">
              <div className="hero-section">
                <h2>欢迎使用 LLM Wiki</h2>
                <p>知识一次编译、持续累积，用 LLM 替代传统 RAG 每次查询从零推导的模式</p>
                <div className="hero-actions">
                  <button onClick={() => setShowUploadModal(true)} className="primary-button">
                    开始上传文档
                  </button>
                  <button onClick={fetchGraphData} className="secondary-button">
                    查看知识图谱
                  </button>
                </div>
              </div>

              <div className="stats-section">
                <div className="stat-card">
                  <h3>文档数量</h3>
                  <p>{documents.length}</p>
                </div>
                <div className="stat-card">
                  <h3>Wiki页面</h3>
                  <p>{wikiPages.length}</p>
                </div>
                <div className="stat-card">
                  <h3>处理状态</h3>
                  <p>{documents.filter(d => d.processing_status === 'completed').length} 已完成</p>
                </div>
              </div>

              <div className="recent-pages">
                <h3>最近的Wiki页面</h3>
                <div className="page-list">
                  {wikiPages.slice(0, 5).map(page => (
                    <div key={page.id} className="page-item">
                      <h4>{page.title}</h4>
                      <p>{page.category}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'documents' && (
            <div className="documents-section">
              <div className="section-header">
                <h2>文档管理</h2>
                <button onClick={processDocuments} disabled={isLoading} className="primary-button">
                  {isLoading ? '处理中...' : '处理文档'}
                </button>
              </div>

              <div className="document-list">
                {documents.map(doc => (
                  <div key={doc.id} className="document-item">
                    <div className="document-info">
                      <h4>{doc.title}</h4>
                      <p>{doc.filename}</p>
                    </div>
                    <div className="document-status">
                      <span className={`status-${doc.processing_status}`}>
                        {doc.processing_status === 'pending' ? '待处理' : 
                         doc.processing_status === 'processing' ? '处理中' : 
                         doc.processing_status === 'completed' ? '已完成' : '失败'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'wiki' && (
            <div className="wiki-section">
              <div className="section-header">
                <h2>Wiki页面</h2>
              </div>

              <div className="wiki-page-list">
                {wikiPages.map(page => (
                  <div key={page.id} className="wiki-page-item">
                    <h4>{page.title}</h4>
                    <p>{page.category}</p>
                    <div className="page-actions">
                      <button className="secondary-button">查看</button>
                      <button className="secondary-button">编辑</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'graph' && (
            <div className="graph-section">
              <div className="section-header">
                <h2>知识图谱</h2>
                <button onClick={fetchGraphData} disabled={isLoading} className="primary-button">
                  {isLoading ? '加载中...' : '刷新图谱'}
                </button>
              </div>

              <div className="graph-container">
                <div id="graph-container" style={{ width: '100%', height: '600px', border: '1px solid #e2e8f0' }}>
                  {/* 知识图谱将通过script.js渲染 */}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'health' && (
            <div className="health-section">
              <div className="section-header">
                <h2>健康检查</h2>
                <button onClick={fetchHealthStatus} disabled={isLoading} className="primary-button">
                  {isLoading ? '检查中...' : '运行检查'}
                </button>
              </div>

              <div className="health-status">
                {healthStatus ? (
                  <div className="health-details">
                    <div className="health-card">
                      <h3>Wiki 状态</h3>
                      <p>页面数量: {healthStatus.wiki.pages_count}</p>
                      <p>索引状态: {healthStatus.wiki.index_status}</p>
                      <p>日志状态: {healthStatus.wiki.log_status}</p>
                    </div>
                    <div className="health-card">
                      <h3>数据库状态</h3>
                      <p>连接状态: {healthStatus.database.connection_status}</p>
                      <p>文档数量: {healthStatus.database.documents_count}</p>
                      <p>实体数量: {healthStatus.database.entities_count}</p>
                      <p>关系数量: {healthStatus.database.relations_count}</p>
                    </div>
                    <div className="health-card">
                      <h3>知识图谱状态</h3>
                      <p>实体数量: {healthStatus.graph.entities_count}</p>
                      <p>关系数量: {healthStatus.graph.relations_count}</p>
                    </div>
                    <div className="health-card">
                      <h3>系统状态</h3>
                      <p>总体状态: {healthStatus.overall_status}</p>
                      <p>检查时间: {new Date(healthStatus.timestamp).toLocaleString()}</p>
                      {healthStatus.recommendations && healthStatus.recommendations.length > 0 && (
                        <div className="recommendations">
                          <h4>建议:</h4>
                          <ul>
                            {healthStatus.recommendations.map((rec, index) => (
                              <li key={index}>{rec}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <p>点击"运行检查"按钮开始健康检查</p>
                )}
              </div>
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <p>© 2026 LLM Wiki - 知识一次编译、持续累积</p>
      </footer>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3>上传文档</h3>
              <button onClick={() => setShowUploadModal(false)}>×</button>
            </div>
            <form onSubmit={handleFileUpload}>
              <div className="form-group">
                <label htmlFor="file">选择文件</label>
                <input
                  type="file"
                  id="file"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  required
                />
              </div>
              {uploadProgress > 0 && (
                <div className="progress-bar">
                  <div className="progress" style={{ width: `${uploadProgress}%` }}></div>
                </div>
              )}
              <div className="modal-actions">
                <button type="button" onClick={() => setShowUploadModal(false)}>
                  取消
                </button>
                <button type="submit" disabled={isLoading}>
                  {isLoading ? '上传中...' : '上传'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Search Modal */}
      {showSearchModal && (
        <div className="modal-overlay">
          <div className="modal search-modal">
            <div className="modal-header">
              <h3>搜索结果</h3>
              <button onClick={() => setShowSearchModal(false)}>×</button>
            </div>
            <div className="search-results">
              {searchResults.map((result, index) => (
                <div key={index} className="search-result-item">
                  <h4>{result.title}</h4>
                  <p>{result.content}</p>
                  <div className="result-meta">
                    <span>{result.type}</span>
                    <span>得分: {result.score.toFixed(2)}</span>
                  </div>
                  <button 
                    className="save-as-wiki-btn"
                    onClick={() => saveSearchResultAsWikiPage(result)}
                    disabled={isLoading}
                  >
                    保存为Wiki页面
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Graph Modal */}
      {showGraphModal && (
        <div className="modal-overlay">
          <div className="modal graph-modal">
            <div className="modal-header">
              <h3>知识图谱</h3>
              <button onClick={() => setShowGraphModal(false)}>×</button>
            </div>
            <div className="graph-modal-content">
              <div id="graph-modal-container" style={{ width: '100%', height: '600px' }}>
                {/* 知识图谱将通过script.js渲染 */}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Notification */}
      {notification.show && (
        <div className={`notification ${notification.type}`}>
          {notification.message}
        </div>
      )}
    </div>
  )
}

export default App
