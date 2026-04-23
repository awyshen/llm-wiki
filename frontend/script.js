// 全局变量
let currentSection = 'import';
let importedDocuments = []; // 存储导入的文档
const API_BASE_URL = 'http://10.35.168.40:5050/api'; // 后端API基础URL
let healthStatus = null; // 存储健康状态

// 页面加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 初始化导航事件
    initNavigation();
    
    // 初始化滑块事件
    initSliders();
    
    // 初始化按钮事件
    initButtons();
    
    // 初始化知识图谱
    initGraphVisualization();
});

// 初始化导航
function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.section');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // 隐藏所有 section
            sections.forEach(section => {
                section.style.display = 'none';
            });
            
            // 移除所有导航链接的 active 类
            navLinks.forEach(navLink => {
                navLink.classList.remove('active');
            });
            
            // 显示当前 section
            const targetId = this.getAttribute('href').substring(1);
            document.getElementById(targetId).style.display = 'block';
            
            // 添加 active 类到当前导航链接
            this.classList.add('active');
            
            // 更新当前 section
            currentSection = targetId;
            
            // 初始化对应部分的功能
            switch(targetId) {
                case 'graph':
                    initGraphVisualization();
                    break;
                case 'dialog':
                    initDialogSection();
                    break;
            }
        });
    });
}

// 初始化滑块事件
function initSliders() {
    // 最大节点数滑块
    const maxNodesSlider = document.getElementById('max-nodes');
    if (maxNodesSlider) {
        maxNodesSlider.addEventListener('input', function() {
            const label = document.querySelector('label[for="max-nodes"]');
            if (label) {
                label.textContent = `最大节点数: ${this.value}`;
            }
        });
    }
    
    // 最大深度滑块
    const maxDepthSlider = document.getElementById('max-depth');
    if (maxDepthSlider) {
        maxDepthSlider.addEventListener('input', function() {
            const label = document.querySelector('label[for="max-depth"]');
            if (label) {
                label.textContent = `最大深度: ${this.value}`;
            }
        });
    }
    
    // 搜索深度滑块
    const searchDepthSlider = document.getElementById('search-depth');
    if (searchDepthSlider) {
        searchDepthSlider.addEventListener('input', function() {
            const label = document.querySelector('label[for="search-depth"]');
            if (label) {
                label.textContent = `搜索深度: ${this.value}`;
            }
        });
    }
}

