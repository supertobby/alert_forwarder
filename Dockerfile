# 使用官方Python镜像作为基础镜像
FROM python:3.9

# 设置工作目录
WORKDIR /app

# 复制当前目录内容到工作目录
COPY . /app

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露Flask默认端口
EXPOSE 5000

# 运行Flask应用
CMD ["python", "alert_forwarder.py"]