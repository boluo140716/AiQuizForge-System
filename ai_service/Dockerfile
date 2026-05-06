# ========== 1. 基础镜像 ==========
# 使用 Python 3.11 的官方精简镜像（体积小、启动快）
FROM python:3.11-slim

# ========== 2. 设置工作目录 ==========
# 容器内所有后续操作都在 /app 目录下进行
WORKDIR /app

# ========== 3. 安装依赖 ==========
# 先把 requirements.txt 复制进去（利用 Docker 层缓存，代码变但依赖不变时不会重复安装）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ========== 4. 复制项目代码 ==========
# 把当前目录下的所有文件（除 .dockerignore 排除的）复制到容器的工作目录
COPY . .

# ========== 5. 暴露端口 ==========
# 声明容器运行时监听的端口（8001），仅作文档用途，实际映射需在 docker run 时 -p
EXPOSE 8001

# ========== 6. 启动命令 ==========
# 容器启动时自动运行 uvicorn，监听所有网络接口，端口 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]