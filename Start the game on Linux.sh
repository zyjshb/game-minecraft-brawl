#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"

echo ""
echo "╔══════════════════════════════════╗"
echo "║        游 戏 启 动 器           ║"
echo "╚══════════════════════════════════╝"
echo ""

# ============================================
# 第一步：检测 Python 环境
# ============================================
PYTHON_CMD=""

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
fi

need_install_python=false
need_install_pip=false

if [ -z "$PYTHON_CMD" ]; then
    need_install_python=true
else
    echo "[检测] Python 命令: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

    # 检测 pip 是否有 ensurepip（用于创建 venv）
    if ! $PYTHON_CMD -m ensurepip --version &>/dev/null && ! $PYTHON_CMD -m pip --version &>/dev/null; then
        need_install_pip=true
    fi
fi

# ============================================
# 第二步：Python 未找到，尝试自动安装
# ============================================
if $need_install_python; then
    echo "[检测] 未找到 Python，尝试自动安装..."

    # 检测包管理器
    PM=""
    INSTALL_CMD=""
    if command -v apt &>/dev/null; then
        PM="apt"
    elif command -v apt-get &>/dev/null; then
        PM="apt-get"
    elif command -v dnf &>/dev/null; then
        PM="dnf"
    elif command -v yum &>/dev/null; then
        PM="yum"
    elif command -v pacman &>/dev/null; then
        PM="pacman"
    elif command -v zypper &>/dev/null; then
        PM="zypper"
    elif command -v apk &>/dev/null; then
        PM="apk"
    fi

    SUDO=""
    if [ "$(id -u)" -ne 0 ]; then
        if command -v sudo &>/dev/null; then
            SUDO="sudo"
        else
            SUDO=""
        fi
    fi

    case "$PM" in
        apt|apt-get)
            echo "[安装] 通过 $PM 安装 Python 3..."
            $SUDO $PM update -y
            $SUDO $PM install -y python3 python3-pip python3-venv
            ;;
        dnf)
            echo "[安装] 通过 dnf 安装 Python 3..."
            $SUDO dnf install -y python3 python3-pip
            ;;
        yum)
            echo "[安装] 通过 yum 安装 Python 3..."
            $SUDO yum install -y python3 python3-pip
            ;;
        pacman)
            echo "[安装] 通过 pacman 安装 Python 3..."
            $SUDO pacman -Sy --noconfirm python python-pip
            ;;
        zypper)
            echo "[安装] 通过 zypper 安装 Python 3..."
            $SUDO zypper install -y python3 python3-pip
            ;;
        apk)
            echo "[安装] 通过 apk 安装 Python 3..."
            $SUDO apk add python3 py3-pip
            ;;
        *)
            echo ""
            echo "[错误] 无法识别包管理器，请手动安装 Python 3.10+"
            echo "Debian/Ubuntu: sudo apt install python3 python3-pip python3-venv"
            echo "Fedora:        sudo dnf install python3 python3-pip"
            echo "Arch:          sudo pacman -S python python-pip"
            echo ""
            exit 1
            ;;
    esac

    # 重新检测 Python
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "[错误] Python 安装失败，请手动安装。"
        exit 1
    fi
    echo "[完成] Python 安装成功！"
fi

# ============================================
# 第三步：确保 pip 可用（不是 venv 必需但有助于检测）
# ============================================
if $need_install_pip && [ -n "$PYTHON_CMD" ]; then
    echo "[检测] pip 未安装，尝试安装..."
    SUDO=""
    if [ "$(id -u)" -ne 0 ] && command -v sudo &>/dev/null; then SUDO="sudo"; fi

    if command -v apt &>/dev/null || command -v apt-get &>/dev/null; then
        $SUDO apt install -y python3-pip python3-venv 2>/dev/null || true
    elif command -v dnf &>/dev/null; then
        $SUDO dnf install -y python3-pip 2>/dev/null || true
    elif command -v pacman &>/dev/null; then
        $SUDO pacman -Sy --noconfirm python-pip 2>/dev/null || true
    fi
fi

# ============================================
# 第四步：创建/激活虚拟环境（隔离、安全）
# ============================================
setup_venv() {
    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo "[设置] 正在创建 Python 虚拟环境..."
        if ! $PYTHON_CMD -m venv "$VENV_DIR" 2>/dev/null; then
            echo "[错误] 虚拟环境创建失败，已自动跳过。"
            return 1
        fi
        echo "[完成] 虚拟环境创建成功。"
    fi
    source "$VENV_DIR/bin/activate"
    return 0
}

# ============================================
# 第五步：检测并安装 pygame
# ============================================

# 先尝试用虚拟环境
VENV_READY=false
if setup_venv; then
    VENV_READY=true
    PIP_CMD="pip"
else
    # Fallback: 直接用系统 Python 安装
    if [ -n "$PYTHON_CMD" ]; then
        PIP_CMD="$PYTHON_CMD -m pip"
    else
        echo "[错误] 没有可用的 Python 环境。"
        exit 1
    fi
fi

echo "[检测] 检查 pygame..."

if python -c "import pygame" 2>/dev/null; then
    echo "[检测] pygame 已安装。"
else
    echo "[安装] 正在安装 pygame..."

    # 优先使用清华镜像
    if $PIP_CMD install pygame -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null; then
        echo "[完成] pygame 安装成功！"
    else
        echo "[重试] 使用默认源安装..."
        if $PIP_CMD install pygame 2>/dev/null; then
            echo "[完成] pygame 安装成功！"
        else
            echo ""
            echo "[错误] pygame 安装失败，请检查网络连接。"
            echo "手动安装: $PIP_CMD install pygame"
            echo ""
            exit 1
        fi
    fi
fi

echo "[检测] 检查 opencv-python..."

if python -c "import cv2" 2>/dev/null; then
    echo "[检测] opencv-python 已安装。"
else
    echo "[安装] 正在安装 opencv-python..."

    # 优先使用清华镜像
    if $PIP_CMD install opencv-python -i https://pypi.tuna.tsinghua.edu.cn/simple 2>/dev/null; then
        echo "[完成] opencv-python 安装成功！"
    else
        echo "[重试] 使用默认源安装..."
        if $PIP_CMD install opencv-python 2>/dev/null; then
            echo "[完成] opencv-python 安装成功！"
        else
            echo ""
            echo "[错误] opencv-python 安装失败，请检查网络连接。"
            echo "手动安装: $PIP_CMD install opencv-python"
            echo ""
            exit 1
        fi
    fi
fi

# ============================================
# 第六步：启动游戏
# ============================================
echo ""
echo "[启动] 正在启动游戏..."
echo "══════════════════════════════════"
echo ""

python main.py
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo ""
    echo "[提示] 游戏已退出（退出码: $exit_code）。"
fi

# 退出虚拟环境
if $VENV_READY; then
    deactivate 2>/dev/null || true
fi

exit $exit_code
