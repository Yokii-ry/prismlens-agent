# 用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录，后续所有命令都在这个目录下执行
WORKDIR /app

# 先装 uv（包管理工具）
RUN pip install uv

# uv sync 默认把依赖安装到项目虚拟环境，容器启动命令需要能找到其中的可执行文件
ENV PATH="/app/.venv/bin:$PATH"

# 先复制依赖文件，利用 Docker 的层缓存机制
# 只要 pyproject.toml 没变，这一层就不会重新执行，加快构建速度
COPY pyproject.toml .
COPY uv.lock .

# 安装所有生产依赖
RUN uv sync --frozen --no-dev

# 再复制其他所有代码
COPY . .

# 暴露端口（仅声明，实际映射在 docker-compose.yml 里配置）
EXPOSE 8000