// 初始化按钮事件
function initButtons() {
    // 文档导入按钮
    const importBtn = document.getElementById('import-btn');
    if (importBtn) {
        importBtn.addEventListener('click', async function() {
            try {
                const fileInput = document.getElementById('file-input');
                const importResult = document.getElementById('import-result');
                
                if (fileInput.files.length === 0) {
                    importResult.textContent = '请选择文件';
                    return;
                }
                
                importResult.textContent = '正在导入文件...';
                
                // 上传文件到后端
                const formData = new FormData();
                for (let i = 0; i < fileInput.files.length; i++) {
                    formData.append('file', fileInput.files[i]);
                }
                
                const results = [];
                for (let i = 0; i < fileInput.files.length; i++) {
                    const file = fileInput.files[i];
                    const fileFormData = new FormData();
                    fileFormData.append('file', file);
                    
                    try {
                        const response = await fetch(`${API_BASE_URL}/documents/upload`, {
                            method: 'POST',
                            body: fileFormData
                        });
                        
                        if (response.ok) {
                            const data = await response.json();
                            results.push({
                                filename: file.name,
                                success: true,
                                type: file.type,
                                doc_id: data.id,
                                error: null,
                                status: 'pending',
                                created_at: new Date().toISOString().replace('T', ' ').substring(0, 19)
                            });
                        } else {
                            const errorData = await response.json();
                            results.push({
                                filename: file.name,
                                success: false,
                                type: file.type,
                                doc_id: null,
                                error: errorData.error || '上传失败',
                                status: 'failed',
                                created_at: new Date().toISOString().replace('T', ' ').substring(0, 19)
                            });
                        }
                    } catch (error) {
                        results.push({
                            filename: file.name,
                            success: false,
                            type: file.type,
                            doc_id: null,
                            error: error.message,
                            status: 'failed',
                            created_at: new Date().toISOString().replace('T', ' ').substring(0, 19)
                        });
                    }
                }
                
                const result = {
                    total: fileInput.files.length,
                    success: results.filter(r => r.success).length,
                    details: results
                };
                
                // 存储导入的文档
                importedDocuments = importedDocuments.concat(results);
                
                importResult.textContent = JSON.stringify(result, null, 2);
                
                // 显示成功消息
                importResult.style.color = '#10b981';
                
                // 3秒后恢复默认颜色
                setTimeout(() => {
                    importResult.style.color = '';
                }, 3000);
            } catch (error) {
                const importResult = document.getElementById('import-result');
                importResult.textContent = '导入操作失败: ' + error.message;
                importResult.style.color = '#ef4444';
            }
        });
    }
    
    // 刷新文档列表按钮
    const refreshDocsBtn = document.getElementById('refresh-docs-btn');
    if (refreshDocsBtn) {
        refreshDocsBtn.addEventListener('click', refreshDocumentList);
    }
    
    // 状态筛选下拉框
    const filterStatus = document.getElementById('filter-status');
    if (filterStatus) {
        filterStatus.addEventListener('change', refreshDocumentList);
    }
    
    // 刷新文档列表函数
    async function refreshDocumentList() {
        try {
            const docList = document.getElementById('doc-list');
            const statusFilter = document.getElementById('filter-status').value;
            
            // 显示加载状态
            docList.innerHTML = '<div style="text-align: center; padding: 20px;">加载中...</div>';
            
            // 从后端API获取文档列表
            const response = await fetch(`${API_BASE_URL}/documents`);
            
            if (response.ok) {
                const documents = await response.json();
                
                // 筛选文档
                let filteredDocs = documents;
                if (statusFilter !== '全部') {
                    filteredDocs = documents.filter(doc => doc.processing_status === statusFilter);
                }
                
                // 生成表格HTML
                let tableHTML = '<table><thead><tr><th>ID</th><th>标题</th><th>文件名</th><th>类型</th><th>状态</th><th>创建时间</th></tr></thead><tbody><tbody>';
                
                if (filteredDocs.length === 0) {
                    tableHTML += '<tr><td colspan="6" style="text-align: center; color: #64748b;">暂无文档</td></tr>';
                } else {
                    filteredDocs.forEach((doc, index) => {
                        tableHTML += `<tr>
                            <td>${index + 1}</td>
                            <td>${doc.title || doc.filename}</td>
                            <td>${doc.filename}</td>
                            <td>${doc.file_type || 'unknown'}</td>
                            <td>${doc.processing_status}</td>
                            <td>${doc.created_at ? new Date(doc.created_at).toLocaleString() : '未知'}</td>
                        </tr>`;
                    });
                }
                
                tableHTML += '</tbody></table>';
                docList.innerHTML = tableHTML;
            } else {
                docList.innerHTML = '<div style="text-align: center; color: #ef4444;">获取文档列表失败</div>';
            }
        } catch (error) {
            console.error('刷新文档列表失败:', error);
            const docList = document.getElementById('doc-list');
            docList.innerHTML = '<div style="text-align: center; color: #ef4444;">刷新文档列表失败: ' + error.message + '</div>';
        }
    }
    
    // 开始处理按钮
    const processBtn = document.getElementById('process-btn');
    if (processBtn) {
        processBtn.addEventListener('click', async function() {
            try {
                const processResult = document.getElementById('process-result');
                
                processResult.textContent = '正在处理文档...';
                
                // 调用后端API处理文档
                const response = await fetch(`${API_BASE_URL}/process/documents`, {
                    method: 'POST'
                });
                
                if (response.ok) {
                    const result = await response.json();
                    processResult.textContent = JSON.stringify(result, null, 2);
                    processResult.style.color = '#10b981';
                    
                    // 刷新文档列表
                    if (currentSection === 'manage') {
                        await refreshDocumentList();
                    }
                    
                    // 3秒后恢复默认颜色
                    setTimeout(() => {
                        processResult.style.color = '';
                    }, 3000);
                } else {
                    const errorData = await response.json();
                    processResult.textContent = '处理文档失败: ' + (errorData.error || '未知错误');
                    processResult.style.color = '#ef4444';
                }
            } catch (error) {
                const processResult = document.getElementById('process-result');
                processResult.textContent = '处理操作失败: ' + error.message;
                processResult.style.color = '#ef4444';
            }
        });
    }
    
    // 刷新统计按钮
    const statsBtn = document.getElementById('stats-btn');
    if (statsBtn) {
        statsBtn.addEventListener('click', async function() {
            try {
                const processResult = document.getElementById('process-result');
                
                // 从后端API获取文档列表，然后计算统计信息
                const response = await fetch(`${API_BASE_URL}/documents`);
                
                if (response.ok) {
                    const documents = await response.json();
                    const result = {
                        total: documents.length,
                        pending: documents.filter(doc => doc.processing_status === 'pending').length,
                        processing: documents.filter(doc => doc.processing_status === 'processing').length,
                        completed: documents.filter(doc => doc.processing_status === 'completed').length,
                        failed: documents.filter(doc => doc.processing_status === 'failed').length
                    };
                    processResult.textContent = JSON.stringify(result, null, 2);
                } else {
                    processResult.textContent = '获取统计信息失败';
                    processResult.style.color = '#ef4444';
                }
            } catch (error) {
                const processResult = document.getElementById('process-result');
                processResult.textContent = '刷新统计失败: ' + error.message;
                processResult.style.color = '#ef4444';
            }
        });
    }
    
    // 刷新页面列表按钮
    const refreshPagesBtn = document.getElementById('refresh-pages-btn');
    if (refreshPagesBtn) {
        refreshPagesBtn.addEventListener('click', async function() {
            try {
                const pageList = document.getElementById('page-list');
                
                // 显示加载状态
                pageList.innerHTML = '<div style="text-align: center; padding: 20px;">加载中...</div>';
                
                // 从后端API获取Wiki页面列表
                const response = await fetch(`${API_BASE_URL}/wiki/pages`);
                
                if (response.ok) {
                    const pages = await response.json();
                    
                    // 生成表格HTML
                    let tableHTML = '<table><thead><tr><th>标题</th><th>分类</th><th>修改时间</th></tr></thead><tbody><tbody>';
                    
                    if (pages.length === 0) {
                        tableHTML += '<tr><td colspan="3" style="text-align: center; color: #64748b;">暂无页面</td></tr>';
                    } else {
                        pages.forEach(page => {
                            tableHTML += `<tr>
                                <td>${page.title}</td>
                                <td>${page.category || '未分类'}</td>
                                <td>${page.updated_at ? new Date(page.updated_at).toLocaleString() : '未知'}</td>
                            </tr>`;
                        });
                    }
                    
                    tableHTML += '</tbody></table>';
                    pageList.innerHTML = tableHTML;
                } else {
                    pageList.innerHTML = '<div style="text-align: center; color: #ef4444;">获取页面列表失败</div>';
                }
            } catch (error) {
                console.error('刷新页面列表失败:', error);
                const pageList = document.getElementById('page-list');
                pageList.innerHTML = '<div style="text-align: center; color: #ef4444;">刷新页面列表失败: ' + error.message + '</div>';
            }
        });
    }
    
    // 搜索按钮
    const searchBtn = document.getElementById('search-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', async function() {
            try {
                const searchInput = document.getElementById('search-input');
                const searchResults = document.getElementById('search-results');
                const searchInfo = document.getElementById('search-info');
                
                if (!searchInput.value) {
                    searchInfo.textContent = '请输入搜索关键词';
                    return;
                }
                
                // 显示加载状态
                searchInfo.textContent = `搜索关键词: ${searchInput.value}`;
                searchResults.innerHTML = '<div style="text-align: center; padding: 20px;">搜索中...</div>';
                
                // 调用后端API进行搜索
                const response = await fetch(`${API_BASE_URL}/wiki/search?q=${encodeURIComponent(searchInput.value)}`);
                
                if (response.ok) {
                    const results = await response.json();
                    
                    // 存储搜索结果到全局变量，以便后续使用
                    window.searchResults = results;
                    window.currentSearchQuery = searchInput.value;
                    
                    // 生成表格HTML
                    let tableHTML = '<table><thead><tr><th>标题</th><th>类型</th><th>内容</th><th>相关性</th><th>操作</th></tr></thead><tbody><tbody><tbody>';
                    
                    if (!results || results.length === 0) {
                        tableHTML += '<tr><td colspan="5" style="text-align: center; color: #64748b;">没有找到匹配的结果</td></tr>';
                    } else {
                        results.forEach((result, index) => {
                            tableHTML += `<tr>
                                <td>${result.title || '未知'}</td>
                                <td>${result.type || '页面'}</td>
                                <td>${result.content || '无内容'}</td>
                                <td>${result.relevance || result.score || 0.0}</td>
                                <td><button onclick="saveSearchResultByIndex(${index})" class="btn btn-secondary">保存为Wiki页面</button></td>
                            </tr>`;
                        });
                    }
                    
                    tableHTML += '</tbody></table>';
                    searchResults.innerHTML = tableHTML;
                } else {
                    searchResults.innerHTML = '<div style="text-align: center; color: #ef4444;">搜索失败</div>';
                }
            } catch (error) {
                console.error('搜索失败:', error);
                const searchResults = document.getElementById('search-results');
                searchResults.innerHTML = '<div style="text-align: center; color: #ef4444;">搜索失败: ' + error.message + '</div>';
            }
        });
    }
    
    // 清空搜索按钮
    const clearBtn = document.getElementById('clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            document.getElementById('search-input').value = '';
            document.getElementById('search-results').innerHTML = '';
            document.getElementById('search-info').textContent = '';
        });
    }
    
    // 清空历史按钮
    const clearHistoryBtn = document.getElementById('clear-history-btn');
    if (clearHistoryBtn) {
        clearHistoryBtn.addEventListener('click', function() {
            document.getElementById('search-history').innerHTML = '';
        });
    }
    
    // 刷新图谱按钮
    const refreshGraphBtn = document.getElementById('refresh-graph-btn');
    if (refreshGraphBtn) {
        refreshGraphBtn.addEventListener('click', function() {
            initGraphVisualization();
        });
    }
    
    // 查找路径按钮
    const findPathBtn = document.getElementById('find-path-btn');
    if (findPathBtn) {
        findPathBtn.addEventListener('click', async function() {
            const startEntity = document.getElementById('start-entity');
            const endEntity = document.getElementById('end-entity');
            
            if (!startEntity.value || !endEntity.value) {
                alert('请输入起始和目标实体ID');
                return;
            }
            
            // 查找路径
            await visualizePath(startEntity.value, endEntity.value);
        });
    }
    
    // 获取相关实体按钮
    const getRelatedBtn = document.getElementById('get-related-btn');
    if (getRelatedBtn) {
        getRelatedBtn.addEventListener('click', async function() {
            const relatedEntity = document.getElementById('related-entity');
            
            if (!relatedEntity.value) {
                alert('请输入实体ID');
                return;
            }
            
            // 查找相关实体
            await visualizeRelatedEntities(relatedEntity.value);
        });
    }
    
    // 导出图谱按钮
    const exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async function() {
            const exportFormat = document.getElementById('export-format');
            const exportOutput = document.getElementById('export-output');
            
            try {
                // 从后端API获取图谱数据
                const graphData = await fetchGraphData();
                
                if (graphData.nodes.length === 0) {
                    exportOutput.textContent = '暂无可用的知识图谱数据';
                    exportOutput.style.color = '#ef4444';
                    return;
                }
                
                // 根据格式导出
                if (exportFormat.value === 'json') {
                    exportOutput.textContent = JSON.stringify(graphData, null, 2);
                } else {
                    // CSV格式
                    let csvContent = 'type,id,label,type,size\n';
                    graphData.nodes.forEach(node => {
                        csvContent += `node,${node.id},${node.label || node.id},${node.type || '其他'},${node.size || 15}\n`;
                    });
                    graphData.links.forEach(link => {
                        csvContent += `link,${link.source.id || link.source},${link.target.id || link.target},${link.label || ''},${link.value || 1}\n`;
                    });
                    exportOutput.textContent = csvContent;
                }
                
                exportOutput.style.color = '#10b981';
            } catch (error) {
                console.error('导出图谱失败:', error);
                exportOutput.textContent = '导出图谱失败: ' + error.message;
                exportOutput.style.color = '#ef4444';
            }
        });
    }
}

