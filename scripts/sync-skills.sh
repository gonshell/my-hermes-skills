#!/bin/bash
#===============================================================================
# sync-skills.sh — 将 ~/.hermes/skills 同步到 GitHub 仓库
#
# 使用方式:
#   ./scripts/sync-skills.sh                    # 同步所有自定义 skills
#   ./scripts/sync-skills.sh weibo xitter        # 只同步指定 skills
#   DRY_RUN=1 ./scripts/sync-skills.sh           # 只显示要同步的内容，不执行
#
#===============================================================================

set -euo pipefail

# ---------- 配置 ----------
SKILLS_DIR="/Users/xiesg/.hermes/skills"
GIT_DIR="/Users/xiesg/github/my-hermes-skills"

# 需要同步的 skills（为空则同步全部）
# 留空表示同步所有 skills
CUSTOM_SKILLS=()

# 同步模式： "all" | "custom-only" | "specified"
MODE="${SYNC_MODE:-all}"

# 干跑模式（只打印，不复制）
DRY_RUN="${DRY_RUN:-0}"

# Git commit message
COMMIT_MSG="${COMMIT_MSG:-sync: $(date '+%Y-%m-%d %H:%M')}"

# ---------- 颜色输出 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ---------- 检查 ----------
[[ -d "$SKILLS_DIR" ]] || { log_error "Skills 目录不存在: $SKILLS_DIR"; exit 1; }
[[ -d "$GIT_DIR" ]]   || { log_error "Git 仓库目录不存在: $GIT_DIR"; exit 1; }

# ---------- 构建同步列表 ----------
build_sync_list() {
    local specified=("$@")

    if [[ ${#specified[@]} -gt 0 ]]; then
        # 指定了 skills
        for s in "${specified[@]}"; do
            echo "$s"
        done
    elif [[ "$MODE" == "all" ]]; then
        # 同步全部
        find "$SKILLS_DIR" -maxdepth 5 -name "SKILL.md" -type f | \
            while read f; do
                rel="${f#$SKILLS_DIR/}"
                echo "${rel%/*}"
            done | sort -u
    else
        log_error "未知模式: $MODE"
        exit 1
    fi
}

# ---------- 同步单个 skill ----------
sync_skill() {
    local skill="$1"  # 格式: category/skill-name
    local src="$SKILLS_DIR/$skill"
    local dst="$GIT_DIR/$skill"

    if [[ ! -d "$src" ]]; then
        log_warn "Skill 目录不存在，跳过: $skill"
        return 1
    fi

    # 创建目标目录
    if [[ "$DRY_RUN" == "0" ]]; then
        mkdir -p "$(dirname "$dst")"
    fi

    # 复制内容（排除 .DS_Store 和日志）
    if [[ "$DRY_RUN" == "1" ]]; then
        echo "  [DRY] cp -r $src → $dst"
    else
        rsync -a --exclude='.DS_Store' --exclude='*.log' \
              --exclude='*.tmp' --exclude='__pycache__' \
              "$src/" "$dst/"
        echo "  ✓ $skill"
    fi
}

# ---------- 主流程 ----------
main() {
    log_info "Skills 目录: $SKILLS_DIR"
    log_info "Git 仓库:    $GIT_DIR"
    echo

    # 解析要同步的 skills
    mapfile -t SKILLS < <(build_sync_list "$@") 2>/dev/null || {
        # macOS compatibility: use alternative
        IFS=$'\n' read -d '' -r -a SKILLS <<< "$(build_sync_list "$@")" || true
    }
    total=${#SKILLS[@]}

    if [[ $total -eq 0 ]]; then
        log_warn "没有需要同步的 skills"
        exit 0
    fi

    log_info "找到 $total 个 skills 待同步:"
    for s in "${SKILLS[@]}"; do
        echo "  - $s"
    done
    echo

    # 执行同步
    if [[ "$DRY_RUN" == "1" ]]; then
        log_info "干跑模式，不执行任何操作"
    else
        log_info "开始同步..."
    fi
    echo

    success=0
    for s in "${SKILLS[@]}"; do
        sync_skill "$s" && ((success++)) || true
    done

    echo
    log_info "成功同步 $success/$total 个 skills"

    # Git 提交（仅在非干跑模式下）
    if [[ "$DRY_RUN" == "0" && $success -gt 0 ]]; then
        echo
        log_info "Git 提交..."
        cd "$GIT_DIR"

        # 检查是否有变更
        if git diff --quiet && [[ -z $(git ls-files --others --exclude-standard) ]]; then
            log_warn "没有变更，跳过 Git 提交"
        else
            git add -A
            git commit -m "$COMMIT_MSG"
            log_info "已提交: $COMMIT_MSG"

            # 尝试推送（可能失败如果没有配置 remote）
            # 用 --get 替代 geturl：兼容性更好，macOS 旧版 git 支持
            if git config --get remote.origin.url >/dev/null 2>&1; then
                if git push origin main 2>&1; then
                    log_info "已推送到 GitHub"
                else
                    log_warn "推送失败，请检查网络或认证配置"
                fi
            else
                log_warn "未配置 remote origin，跳过推送"
                log_info "请手动运行: cd $GIT_DIR && git remote add origin git@github.com:YOUR_NAME/my-hermes-skills.git"
            fi
        fi
    fi
}

# ---------- 入口 ----------
main "$@"
