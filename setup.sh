#!/bin/bash

echo "正在创建虚拟环境..."
python3 -m venv venv

echo "激活虚拟环境..."
source venv/bin/activate

echo "安装依赖包..."
pip install --upgrade pip
pip install -r requirements.txt

echo "检查 .env 文件..."
if [ ! -f .env ]; then
    echo "创建 .env 文件模板，请编辑并填入你的 API Key"
    echo "OPENAI_API_KEY=your-api-key-here" > .env
    echo "OPENAI_MODEL=gpt-4" >> .env
fi

echo "设置完成！"
echo "使用以下命令激活环境并运行程序："
echo "  source venv/bin/activate"
echo "  python auto_data.py problems/example.txt"