// 从后端API获取图谱数据
async function fetchGraphData() {
    try {
        const response = await fetch(`${API_BASE_URL}/graph/data`);
        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            console.error('获取图谱数据失败:', response.status);
            // 使用默认数据作为降级方案
            return {
                nodes: [
                    { id: '1', label: '张三', type: '人物', size: 15, color: '#FF6B6B' },
                    { id: '2', label: '李四', type: '人物', size: 15, color: '#FF6B6B' },
                    { id: '3', label: '王五', type: '人物', size: 15, color: '#FF6B6B' }
                ],
                links: [
                    { source: '1', target: '2', label: '朋友', value: 1, color: '#94a3b8' },
                    { source: '2', target: '3', label: '同事', value: 1, color: '#94a3b8' }
                ]
            };
        }
    } catch (error) {
        console.error('获取图谱数据失败:', error);
        // 使用默认数据作为降级方案
        return {
            nodes: [
                { id: '1', label: '张三', type: '人物', size: 15, color: '#FF6B6B' },
                { id: '2', label: '李四', type: '人物', size: 15, color: '#FF6B6B' },
                { id: '3', label: '王五', type: '人物', size: 15, color: '#FF6B6B' }
            ],
            links: [
                { source: '1', target: '2', label: '朋友', value: 1, color: '#94a3b8' },
                { source: '2', target: '3', label: '同事', value: 1, color: '#94a3b8' }
            ]
        };
    }
}

// 初始化知识图谱可视化
async function initGraphVisualization() {
    const graphContainer = document.getElementById('graph-container');
    if (!graphContainer) return;
    
    // 清空容器
    graphContainer.innerHTML = '';
    
    // 添加控制面板
    const controlPanel = document.createElement('div');
    controlPanel.className = 'control-panel';
    controlPanel.innerHTML = `
        <button onclick="resetZoom()">重置缩放</button>
        <button onclick="centerGraph()">居中图谱</button>
        <button onclick="toggleLabels()">切换标签</button>
        <input type="text" id="node-search" placeholder="搜索节点..." style="margin-left: 10px; padding: 5px;">
        <button onclick="searchNode()">搜索</button>
        <select id="type-filter" style="margin-left: 10px; padding: 5px;">
            <option value="all">所有类型</option>
        </select>
        <button onclick="filterByType()">筛选</button>
    `;
    graphContainer.appendChild(controlPanel);
    
    // 添加信息面板
    const infoPanel = document.createElement('div');
    infoPanel.className = 'info-panel';
    infoPanel.innerHTML = `
        节点: <strong id="node-count">0</strong> | 
        边: <strong id="link-count">0</strong> |
        类型: <strong id="type-count">0</strong>
    `;
    graphContainer.appendChild(infoPanel);
    
    // 显示加载状态
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'loading';
    loadingDiv.textContent = '加载中...';
    graphContainer.appendChild(loadingDiv);
    
    // 从后端API获取图谱数据
    const graphData = await fetchGraphData();
    
    // 移除加载状态
    loadingDiv.remove();
    
    // 更新统计信息
    document.getElementById('node-count').textContent = graphData.nodes.length;
    document.getElementById('link-count').textContent = graphData.links.length;
    document.getElementById('type-count').textContent = new Set(graphData.nodes.map(node => node.type)).size;
    
    // 填充类型选项
    const typeSet = new Set(graphData.nodes.map(node => node.type));
    const typeFilter = document.getElementById('type-filter');
    if (typeFilter) {
        typeSet.forEach(type => {
            const option = document.createElement('option');
            option.value = type;
            option.textContent = type;
            typeFilter.appendChild(option);
        });
    }
    
    // 绘制图谱
    drawGraph(graphData);
    
    // 响应式处理
    window.addEventListener('resize', function() {
        if (graphContainer) {
            initGraphVisualization();
        }
    });
}

