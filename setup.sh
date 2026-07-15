#!/bin/bash

set -e

VENV_DIR=".venv"
HOST="${DATAFORGE_HOST:-127.0.0.1}"
PORT="${DATAFORGE_PORT:-8000}"

echo "正在创建虚拟环境..."
python3 -m venv "$VENV_DIR"

echo "激活虚拟环境..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "安装依赖包..."
pip install --upgrade pip
pip install -r requirements.txt

echo "检查 .env 文件..."
if [ ! -f .env ]; then
    echo "创建 .env 文件模板，请编辑并填入你的 API Key"
    {
      echo "# Provider: deepseek / ark / openai / openai_compatible"
      echo "LLM_PROVIDER=deepseek"
      echo ""
      echo "# DeepSeek (default)"
      echo "DEEPSEEK_API_KEY=your-deepseek-key"
      echo "DEEPSEEK_BASE_URL=https://api.deepseek.com"
      echo "DEEPSEEK_MODEL=deepseek-v4-pro"
      echo "DEEPSEEK_REASONING_MODEL=deepseek-v4-pro"
      echo "DEEPSEEK_REASONING_MAX_TOKENS=8192"
      echo ""
      echo "# Ark (optional)"
      echo "# ARK_API_KEY=your-ark-api-key"
      echo "# ARK_MODEL=doubao-seed-1-6-250615"
      echo "# ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3"
      echo ""
      echo "# OpenAI (optional)"
      echo "# OPENAI_API_KEY=your-openai-api-key"
      echo "# OPENAI_MODEL=gpt-4o-mini"
      echo ""
      echo "# OpenAI-Compatible (optional)"
      echo "# OPENAI_COMPAT_API_KEY=your-compat-key"
      echo "# OPENAI_COMPAT_BASE_URL=https://api.deepseek.com/v1"
      echo "# OPENAI_COMPAT_MODEL=deepseek-chat"
      echo ""
      echo "# DataForge hardening"
      echo "DATAFORGE_HOST=127.0.0.1"
      echo "DATAFORGE_PORT=8000"
      echo "DATAFORGE_API_TOKEN="
      echo "DATAFORGE_RATE_LIMIT_PER_MINUTE=30"
      echo "DATAFORGE_MAX_QUEUE_SIZE=50"
      echo "DATAFORGE_TASK_TTL_SECONDS=3600"
      echo "DATAFORGE_CASE_WORKERS=4"
      echo "DATAFORGE_SANDBOX=auto"
      echo "LLM_MAX_RETRIES=3"
      echo "LLM_RETRY_BASE_SECONDS=1.0"
    } > .env
fi

echo "设置完成！"
echo "使用以下命令激活环境并运行程序："
echo "  source $VENV_DIR/bin/activate"
echo "  uvicorn webapp:app --host ${HOST} --port ${PORT}"
echo "默认仅本机可访问。若必须公网暴露，请设置强 DATAFORGE_API_TOKEN，并用反向代理限制来源。"
