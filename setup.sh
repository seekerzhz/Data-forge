#!/bin/bash

set -e

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
    {
      echo "# Ark (default)"
      echo "ARK_API_KEY=your-ark-api-key"
      echo "ARK_MODEL=doubao-seed-1-6-250615"
      echo "ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3"
      echo ""
      echo "# OpenAI (optional)"
      echo "OPENAI_API_KEY=your-openai-api-key"
      echo "OPENAI_MODEL=gpt-4o-mini"
    } > .env
fi

echo "设置完成！"
echo "使用以下命令激活环境并运行程序："
echo "  source venv/bin/activate"
echo "  python forge.py workspace/example/problem.txt --provider ark --num-cases 50"