// 绘制图谱
function drawGraph(data) {
    const graphContainer = document.getElementById('graph-container');
    if (!graphContainer) return;
    
    const width = graphContainer.clientWidth;
    const height = graphContainer.clientHeight;
    
    // 创建 SVG
    const svg = d3.select(graphContainer)
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // 创建 tooltip
    const tooltip = d3.select('body')
        .append('div')
        .attr('class', 'tooltip')
        .style('opacity', 0);
    
    // 优化：根据节点数量调整力导向参数
    const nodeCount = data.nodes.length;
    const linkDistance = nodeCount > 500 ? 100 : 150;
    const chargeStrength = nodeCount > 500 ? -300 : -400;
    const collisionRadius = nodeCount > 500 ? 15 : 20;
    
    // 力导向布局 - 智能布局算法
    const simulation = d3.forceSimulation(data.nodes)
        .force('link', d3.forceLink(data.links).id(d => d.id).distance(linkDistance).strength(0.8))
        .force('charge', d3.forceManyBody().strength(chargeStrength))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(d => (d.size || 15) + collisionRadius).iterations(10))
        .force('x', d3.forceX(width / 2).strength(0.1))
        .force('y', d3.forceY(height / 2).strength(0.1))
        .force('radial', d3.forceRadial(Math.min(width, height) / 3, width / 2, height / 2).strength(0.05));
    
    // 优化：设置初始alpha值，加快收敛
    simulation.alpha(0.3).alphaTarget(0.1).restart();
    
    // 优化：根据节点类型进行分组布局
    const typeGroups = {};
    data.nodes.forEach(node => {
        const type = node.type || '其他';
        if (!typeGroups[type]) {
            typeGroups[type] = [];
        }
        typeGroups[type].push(node);
    });
    
    // 为不同类型的节点分配不同的初始位置
    const typeCount = Object.keys(typeGroups).length;
    let angle = 0;
    const radius = Math.min(width, height) / 3;
    
    Object.keys(typeGroups).forEach(type => {
        const groupNodes = typeGroups[type];
        const groupAngle = (angle / 360) * 2 * Math.PI;
        const centerX = width / 2 + Math.cos(groupAngle) * radius;
        const centerY = height / 2 + Math.sin(groupAngle) * radius;
        
        // 为组内节点分配初始位置
        groupNodes.forEach((node, index) => {
            const nodeAngle = (index / groupNodes.length) * 2 * Math.PI;
            const nodeRadius = Math.min(width, height) / 10;
            node.x = centerX + Math.cos(nodeAngle) * nodeRadius;
            node.y = centerY + Math.sin(nodeAngle) * nodeRadius;
        });
        
        angle += 360 / typeCount;
    });
    
    // 优化：对于大规模图谱，减少迭代次数
    if (nodeCount > 1000) {
        simulation.alphaTarget(0.1).restart();
    }
    
    // 创建边组
    const linkGroup = svg.append('g')
        .attr('class', 'link-group');
    
    // 绘制边
    const link = linkGroup.selectAll('line')
        .data(data.links)
        .enter()
        .append('line')
        .attr('class', 'link')
        .attr('stroke-width', d => Math.sqrt(d.value) || 1)
        .attr('stroke', d => d.color || '#94a3b8');
    
    // 优化：对于大规模图谱，默认隐藏边标签
    let linkLabel;
    if (nodeCount < 500) {
        linkLabel = linkGroup.selectAll('text')
            .data(data.links)
            .enter()
            .append('text')
            .attr('class', 'link-label')
            .text(d => d.label || '');
    }
    
    // 创建节点组
    const nodeGroup = svg.append('g')
        .attr('class', 'node-group');
    
    // 绘制节点
    const node = nodeGroup.selectAll('g')
        .data(data.nodes)
        .enter()
        .append('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // 节点圆形
    node.append('circle')
        .attr('r', d => d.size || 15)
        .attr('fill', d => d.color || '#3b82f6')
        .on('mouseover', function(event, d) {
            tooltip.transition()
                .duration(200)
                .style('opacity', 0.9);
            
            // 构建工具提示内容
            let tooltipContent = '<div class="tooltip-title">' + (d.label || d.id) + '</div>';
            tooltipContent += '<div class="tooltip-type">类型: ' + (d.type || '未知') + '</div>';
            
            tooltip.html(tooltipContent)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 28) + 'px');
        })
        .on('mouseout', function() {
            tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        })
        .on('click', function(event, d) {
            // 高亮与当前节点相关的所有边和节点
            highlightRelatedNodes(d.id);
        });
    
    // 节点标签
    const nodeLabels = node.append('text')
        .attr('dy', 4)
        .attr('text-anchor', 'middle')
        .text(d => d.label || d.id)
        .attr('fill', '#333');
    
    // 优化：对于大规模图谱，默认隐藏节点标签
    if (nodeCount > 500) {
        nodeLabels.style('display', 'none');
    }
    
    // 缩放功能
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            // 应用缩放变换到所有元素
            const transform = event.transform;
            svg.select('.node-group').attr('transform', transform);
            svg.select('.link-group').attr('transform', transform);
        });
    
    svg.call(zoom);
    
    // 优化：使用 requestAnimationFrame 优化渲染
    let animationFrameId;
    function updatePositions() {
        // 计算缩放变换
        const transform = d3.zoomTransform(svg.node());
        
        // 更新边的位置
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        if (linkLabel) {
            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2)
                .attr('text-anchor', 'middle')
                .attr('dy', -5);
        }
        
        // 更新节点的位置
        node
            .attr('transform', d => `translate(${d.x},${d.y})`);
        
        // 边界检测与调整
        data.nodes.forEach(node => {
            // 确保节点在可视区域内
            const padding = 50;
            node.x = Math.max(padding, Math.min(width - padding, node.x));
            node.y = Math.max(padding, Math.min(height - padding, node.y));
        });
        
        animationFrameId = requestAnimationFrame(updatePositions);
    }
    
    // 更新位置
    simulation.on('tick', () => {
        if (!animationFrameId) {
            updatePositions();
        }
    });
    
    // 停止动画
    simulation.on('end', () => {
        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }
    });
    
    // 优化：缩放时暂停力导向模拟
    zoom.on('start', () => {
        simulation.stop();
    });
    
    zoom.on('end', () => {
        // 重新启动模拟，使用较低的alpha值
        simulation.alpha(0.1).restart();
    });
    
    // 全局函数
    window.resetZoom = function() {
        svg.transition()
            .duration(750)
            .call(zoom.transform, d3.zoomIdentity);
    };
    
    window.centerGraph = function() {
        simulation.force('center', d3.forceCenter(width / 2, height / 2));
        simulation.alpha(0.3).restart();
    };
    
    window.toggleLabels = function() {
        nodeLabels.style('display', nodeLabels.style('display') === 'none' ? 'block' : 'none');
        if (linkLabel) {
            linkLabel.style('display', linkLabel.style('display') === 'none' ? 'block' : 'none');
        }
    };
    
    // 高亮相关节点
    window.highlightRelatedNodes = function(nodeId) {
        // 重置所有节点和边的样式
        node.select('circle').attr('fill', d => d.color || '#3b82f6');
        link.attr('stroke', d => d.color || '#94a3b8');
        link.attr('stroke-width', d => Math.sqrt(d.value) || 1);
        
        // 高亮与当前节点相关的边和节点
        link.filter(d => d.source.id === nodeId || d.target.id === nodeId)
            .attr('stroke', '#ef4444')
            .attr('stroke-width', 3);
        
        // 高亮当前节点
        node.filter(d => d.id === nodeId)
            .select('circle')
            .attr('fill', '#ef4444');
        
        // 高亮相关节点
        node.filter(d => {
            return link.data().some(link => 
                (link.source.id === nodeId && link.target.id === d.id) || 
                (link.target.id === nodeId && link.source.id === d.id)
            );
        })
        .select('circle')
        .attr('fill', '#f59e0b');
    };
    
    // 路径高亮
    window.highlightPath = function(pathNodes, pathLinks) {
        // 重置所有节点和边的样式
        node.select('circle').attr('fill', d => d.color || '#3b82f6');
        link.attr('stroke', d => d.color || '#94a3b8');
        link.attr('stroke-width', d => Math.sqrt(d.value) || 1);
        
        // 高亮路径中的节点
        node.filter(d => pathNodes.includes(d.id))
            .select('circle')
            .attr('fill', '#10b981');
        
        // 高亮路径中的边
        link.filter(d => {
            return pathLinks.some(link => 
                (link.source === d.source.id && link.target === d.target.id) || 
                (link.source === d.target.id && link.target === d.source.id)
            );
        })
        .attr('stroke', '#10b981')
        .attr('stroke-width', 3);
    };
    
    // 拖拽函数
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

