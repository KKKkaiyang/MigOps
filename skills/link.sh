#!/usr/bin/env bash
# 重建 .codebuddy/skills 下指向本目录各技能的软链，使 CodeBuddy Code 进入项目时自动加载。
# 用法：在仓库根目录执行 bash skills/link.sh
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$repo_root/skills"
dst="$repo_root/.codebuddy/skills"

mkdir -p "$dst"

for d in "$src"/*/; do
  name="$(basename "$d")"
  [ "$name" = "$(basename "$src")" ] && continue
  # 仅对含 SKILL.md 的目录建链（排除 README 等非技能项）
  [ -f "$d/SKILL.md" ] || continue
  link="$dst/$name"
  if [ -L "$link" ] || [ -e "$link" ]; then
    rm -f "$link"
  fi
  ln -s "../../skills/$name" "$link"
  echo "linked: $name -> ../../skills/$name"
done

echo "done. Run /skills in CodeBuddy to verify."
