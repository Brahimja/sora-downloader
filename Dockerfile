# 使用官方 Python 镜像作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码到工作目录
COPY . .

# 暴露端口
EXPOSE 8000

# 运行应用的命令
# 环境变量将完全在 'docker run' 时注入，无需在此处声明
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]