// 可视化路径
async function visualizePath(startId, endId) {
    const graphContainer = document.getElementById('graph-container');
    if (!graphContainer) return;
    
    // 清空容器
    graphContainer.innerHTML = '';
    
    // 添加控制面板
    const controlPanel = document.createElement('div');
    controlPanel.className = 'control-panel';
    controlPanel.innerHTML = `
        <button onclick="resetZoom()">重置缩放</button>
        <button onclick="centerGraph()">居中图谱</button>
        <button onclick="toggleLabels()">切换标签</button>
        <input type="text" id="node-search" placeholder="搜索节点..." style="margin-left: 10px; padding: 5px;">
        <button onclick="searchNode()">搜索</button>
        <select id="type-filter" style="margin-left: 10px; padding: 5px;">
            <option value="all">所有类型</option>
        </select>
        <button onclick="filterByType()">筛选</button>
    `;
    graphContainer.appendChild(controlPanel);
    
    // 添加信息面板
    const infoPanel = document.createElement('div');
    infoPanel.className = 'info-panel';
    infoPanel.innerHTML = `
        路径数量: <strong id="path-count">加载中...</strong> | 
        节点数: <strong id="node-count">0</strong> |
        边数: <strong id="link-count">0</strong>
    `;
    graphContainer.appendChild(infoPanel);
    
    // 从后端API获取路径数据
    try {
        const response = await fetch(`${API_BASE_URL}/graph/path?start=${startId}&end=${endId}&max_depth=5`);
        if (response.ok) {
            const paths = await response.json();
            
            if (paths.length > 0) {
                const pathData = paths[0];
                // 更新统计信息
                document.getElementById('path-count').textContent = paths.length;
                document.getElementById('node-count').textContent = pathData.nodes.length;
                document.getElementById('link-count').textContent = pathData.links.length;
                
                // 填充类型选项
                const typeSet = new Set(pathData.nodes.map(node => node.type));
                const typeFilter = document.getElementById('type-filter');
                if (typeFilter) {
                    typeSet.forEach(type => {
                        const option = document.createElement('option');
                        option.value = type;
                        option.textContent = type;
                        typeFilter.appendChild(option);
                    });
                }
                
                // 绘制路径
                drawGraph(pathData);
            } else {
                // 未找到路径
                infoPanel.innerHTML = `
                    路径数量: <strong id="path-count">0</strong> | 
                    节点数: <strong id="node-count">0</strong> |
                    边数: <strong id="link-count">0</strong>
                `;
                graphContainer.appendChild(infoPanel);
            }
        } else {
            // API调用失败
            infoPanel.innerHTML = `
                路径数量: <strong id="path-count">错误</strong> | 
                节点数: <strong id="node-count">0</strong> |
                边数: <strong id="link-count">0</strong>
            `;
            graphContainer.appendChild(infoPanel);
        }
    } catch (error) {
        console.error('获取路径数据失败:', error);
        infoPanel.innerHTML = `
            路径数量: <strong id="path-count">错误</strong> | 
            节点数: <strong id="node-count">0</strong> |
            边数: <strong id="link-count">0</strong>
        `;
        graphContainer.appendChild(infoPanel);
    }
}

// 可视化相关实体
async function visualizeRelatedEntities(entityId) {
    const graphContainer = document.getElementById('graph-container');
    if (!graphContainer) return;
    
    // 清空容器
    graphContainer.innerHTML = '';
    
    // 添加控制面板
    const controlPanel = document.createElement('div');
    controlPanel.className = 'control-panel';
    controlPanel.innerHTML = `
        <button onclick="resetZoom()">重置缩放</button>
        <button onclick="centerGraph()">居中图谱</button>
        <button onclick="toggleLabels()">切换标签</button>
        <input type="text" id="node-search" placeholder="搜索节点..." style="margin-left: 10px; padding: 5px;">
        <button onclick="searchNode()">搜索</button>
        <select id="type-filter" style="margin-left: 10px; padding: 5px;">
            <option value="all">所有类型</option>
        </select>
        <button onclick="filterByType()">筛选</button>
    `;
    graphContainer.appendChild(controlPanel);
    
    // 添加信息面板
    const infoPanel = document.createElement('div');
    infoPanel.className = 'info-panel';
    infoPanel.innerHTML = `
        中心实体: <strong id="center-entity">${entityId}</strong> | 
        相关实体数: <strong id="related-count">加载中...</strong> |
        关系数: <strong id="relation-count">0</strong>
    `;
    graphContainer.appendChild(infoPanel);
    
    // 从后端API获取相关实体数据
    try {
        const response = await fetch(`${API_BASE_URL}/graph/related?entity_id=${entityId}&depth=2`);
        if (response.ok) {
            const relatedData = await response.json();
            
            // 更新统计信息
            document.getElementById('related-count').textContent = relatedData.nodes.length - 1; // 减去中心实体
            document.getElementById('relation-count').textContent = relatedData.links.length;
            
            // 填充类型选项
            const typeSet = new Set(relatedData.nodes.map(node => node.type));
            const typeFilter = document.getElementById('type-filter');
            if (typeFilter) {
                typeSet.forEach(type => {
                    const option = document.createElement('option');
                    option.value = type;
                    option.textContent = type;
                    typeFilter.appendChild(option);
                });
            }
            
            // 绘制相关实体
            drawGraph(relatedData);
        } else {
            // API调用失败
            infoPanel.innerHTML = `
                中心实体: <strong id="center-entity">${entityId}</strong> | 
                相关实体数: <strong id="related-count">错误</strong> |
                关系数: <strong id="relation-count">0</strong>
            `;
            graphContainer.appendChild(infoPanel);
        }
    } catch (error) {
        console.error('获取相关实体数据失败:', error);
        infoPanel.innerHTML = `
            中心实体: <strong id="center-entity">${entityId}</strong> | 
            相关实体数: <strong id="related-count">错误</strong> |
            关系数: <strong id="relation-count">0</strong>
        `;
        graphContainer.appendChild(infoPanel);
    }
}

// 模拟 API 调用
function fetchApi(endpoint, data) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            resolve({ success: true, data: {} });
        }, 500);
    });
}

// 搜索节点
async function searchNode() {
    const searchInput = document.getElementById('node-search');
    if (!searchInput || !searchInput.value) return;
    
    const searchTerm = searchInput.value.trim().toLowerCase();
    
    // 从后端API获取图谱数据
    const graphData = await fetchGraphData();
    
    // 筛选包含搜索词的节点
    const filteredNodes = graphData.nodes.filter(node => 
        (node.label && node.label.toLowerCase().includes(searchTerm)) ||
        (node.id && node.id.toLowerCase().includes(searchTerm))
    );
    
    // 构建筛选后的图谱数据
    const filteredLinks = [];
    const nodeIds = new Set(filteredNodes.map(node => node.id));
    
    // 只保留与筛选节点相关的边
    graphData.links.forEach(link => {
        if (nodeIds.has(link.source.id) && nodeIds.has(link.target.id)) {
            filteredLinks.push(link);
        }
    });
    
    // 重新绘制图谱
    const graphContainer = document.getElementById('graph-container');
    if (graphContainer) {
        graphContainer.innerHTML = '';
        
        // 添加控制面板
        const controlPanel = document.createElement('div');
        controlPanel.className = 'control-panel';
        controlPanel.innerHTML = `
            <button onclick="resetZoom()">重置缩放</button>
            <button onclick="centerGraph()">居中图谱</button>
            <button onclick="toggleLabels()">切换标签</button>
            <input type="text" id="node-search" placeholder="搜索节点..." style="margin-left: 10px; padding: 5px;" value="${searchTerm}">
            <button onclick="searchNode()">搜索</button>
            <select id="type-filter" style="margin-left: 10px; padding: 5px;">
                <option value="all">所有类型</option>
            </select>
            <button onclick="filterByType()">筛选</button>
        `;
        graphContainer.appendChild(controlPanel);
        
        // 添加信息面板
        const infoPanel = document.createElement('div');
        infoPanel.className = 'info-panel';
        infoPanel.innerHTML = `
            节点: <strong id="node-count">${filteredNodes.length}</strong> | 
            边: <strong id="link-count">${filteredLinks.length}</strong> |
            类型: <strong id="type-count">${new Set(filteredNodes.map(node => node.type)).size}</strong>
        `;
        graphContainer.appendChild(infoPanel);
        
        // 填充类型选项
        const typeSet = new Set(filteredNodes.map(node => node.type));
        const typeFilter = document.getElementById('type-filter');
        if (typeFilter) {
            typeSet.forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                typeFilter.appendChild(option);
            });
        }
        
        // 绘制筛选后的图谱
        drawGraph({ nodes: filteredNodes, links: filteredLinks });
    }
}

// 按类型筛选节点
async function filterByType() {
    const typeFilter = document.getElementById('type-filter');
    if (!typeFilter) return;
    
    const selectedType = typeFilter.value;
    
    // 从后端API获取图谱数据
    const graphData = await fetchGraphData();
    
    // 筛选指定类型的节点
    let filteredNodes;
    if (selectedType === 'all') {
        filteredNodes = graphData.nodes;
    } else {
        filteredNodes = graphData.nodes.filter(node => node.type === selectedType);
    }
    
    // 构建筛选后的图谱数据
    const filteredLinks = [];
    const nodeIds = new Set(filteredNodes.map(node => node.id));
    
    // 只保留与筛选节点相关的边
    graphData.links.forEach(link => {
        if (nodeIds.has(link.source.id) && nodeIds.has(link.target.id)) {
            filteredLinks.push(link);
        }
    });
    
    // 重新绘制图谱
    const graphContainer = document.getElementById('graph-container');
    if (graphContainer) {
        graphContainer.innerHTML = '';
        
        // 添加控制面板
        const controlPanel = document.createElement('div');
        controlPanel.className = 'control-panel';
        controlPanel.innerHTML = `
            <button onclick="resetZoom()">重置缩放</button>
            <button onclick="centerGraph()">居中图谱</button>
            <button onclick="toggleLabels()">切换标签</button>
            <input type="text" id="node-search" placeholder="搜索节点..." style="margin-left: 10px; padding: 5px;">
            <button onclick="searchNode()">搜索</button>
            <select id="type-filter" style="margin-left: 10px; padding: 5px;">
                <option value="all">所有类型</option>
            </select>
            <button onclick="filterByType()">筛选</button>
        `;
        graphContainer.appendChild(controlPanel);
        
        // 添加信息面板
        const infoPanel = document.createElement('div');
        infoPanel.className = 'info-panel';
        infoPanel.innerHTML = `
            节点: <strong id="node-count">${filteredNodes.length}</strong> | 
            边: <strong id="link-count">${filteredLinks.length}</strong> |
            类型: <strong id="type-count">${new Set(filteredNodes.map(node => node.type)).size}</strong>
        `;
        graphContainer.appendChild(infoPanel);
        
        // 填充类型选项
        const typeSet = new Set(graphData.nodes.map(node => node.type));
        const newTypeFilter = document.getElementById('type-filter');
        if (newTypeFilter) {
            typeSet.forEach(type => {
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                if (type === selectedType) {
                    option.selected = true;
                }
                newTypeFilter.appendChild(option);
            });
        }
        
        // 绘制筛选后的图谱
        drawGraph({ nodes: filteredNodes, links: filteredLinks });
    }
}

// 按索引保存搜索结果为Wiki页面
async function saveSearchResultByIndex(index) {
    // 从全局变量中获取搜索结果和查询
    const results = window.searchResults;
    const query = window.currentSearchQuery;
    
    if (!results || !results[index]) {
        console.error('搜索结果不存在');
        return;
    }
    
    const result = results[index];
    await saveSearchResultAsWikiPage(query, result);
}

// 保存搜索结果为Wiki页面
async function saveSearchResultAsWikiPage(query, result) {
    try {
        // 显示加载状态
        const searchResults = document.getElementById('search-results');
        const originalContent = searchResults.innerHTML;
        searchResults.innerHTML = '<div style="text-align: center; padding: 20px;">保存中...</div>';
        
        // 调用后端API保存为Wiki页面
        const response = await fetch(`${API_BASE_URL}/wiki/save-answer`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                answer: result.content,
                related_results: [result]
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            searchResults.innerHTML = '<div style="text-align: center; color: #10b981;">已保存为Wiki页面: ' + data.title + '</div>';
            
            // 3秒后恢复原始内容
            setTimeout(() => {
                searchResults.innerHTML = originalContent;
            }, 3000);
        } else {
            searchResults.innerHTML = '<div style="text-align: center; color: #ef4444;">保存失败</div>';
            
            // 3秒后恢复原始内容
            setTimeout(() => {
                searchResults.innerHTML = originalContent;
            }, 3000);
        }
    } catch (error) {
        console.error('保存搜索结果失败:', error);
        const searchResults = document.getElementById('search-results');
        searchResults.innerHTML = '<div style="text-align: center; color: #ef4444;">保存失败: ' + error.message + '</div>';
    }
}

// 初始化健康检查功能
function initHealthCheck() {
    // 系统状态页面加载时执行
    const statusSection = document.getElementById('status');
    if (statusSection) {
        // 添加健康检查按钮
        const card = statusSection.querySelector('.card');
        if (card) {
            const healthCheckBtn = document.createElement('button');
            healthCheckBtn.id = 'health-check-btn';
            healthCheckBtn.className = 'btn btn-primary';
            healthCheckBtn.textContent = '运行健康检查';
            healthCheckBtn.style.marginBottom = '20px';
            card.insertBefore(healthCheckBtn, card.firstChild);
            
            // 添加健康检查结果容器
            const healthResult = document.createElement('div');
            healthResult.id = 'health-result';
            healthResult.className = 'result';
            card.appendChild(healthResult);
            
            // 添加健康检查按钮事件监听器
            healthCheckBtn.addEventListener('click', async function() {
                await runHealthCheck();
            });
        }
    }
}

// 运行健康检查
async function runHealthCheck() {
    try {
        const healthResult = document.getElementById('health-result');
        if (healthResult) {
            // 显示加载状态
            healthResult.textContent = '运行健康检查中...';
            
            // 调用后端API进行健康检查
            const response = await fetch(`${API_BASE_URL}/health`);
            
            if (response.ok) {
                const data = await response.json();
                healthStatus = data;
                
                // 生成健康检查结果HTML
                let healthHTML = `
                    <h3>健康检查结果</h3>
                    <div class="health-details">
                        <div class="health-card">
                            <h4>Wiki 状态</h4>
                            <p>页面数量: ${data.wiki.total_pages || 0}</p>
                            <p>有效页面: ${data.wiki.valid_pages || 0}</p>
                            <p>无效页面: ${data.wiki.invalid_pages || 0}</p>
                        </div>
                        <div class="health-card">
                            <h4>数据库状态</h4>
                            <p>连接状态: ${data.database.status || '未知'}</p>
                            <p>文档数量: ${data.database.document_count || 0}</p>
                            <p>Wiki页面数量: ${data.database.wiki_page_count || 0}</p>
                            <p>错误: ${data.database.errors ? data.database.errors.length : 0}</p>
                        </div>
                        <div class="health-card">
                            <h4>知识图谱状态</h4>
                            <p>实体数量: ${data.knowledge_graph.entity_count || 0}</p>
                            <p>关系数量: ${data.knowledge_graph.relation_count || 0}</p>
                            <p>状态: ${data.knowledge_graph.status || '未知'}</p>
                        </div>
                        <div class="health-card">
                            <h4>系统状态</h4>
                            <p>总体状态: ${data.overall_status || '未知'}</p>
                            <p>检查时间: ${new Date().toLocaleString()}</p>
                            ${data.wiki.suggestions && data.wiki.suggestions.length > 0 ? `
                                <div class="recommendations">
                                    <h5>建议:</h5>
                                    <ul>
                                        ${data.wiki.suggestions.map(rec => `<li>${rec}</li>`).join('')}
                                    </ul>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
                
                healthResult.innerHTML = healthHTML;
                healthResult.style.color = '#10b981';
            } else {
                healthResult.textContent = '健康检查失败';
                healthResult.style.color = '#ef4444';
            }
        }
    } catch (error) {
        console.error('健康检查失败:', error);
        const healthResult = document.getElementById('health-result');
        if (healthResult) {
            healthResult.textContent = '健康检查失败: ' + error.message;
            healthResult.style.color = '#ef4444';
        }
    }
}

// 页面加载完成后初始化健康检查功能
document.addEventListener('DOMContentLoaded', function() {
    initHealthCheck();
});

// 初始化对话系统
function initDialogSection() {
    // 初始化创建会话按钮
    const createSessionBtn = document.getElementById('create-session-btn');
    if (createSessionBtn) {
        createSessionBtn.addEventListener('click', async function() {
            const documentId = document.getElementById('document-id').value.trim();
            const wikiPageId = document.getElementById('wiki-page-id').value.trim();
            
            try {
                const response = await fetch(`${API_BASE_URL}/dialog/sessions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        document_id: documentId || null,
                        wiki_page_id: wikiPageId || null
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.success) {
                        document.getElementById('session-id').value = result.session_id;
                        alert(`会话创建成功！会话ID: ${result.session_id}`);
                        loadSessionList();
                    } else {
                        alert(`创建会话失败: ${result.error}`);
                    }
                } else {
                    alert('创建会话失败');
                }
            } catch (error) {
                console.error('创建会话失败:', error);
                alert('创建会话失败');
            }
        });
    }
    
    // 初始化发送消息按钮
    const sendMessageBtn = document.getElementById('send-message-btn');
    if (sendMessageBtn) {
        sendMessageBtn.addEventListener('click', async function() {
            const sessionId = document.getElementById('session-id').value.trim();
            const message = document.getElementById('message-input').value.trim();
            
            if (!sessionId) {
                alert('请输入会话ID');
                return;
            }
            
            if (!message) {
                alert('请输入消息内容');
                return;
            }
            
            try {
                // 添加用户消息到对话历史
                addMessageToHistory('user', message);
                
                // 清空消息输入框
                document.getElementById('message-input').value = '';
                
                const response = await fetch(`${API_BASE_URL}/dialog/sessions/${sessionId}/messages`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.success) {
                        // 添加助手消息到对话历史
                        addMessageToHistory('assistant', result.answer);
                        
                        // 显示重要信息
                        if (result.important_info && result.important_info.length > 0) {
                            alert('提取到重要信息，已自动更新相关文档');
                        }
                    } else {
                        alert(`发送消息失败: ${result.error}`);
                    }
                } else {
                    alert('发送消息失败');
                }
            } catch (error) {
                console.error('发送消息失败:', error);
                alert('发送消息失败');
            }
        });
    }
    
    // 初始化获取会话按钮
    const getSessionBtn = document.getElementById('get-session-btn');
    if (getSessionBtn) {
        getSessionBtn.addEventListener('click', async function() {
            const sessionId = document.getElementById('session-id').value.trim();
            
            if (!sessionId) {
                alert('请输入会话ID');
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE_URL}/dialog/sessions/${sessionId}`);
                
                if (response.ok) {
                    const sessionInfo = await response.json();
                    
                    // 清空对话历史
                    document.getElementById('dialog-history').innerHTML = '';
                    
                    // 添加历史消息到对话历史
                    if (sessionInfo.messages) {
                        sessionInfo.messages.forEach(msg => {
                            addMessageToHistory(msg.role, msg.content);
                        });
                    }
                    
                    alert('会话信息加载成功');
                } else {
                    alert('获取会话信息失败');
                }
            } catch (error) {
                console.error('获取会话信息失败:', error);
                alert('获取会话信息失败');
            }
        });
    }
    
    // 初始化删除会话按钮
    const deleteSessionBtn = document.getElementById('delete-session-btn');
    if (deleteSessionBtn) {
        deleteSessionBtn.addEventListener('click', async function() {
            const sessionId = document.getElementById('session-id').value.trim();
            
            if (!sessionId) {
                alert('请输入会话ID');
                return;
            }
            
            if (!confirm(`确定要删除会话 ${sessionId} 吗？`)) {
                return;
            }
            
            try {
                const response = await fetch(`${API_BASE_URL}/dialog/sessions/${sessionId}`, {
                    method: 'DELETE'
                });
                
                if (response.ok) {
                    const result = await response.json();
                    if (result.success) {
                        // 清空对话历史
                        document.getElementById('dialog-history').innerHTML = '';
                        // 清空会话ID
                        document.getElementById('session-id').value = '';
                        // 重新加载会话列表
                        loadSessionList();
                        alert('会话删除成功');
                    } else {
                        alert(`删除会话失败: ${result.error}`);
                    }
                } else {
                    alert('删除会话失败');
                }
            } catch (error) {
                console.error('删除会话失败:', error);
                alert('删除会话失败');
            }
        });
    }
    
    // 加载会话列表
    loadSessionList();
}

// 加载会话列表
async function loadSessionList() {
    try {
        const response = await fetch(`${API_BASE_URL}/dialog/sessions`);
        
        if (response.ok) {
            const sessions = await response.json();
            const sessionList = document.getElementById('session-list');
            
            if (sessionList) {
                if (sessions.length === 0) {
                    sessionList.innerHTML = '<p>暂无会话</p>';
                } else {
                    let html = '<table><thead><tr><th>会话ID</th><th>文档ID</th><th>Wiki页面ID</th><th>创建时间</th><th>操作</th></tr></thead><tbody>';
                    
                    sessions.forEach(session => {
                        const startTime = new Date(session.start_time * 1000).toLocaleString();
                        html += `<tr>\n                            <td>${session.session_id}</td>\n                            <td>${session.document_id || '-'}</td>\n                            <td>${session.wiki_page_id || '-'}</td>\n                            <td>${startTime}</td>\n                            <td>\n                                <button onclick="selectSession('${session.session_id}')" class="btn btn-sm btn-primary">选择</button>\n                                <button onclick="deleteSession('${session.session_id}')" class="btn btn-sm btn-danger">删除</button>\n                            </td>\n                        </tr>`;
                    });
                    
                    html += '</tbody></table>';
                    sessionList.innerHTML = html;
                }
            }
        }
    } catch (error) {
        console.error('加载会话列表失败:', error);
    }
}

// 选择会话
function selectSession(sessionId) {
    document.getElementById('session-id').value = sessionId;
}

// 删除会话
async function deleteSession(sessionId) {
    if (!confirm(`确定要删除会话 ${sessionId} 吗？`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/dialog/sessions/${sessionId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                // 重新加载会话列表
                loadSessionList();
                alert('会话删除成功');
            } else {
                alert(`删除会话失败: ${result.error}`);
            }
        } else {
            alert('删除会话失败');
        }
    } catch (error) {
        console.error('删除会话失败:', error);
        alert('删除会话失败');
    }
}

// 添加消息到对话历史
function addMessageToHistory(role, content) {
    const dialogHistory = document.getElementById('dialog-history');
    if (dialogHistory) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.innerHTML = `
            <div class="message-header">
                <span class="role">${role === 'user' ? '用户' : '助手'}</span>
                <span class="time">${new Date().toLocaleString()}</span>
            </div>
            <div class="message-content">${content}</div>
        `;
        dialogHistory.appendChild(messageDiv);
        // 滚动到底部
        dialogHistory.scrollTop = dialogHistory.scrollHeight;
    }
}